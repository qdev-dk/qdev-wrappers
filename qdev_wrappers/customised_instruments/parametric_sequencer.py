import logging
from warnings import warn

from typing import Dict, Union, Tuple, NamedTuple, Optional, TypeVar
from typing_extensions import final, Final
from numbers import Number

import typing
from lomentum.types import (
    ContextDict, Symbol, RoutesDictType)

from functools import partial
from contextlib import contextmanager

import numpy as np

from qcodes.instrument.base import Instrument
from qcodes.instrument.channel import InstrumentChannel
from qcodes.utils import validators

from lomentum import Sequence, Element, in_context

from qdev_wrappers.customised_instruments.awg_interface import AWGInterface

log = logging.getLogger(__name__)

#
NOT_GIVEN: Final = 'This is a placeholder for arguments that have not been supplied.'
T = TypeVar('T')
_Optional = Union[T, str]

# namedtuple for the setpoints of a sequence. Symbol refers to a broavsdbean
# symbol and values is a
Setpoints = NamedTuple('Setpoints',
                       (('symbol', Symbol),
                        ('values', typing.Sequence)))
SetpointsType = Optional[Tuple[Symbol, typing.Sequence]]


def make_setpoints_tuple(from_tuple) -> Union[None, Setpoints]:
    if from_tuple is None:
        return None
    return Setpoints(*from_tuple)


class OutOfRangeException(Exception):
    def __init__(self, message, value, erange):
        self.message = message
        self.value = value
        self.erange = erange

class RoundingWarning(Warning):
    def __init__(self, message, original, rounded):
        self.message = message
        self.original = original
        self.rounded = rounded

class SequenceChannel(InstrumentChannel):
    """
    This is a dummy InstrumentChannel in order to isolate the name scope
    of the sequence symbols. All the logic is still contained in the
    ParametricSequencer.
    """
    def __init__(self, parent: 'ParametricSequencer', name: str) -> None:
        super().__init__(parent, name)


class RepeatChannel(InstrumentChannel):
    """
    This is a dummy InstrumentChannel in order to isolate the name scope
    of the sequence symbols assosicated with stepping. All the logic is still
    contained in the ParametricSequencer.
    """
    def __init__(self, parent: 'ParametricSequencer', name: str) -> None:
        super().__init__(parent, name)


class ParametricSequencer(Instrument):
    """
    possibly extract everything that is not relevant for the instrument
    communication into another layer i.e. the triple (template_element,
    context, setpoints) plus building sequence
    contra: units are not included here
    start out with 1D tests
    """

    def __init__(self,
                 name: str,
                 awg: AWGInterface,
                 routes: Optional[RoutesDictType]=None,
                 units: Optional[Dict[Symbol, str]]=None,
                 labels: Optional[Dict[Symbol, str]]=None,
                 template_element: _Optional[Element]=NOT_GIVEN,
                 inner_setpoints: _Optional[Union[SetpointsType,str]]=NOT_GIVEN,
                 outer_setpoints: _Optional[SetpointsType]=NOT_GIVEN,
                 context: _Optional[ContextDict]=NOT_GIVEN,
                 first_sequence_element: _Optional[Element]=NOT_GIVEN,
                 initial_element: _Optional[Element]=NOT_GIVEN):
        super().__init__(name)
        self.awg = awg
        self.routes = routes
        
        self.units: Dict[Symbol, str] = units or {}
        self.labels: Dict[Symbol, str] = labels or {}
        
        # we need to initialise these attributes with `None`. The actual value
        # gets set via the `change_sequence` call
        self._template_element: Optional[Element] = None
        self._inner_setpoints: SetpointsType = None
        self._outer_setpoints: SetpointsType = None
        self._context: ContextDict = {}
        self._first_sequence_element: Optional[Element] = None
        self._initial_element: Optional[Element] = None
        
        # inital values of states
        self._do_upload = True
        self._do_sync_repetion_state = True
        self.deviation_margin = None

        # all symbols are mapped to parameters that live on the SequenceChannel
        # and RepeatChannel respectively
        sequence_channel = SequenceChannel(self, 'sequence_parameters')
        self.add_submodule('sequence', sequence_channel)
        repeat_channel = SequenceChannel(self, 'repeat_parameters')
        self.add_submodule('repeat', repeat_channel)

        # this parameter has to be added at the end because setting it
        # to its initial value is only is defined when a sequence is uploaded
        self.add_parameter(
            'repeat_mode',
            vals=validators.Enum('element', 'inner', 'sequence'),
            set_cmd=self._set_repeat_mode)

        # populate the sequence channel with the provided symbols
        # suppress upload if sequence passed in by the constructor is
        # incomplete
        self._do_upload = self._is_sequence_complete()
        self.change_sequence(
            template_element=template_element,
            inner_setpoints=inner_setpoints,
            outer_setpoints=outer_setpoints,
            context=context,
            initial_element=initial_element,
            first_sequence_element=first_sequence_element)
        self._do_upload = True

    def change_sequence(self,
                        template_element: _Optional[Element]=NOT_GIVEN,
                        inner_setpoints: _Optional[SetpointsType]=NOT_GIVEN,
                        outer_setpoints: _Optional[SetpointsType]=NOT_GIVEN,
                        context: _Optional[ContextDict]=NOT_GIVEN,
                        first_sequence_element: _Optional[Element]=NOT_GIVEN,
                        initial_element: _Optional[Element]=NOT_GIVEN) -> None:
        if template_element is not NOT_GIVEN:
            self._template_element = template_element
        if first_sequence_element is not NOT_GIVEN:
            self._first_sequence_element = first_sequence_element
        if initial_element is not NOT_GIVEN:
            self._initial_element = initial_element
        if context is not NOT_GIVEN:
            self._context = context
        if inner_setpoints is not NOT_GIVEN:
            self._inner_setpoints = make_setpoints_tuple(inner_setpoints)
        if outer_setpoints is not NOT_GIVEN:
            self._outer_setpoints = make_setpoints_tuple(outer_setpoints)

        # add metadata, that gets added to the snapshot automatically
        # add it before the upload so that if there is a crash, the
        # state that is causing the crash is captured in the metadata
        self._update_metadata()
        # self._validate_sequence()

        # no matter what is changed, the sequence is no longer up to date.
        self._sequence_up_to_date = False
        with self.single_upload():
            # only update parameters if context changed
            if context is not NOT_GIVEN:
                # add sequence symbols as qcodes parameters
                self.sequence.parameters = {}
                for name, value in self._context.items():
                    self.sequence.add_parameter(
                        name=name,
                        unit=self.units.get(name, ''),
                        label=self.labels.get(name, ''),
                        get_cmd=None,
                        set_cmd=partial(self._set_context_parameter, name),
                        initial_value=value)
            if (inner_setpoints is not NOT_GIVEN or
               outer_setpoints is not NOT_GIVEN):
                self._update_setpoints()

    def _validate_sequence(self):
        # TODO: implement error
        assert self._is_sequence_complete()

    def _is_sequence_complete(self) -> bool:
        # TODO: implement validation that checks if all symbols are provided
        # this might be best done in the lomentum layer
        return (
            self._template_element is not None and
            self._context is not None
        )

    def _update_setpoints(self):
        self._sequence_up_to_date = False

        self.last_inner_index = 0
        self.last_outer_index = 0
        self._inner_index = 0
        self._outer_index = 0

        # setting this state to False is needed to avoid syncing when the
        # initial value of the parameters is set.
        self._do_sync_repetion_state = False

        self.repeat.parameters = {}
        for setpoints in (self._inner_setpoints, self._outer_setpoints):
            if setpoints is None:
                continue
            symbol = setpoints.symbol
            set_inner = setpoints is self._inner_setpoints
            self.repeat.add_parameter(name=symbol,
                                      get_cmd=None,
                                      set_cmd=partial(
                                          self._set_repeated_element,
                                          set_inner=set_inner),
                                      unit=self.units.get(symbol, ''),
                                      label=self.labels.get(symbol, ''),
                                      initial_value=setpoints.values[0])
        self._do_sync_repetion_state = True

        # define shortcuts
        self._inner_setpoint_parameter = None
        self._outer_setpoint_parameter = None
        if self._inner_setpoints:
            self._inner_setpoint_parameter = (
                self.repeat.parameters[self._inner_setpoints.symbol])
        if self._outer_setpoints:
            self._outer_setpoint_parameter = (
                self.repeat.parameters[self._outer_setpoints.symbol])

        if self._do_upload:
            self._upload_sequence()

    def _update_metadata(self):
        # add metadata, that gets added to the snapshot automatically
        self.metadata['inner_setpoints'] = self._inner_setpoints
        self.metadata['outer_setpoints'] = self._outer_setpoints
        # TODO: add serialization of the elements
        # self.metadata['template_element'] = template_element
        # self.metadata['initial_element'] = initial_element

    def get_inner_setpoints(self):
        return self._inner_setpoints

    def get_outer_setpoints(self):
        return self._outer_setpoints

    # context managers
    @contextmanager
    def no_upload(self):
        # we have to save the oringinal stat in order to allow nesting of
        # this context
        original_state = self._do_upload
        self._do_upload = False
        try:
            yield
        finally:
            self._do_upload = original_state

    @contextmanager
    def single_upload(self):
        with self.no_upload():
            yield
        # wrapping single upload somewhere in a no_upload context should not
        # result in an upload. Therefore add check of flag
        if self._do_upload:
            self._upload_sequence()

    # Parameter getters and setters
    def _set_repeat_mode(self, mode):
        self._sync_repetion_state(mode)

    def _set_context_parameter(self, parameter, val):
        self._context[parameter] = val
        self._sequence_up_to_date = False
        if self._do_upload:
            self._upload_sequence()

    def _set_repeated_element(self, value, set_inner):
        if self.repeat_mode() == 'sequence':
            warn(f"Warning: setting the {['outer', 'inner'][set_inner]} "
                 f"setpoints to while being in sequence mode")
        try:
            if set_inner:
                self._inner_index = self._value_to_index(value,
                                                        self._inner_setpoints)
                self.last_inner_index = self._inner_index
            else:
                self._outer_index = self._value_to_index(value,
                                                        self._outer_setpoints)
                self.last_outer_index = self._outer_index
        except OutOfRangeException as e:
            setpoints_name = [self._outer_setpoints,
                              self._inner_setpoints][set_inner].symbol
            raise RuntimeWarning(
                'Error setting repeated element corressponding to ' +
                f'the {["outer", "inner"][set_inner]} setpoints ' +
                f'{setpoints_name}: \n' +
                e.message)

        if self._do_sync_repetion_state:
            self._sync_repetion_state()

    def _get_repeated_element(self, set_inner):
        # TODO: implement
        return None

    def _sync_repetion_state(self, repeat_mode=None):
        if repeat_mode is None:
            repeat_mode = self.repeat_mode()
        if repeat_mode == 'sequence':
            self.awg.repeat_full_sequence()
        if repeat_mode == 'element':
            if self._outer_setpoints is None:
                index = self._inner_index
            else:
                index = (self._outer_index *
                         len(self._outer_setpoints.values) +
                         self._inner_index)

            index += 1
            if self._initial_element is not None:
                index += 1
            self.awg.set_repeated_element(int(index))
            # # assert correct mode
            # if self._outer_setpoints:
            #     index = (outer_index*len(self._outer_setpoints.values) +
            #              inner_index)
            # else:
            #     assert set_inner
            #     index = self._value_to_index(value, self._inner_setpoints)
            #     self.last_inner_index = index
            # # most awgs are 1 indexed not 0 indexed
            # index += 1
            # if self.initial_element is not None:
            #     index += 1
            # self.awg.set_repeated_element(index)
        elif repeat_mode == 'inner':
            raise NotImplementedError('The "inner" repeat_mode is not yet'
                                      ' implemented')
            # if not set_inner:
            #     raise RuntimeWarning('Cannot set repeated outer setpoint '
            #                          'when repeat mode is "inner"')

    def _value_to_index(self, value, setpoints):
        # setpoints may have any type. For numbers apply interpolation
        if isinstance(value, Number):
            values = np.asarray(setpoints.values)
            delta = 0.5 * np.min(np.absolute(np.diff(values)))
            rmin = np.nanmin(values) - delta
            rmax = np.nanmax(values) + delta
            if value > rmax or value < rmin:
                raise OutOfRangeException(
                    f'Value {value} is outside of range ({rmin}, {rmax})',
                    value, (rmin, rmax))
            index = (np.abs(values - value)).argmin()
            deviation = abs(values[index] - value)
            relative_deviation = deviation / (
                (rmax-rmin) / len(values))
            close_to_zero_deviation = np.isclose(relative_deviation, 0)

            # if None: warn if not close
            # if 0: fail if not equal
            # if number: fail
            if self.deviation_margin is None:
                if not close_to_zero_deviation:
                    warn(f'Rounding setpoint value from {value} to '
                         f'{values[index]}.')
            # `=` is important for the 0 case
            elif deviation >= self.deviation_margin:
                raise RuntimeWarning(
                    f'Error: Trying to set repeat element to `{value}`. '
                    f'The closest available segment corresponds to '
                    f'`{values[index]}` which deviates more than the '
                    f'configured deviation margin `{self.deviation_margin}` '
                    f'Refusing to continue!')

            return index
        else:
            return setpoints.values.index(value)

    # Private methods
    def _upload_sequence(self):
        self._update_sequence()
        self.awg.upload(
            self._sequence_object.forge(SR=self.awg.get_SR(),
                                        routes=self.routes,
                                        context=self._sequence_context))
        # uploading a sequence will clear the state of the current element
        # so we need to sync the repetition state or revert the value of
        # repetition mode
        self._sync_repetion_state()

    def _update_sequence(self):
        if self._sequence_up_to_date:
            return
        elements = []
        # this duplication of code could be done nicer, with some more time...
        # 2D
        if self._outer_setpoints is not None:
            for i, outer_value in enumerate(self._outer_setpoints.values):
                kwarg = {self._outer_setpoints.symbol: outer_value}
                for j, inner_value in enumerate(self._inner_setpoints.values):
                    if (self._first_sequence_element is not None and
                        j == 0 and i == 0):
                        template = self._first_sequence_element
                    else:
                        template = self._template_element
                    kwarg[self._inner_setpoints.symbol] = inner_value
                    new_element = in_context(template, **kwarg)
                    elements.append(new_element)
        # 1D
        elif self._inner_setpoints is not None:
            kwarg = {}
            for j, inner_value in enumerate(self._inner_setpoints.values):
                if (self._first_sequence_element is not None and
                    j == 0):
                    template = self._first_sequence_element
                else:
                    template = self._template_element
                kwarg[self._inner_setpoints.symbol] = inner_value
                new_element = in_context(template, **kwarg)
                elements.append(new_element)
        # 0D
        else:
            if self._first_sequence_element is not None:
                elements.append(self._first_sequence_element)
            elements.append(self._template_element)
    
        # make sequence repeat indefinitely
        elements[-1].sequencing['goto_state'] = 1

        if self._initial_element is not None:
            elements.insert(0, self._initial_element)

        self._sequence_object = Sequence(elements)

        if self._outer_setpoints is not None:
            condition = lambda k: (k != self._inner_setpoints.symbol and
                                   k != self._outer_setpoints.symbol)
        elif self._inner_setpoints is not None:
            condition = lambda k: k != self._inner_setpoints.symbol
        else:
            condition = lambda k: True

        self._sequence_context = {k: v for k, v in self._context.items()
                                  if condition(k)}

        self._sequence_up_to_date = True
