import logging

from typing import Dict, Union, Tuple, Sequence, NamedTuple
from lomentum.types import ContextDict, ForgedSequenceType, Symbol

from copy import copy
from functools import partial
from contextlib import contextmanager
from collections import namedtuple

import numpy as np

from qcodes.instrument.base import Instrument
from qcodes.instrument.channel import InstrumentChannel
from qcodes.utils import validators

from lomentum import Sequence, Element, in_context
from lomentum.plotting import plotter

from qdev_wrappers.customised_instruments.awg_interface import AWGInterface

log = logging.getLogger(__name__)


# namedtuple for the setpoints of a sequence. Symbol refers to a broadbean
# symbol and values is a
Setpoints = NamedTuple('Setpoints', (('symbol', Symbol), ('values', Sequence)))


def make_setpoints_tuple(tuple) -> Union[None, Setpoints]:
    if tuple is None:
        return None
    return Setpoints(*tuple)


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
    def __init__(self, name: str,
                 awg: AWGInterface,
                 template_element: Element,
                 inner_setpoints: Tuple[Symbol, Sequence],
                 outer_setpoints: Tuple[Symbol, Sequence]=None,
                 context: ContextDict=None,
                 units: Dict[Symbol, str]=None,
                 labels: Dict[Symbol, str]=None,
                 first_sequence_element: Element=None,
                 initial_element: Element=None) -> None:
        super().__init__(name)
        self.awg = awg

        # inital values of states
        self._do_upload = True
        self._do_sync_repetion_state = True

        # all symbols are mapped to parameters that live on the SequenceChannel
        # and RepeatChannel respectively
        sequence_channel = SequenceChannel(self, 'sequence_parameters')
        self.add_submodule('sequence', sequence_channel)
        repeat_channel = SequenceChannel(self, 'repeat_parameters')
        self.add_submodule('repeat', repeat_channel)

        # this parameter has to be added at the end because setting it
        # to its initial value is only is defined when a sequence is uploaded
        self.add_parameter('repeat_mode',
                           vals=validators.Enum('element', 'inner', 'sequence'),
                           set_cmd=self._set_repeat_mode)

        # populate the sequence channel with the provided symbols
        self.set_template(template_element=template_element,
                          inner_setpoints=inner_setpoints,
                          outer_setpoints=outer_setpoints,
                          context=context,
                          units=units,
                          labels=labels,
                          initial_element=initial_element,
                          first_sequence_element=first_sequence_element)

    def set_template(self,
                     template_element: Element,
                     inner_setpoints: Tuple[Symbol, Sequence],
                     outer_setpoints: Tuple[Symbol, Sequence]=None,
                     context: ContextDict=None,
                     units: Dict[Symbol, str]=None,
                     labels: Dict[Symbol, str]=None,
                     first_sequence_element: Element=None,
                     initial_element: Element=None) -> None:
        self.template_element = template_element
        self.first_sequence_element = first_sequence_element
        self.initial_element = initial_element
        self._context = context or {}
        self._units = units or {}
        self._labels = labels or {}

        self._sequence_up_to_date = False

        # add metadata, that gets added to the snapshot automatically
        # add it before the upload so that if there is a crash, the
        # state that is causing the crash is captured in the metadata
        # TODO: add serialization of the elements
        # self.metadata['template_element'] = template_element
        # self.metadata['initial_element'] = initial_element

        # add sequence symbols as qcodes parameters
        self.sequence.parameters = {}
        with self.single_upload():
            for name, value in self._context.items():
                self.sequence.add_parameter(name=name,
                                            unit=self._units.get(name, ''),
                                            label=self._labels.get(name, ''),
                                            get_cmd=None,
                                            set_cmd=partial(
                                                self._set_context_parameter,
                                                name),
                                            initial_value=value)
            if inner_setpoints is not None or outer_setpoints is not None:
                self.set_setpoints(inner=inner_setpoints,
                                   outer=outer_setpoints)

    def set_setpoints(self,
                      inner: Union[Tuple[Symbol, Sequence], None],
                      outer: Union[Tuple[Symbol, Sequence], None]=None):
        inner = make_setpoints_tuple(inner)
        outer = make_setpoints_tuple(outer)
        self._sequence_up_to_date = False

        # add metadata, that gets added to the snapshot automatically
        self.metadata['inner_setpoints'] = inner
        self.metadata['outer_setpoints'] = outer

        self.last_inner_index = 0
        self.last_outer_index = 0
        self._inner_index = 0
        self._outer_index = 0

        self._inner_setpoints = inner
        self._outer_setpoints = outer

        # setting this state to False is needed to avoid syncing when the
        # initial value of the parameters is set.
        self._do_sync_repetion_state = False

        self.repeat.parameters = {}
        for setpoints in (inner, outer):
            if setpoints is None:
                continue
            symbol = setpoints.symbol
            self.repeat.add_parameter(name=symbol,
                                      get_cmd=None,
                                      set_cmd=partial(
                                          self._set_repeated_element,
                                          set_inner=setpoints == inner),
                                      unit=self._units.get(symbol, ''),
                                      label=self._labels.get(symbol, ''),
                                      initial_value=setpoints.values[0])
        self._do_sync_repetion_state = True
        # define shortcuts (with long names, I know)
        self._inner_setpoint_parameter = None
        self._outer_setpoint_parameter = None
        if inner:
            self._inner_setpoint_parameter = self.repeat.parameters[inner.symbol]
        if outer:
            self._outer_setpoint_parameter = self.repeat.parameters[outer.symbol]

        if self._do_upload:
            self._upload_sequence()

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
        yield
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
        if set_inner:
            self._inner_index = self._value_to_index(value,
                                                     self._inner_setpoints)
            self.last_inner_index = self._inner_index
        else:
            self._outer_index = self._value_to_index(value,
                                                     self._outer_setpoints)
            self.last_outer_index = self._outer_index
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
                index = (self._outer_index * len(self._outer_setpoints.values) +
                         self._inner_index)
            index += 1
            if self.initial_element is not None:
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
            if not set_inner:
                raise RuntimeWarning('Cannot set repeated outer setpoint '
                                     'when repeat mode is "inner"')

    @staticmethod
    def _value_to_index(value, setpoints):
        if type(value) is str:
            return setpoints.values.index(value)
        else:
            values = np.asarray(setpoints.values)
            return (np.abs(values - value)).argmin()

    # Private methods
    def _upload_sequence(self):
        self._update_sequence()
        self.awg.upload(
            self._sequence_object.forge(SR=self.awg.get_SR(),
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
        if self._outer_setpoints:
            for i, outer_value in enumerate(self._outer_setpoints.values):
                kwarg = {self._outer_setpoints.symbol: outer_value}
                for j, inner_value in enumerate(self._inner_setpoints.values):
                    if (self.first_sequence_element is not None and
                        j == 0 and i == 0):
                        template = self.first_sequence_element
                    else:
                        template = self.template_element
                    kwarg[self._inner_setpoints.symbol] = inner_value
                    new_element = in_context(template, **kwarg)
                    elements.append(new_element)
        else:
            kwarg = {}
            for j, inner_value in enumerate(self._inner_setpoints.values):
                if (self.first_sequence_element is not None and
                    j == 0):
                    template = self.first_sequence_element
                else:
                    template = self.template_element
                kwarg[self._inner_setpoints.symbol] = inner_value
                new_element = in_context(template, **kwarg)
                elements.append(new_element)

        # make sequence repeat indefinitely
        elements[-1].sequencing['goto_state'] = 1

        if self.initial_element is not None:
            elements.insert(0, self.initial_element)

        self._sequence_object = Sequence(elements)

        condition = lambda k: k != self._inner_setpoints.symbol
        if self._outer_setpoints:
            condition = lambda k: (k != self._inner_setpoints.symbol and
                                   k != self._outer_setpoints.symbol)

        self._sequence_context = {k: v for k, v in self._context.items()
                                  if condition(k)}

        self._sequence_up_to_date = True
