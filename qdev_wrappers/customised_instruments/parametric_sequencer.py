import logging

from typing import Dict, Union, Tuple, Sequence, NamedTuple
from broadbean.types import ContextDict, ForgedSequenceType, Symbol

from copy import copy
from functools import partial
from contextlib import contextmanager
from collections import namedtuple

import numpy as np

from qcodes.instrument.base import Instrument
from qcodes.instrument.channel import InstrumentChannel
from qcodes.utils import validators

import broadbean as bb
from broadbean.element import Element
from broadbean.segment import in_context
from broadbean.plotting import plotter


log = logging.getLogger(__name__)

Setpoints = NamedTuple('Setpoints', (('symbol', Symbol), ('values', Sequence)))


def make_setpoints_tuple(tuple) -> Union[None, Setpoints]:
    if tuple is None:
        return None
    return Setpoints(*tuple)


class AWGInterface:

    def upload(self, forged_sequence: ForgedSequenceType):
        raise NotImplementedError()

    def set_infinit_loop(self, element_index: int,
                         true_on_false_off: bool):
        raise NotImplementedError()

    def set_repeated_element(self, index):
        raise NotImplementedError()

    def set_repeated_element_series(self, start_index, stop_index):
        raise NotImplementedError()

    def repeat_full_sequence(self):
        raise NotImplementedError()

    def get_SR(self):
        raise NotImplementedError()


class SimulatedAWGInterface(AWGInterface):
    def __init__(self):
        self.forged_sequence = None

    def upload(self, forged_sequence: ForgedSequenceType):
        print(f'uploading')
        SR = self.get_SR()
        self.forged_sequence = forged_sequence
        plotter(forged_sequence, SR=SR)

    def set_repeated_element(self, index):
        print(f'setting repeated element to {index}')
        if self.forged_sequence is None:
            print(f'but there was not sequence uploaded')
            return
        plotter(self.forged_sequence[index], SR=self.get_SR())

    def set_repeated_element_series(self, start_index, stop_index):
        print(f'setting repeated element series from {start_index} to '
              f'{stop_index}')
        if self.forged_sequence is None:
            print(f'but there was not sequence uploaded')
            return
        plotter(self.forged_sequence[start_index:stop_index], SR=self.get_SR())

    def repeat_full_sequence(self):
        print(f'repeating full series')
        plotter(self.forged_sequence, SR=self.get_SR())

    def get_SR(self):
        # fake this for now
        return 1e6


class AWG5014Interface(AWGInterface):
    def __init__(self, awg):
        self.awg = awg
        self.last_repeated_element = None
        self.forged_sequence = None
        self.last_repeated_element_series = (None, None)

    def upload(self, forged_sequence: ForgedSequenceType):
        self.awg.make_send_and_load_awg_file_from_forged_sequence(forged_sequence)
        self.forged_sequence = forged_sequence
        self.awg.all_channels_on()
        self.awg.run()

    def set_repeated_element(self, index):
        print(f'stop repeating {self.last_repeated_element} start {index}')
        self.awg.set_sqel_loopcnt_to_inf(index, state=1)
        self.awg.sequence_pos(index)
        if self.last_repeated_element is not None:
            self.awg.set_sqel_loopcnt_to_inf(self.last_repeated_element,
                                             state=0)
        self.last_repeated_element = index

    def set_repeated_element_series(self, start_index, stop_index):
        self._restore_sequence_state()
        self.awg.set_sqel_goto_target_index(stop_index, start_index)
        self.awg.sequence_pos(start_index)

    def repeat_full_sequence(self):
        self._restore_sequence_state()
        self.awg.sequence_pos(1)

    def get_SR(self):
        return 1e6

    def _restore_sequence_state(self):
        if self.last_repeated_element is not None:
            self.awg.set_sqel_loopcnt_to_inf(self.last_repeated_element,
                                             state=0)
        lres = self.last_repeated_element_series
        if lres[0] is not None or lres[1] is not None:
            assert (lres[0] is not None and
                    lres[1] is not None and
                    self.forged_sequence is not None)
            if lres[0] == len(self.forged_sequence):
                goto_element = 1
            else:
                goto_element = 0
            self.awg.set_sqel_goto_target_index(lres[0], goto_element)


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
                 context: ContextDict={},
                 units: Dict[Symbol, str]={},
                 labels: Dict[Symbol, str]={},
                 initial_element: Element=None) -> None:
        super().__init__(name)
        self.awg = awg

        self.add_parameter('repeat_mode',
                           vals=validators.Enum('element', 'inner', 'sequence'),
                           initial_value='sequence',
                           set_cmd=self._set_repeat_mode)

        # all symbols are mapped to parameters that live on the SequenceChannel
        # and RepeatChannel respectively
        sequence_channel = SequenceChannel(self, 'sequence_parameters')
        self.add_submodule('sequence', sequence_channel)
        repeat_channel = SequenceChannel(self, 'repeat_parameters')
        self.add_submodule('repeat', repeat_channel)

        # populate the sequence channel with the provided symbols
        self.set_template(template_element=template_element,
                           inner_setpoints=inner_setpoints,
                           outer_setpoints=outer_setpoints,
                           context=context,
                           units=units,
                           labels=labels,
                           initial_element=initial_element,
                           upload=True)

    def set_template(self,
                      template_element: Element,
                      inner_setpoints: Tuple[Symbol, Sequence],
                      outer_setpoints: Tuple[Symbol, Sequence]=None,
                      context: ContextDict={},
                      units: Dict[Symbol, str]={},
                      labels: Dict[Symbol, str]={},
                      initial_element: Element=None,
                      upload=False) -> None:
        self.template_element = template_element
        self.initial_element = initial_element
        self._context = context
        self._units = units
        self._labels = labels

        self._sequence_up_to_date = False
        self._sync_repetion_state_element = True

        # add sequence symbols as qcodes parameters
        self.sequence.parameters = {}
        with self.no_upload():
            for name, value in self._context.items():
                self.sequence.add_parameter(name=name,
                                            unit=self._units.get(name, ''),
                                            label=self._labels.get(name, ''),
                                            get_cmd=None,
                                            set_cmd=partial(
                                                self._set_context_parameter,
                                                name),
                                            initial_value=value)

        # add metadata, that gets added to the snapshot automatically
        # TODO: add serialization of the elements
        self.metadata['template_element'] = template_element
        self.metadata['initial_element'] = initial_element

        if inner_setpoints is not None or outer_setpoints is not None:
            self.set_setpoints(inner=inner_setpoints,
                               outer=outer_setpoints,
                               upload=upload)
        elif upload:
            self._upload_sequence()

    def set_setpoints(self,
                      inner: Union[Tuple[Symbol, Sequence], None],
                      outer: Union[Tuple[Symbol, Sequence], None]=None,
                      upload=True):
        inner = make_setpoints_tuple(inner)
        outer = make_setpoints_tuple(outer)
        self._sequence_up_to_date = False

        self.last_inner_index = 0
        self.last_outer_index = 0
        self._inner_index = 0
        self._outer_index = 0

        self._inner_setpoints = inner
        self._outer_setpoints = outer
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
                                      initial_value=setpoints.values[0])
        # define shortcuts (with long names, I know)
        self._inner_setpoint_parameter = None
        self._outer_setpoint_parameter = None
        if inner:
            self._inner_setpoint_parameter = self.repeat.parameters[inner.symbol]
        if outer:
            self._outer_setpoint_parameter = self.repeat.parameters[outer.symbol]

        # add metadata, that gets added to the snapshot automatically
        self.metadata['inner_setpoints'] = inner
        self.metadata['outer_setpoints'] = outer

        if upload:
            self._upload_sequence()

    # context managers
    @contextmanager
    def no_upload(self):
        self._do_upload_on_set_sequence_parameter = False
        yield
        self._do_upload_on_set_sequence_parameter = True

    @contextmanager
    def single_upload(self):
        self._do_upload_on_set_sequence_parameter = False
        yield
        self._do_upload_on_set_sequence_parameter = True
        self._upload_sequence()

    # Parameter getters and setters
    def _set_repeat_mode(self, mode):
        pass

    def _set_context_parameter(self, parameter, val):
        self._context[parameter] = val
        self._sequence_up_to_date = False
        if self._do_upload_on_set_sequence_parameter:
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
        if self._sync_repetion_state_element:
            self._sync_repetion_state()

    def _get_repeated_element(self, set_inner):
        # TODO: implement
        return None

    def _sync_repetion_state(self):
        if self.repeat_mode() == 'sequence':
            pass
            # raise RuntimeWarning('Cannot set repeated element when repeat '
            #                      'mode is "sequence"')
        if self.repeat_mode() == 'element':
            if self._outer_index is None:
                index = self._inner_index
            else:
                index = (self._outer_index*len(self._outer_setpoints.values) +
                    self._inner_index)
            index += 1
            if self.initial_element is not None:
                index += 1
            self.awg.set_repeated_element(index)
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
        elif self.repeat_mode() == 'inner':
            if not set_inner:
                raise RuntimeWarning('Cannot set repeated outer setpoint '
                                     'when repeat mode is "inner"')


    @staticmethod
    def _value_to_index(value, setpoints):
        index = (np.abs(setpoints.values -
                        value)).argmin()
        return index

    # Private methods
    def _upload_sequence(self):
        self._update_sequence()
        self.awg.upload(
            self._sequence_object.forge(SR=self.awg.get_SR(),
                                        context=self._sequence_context))

    def _update_sequence(self):
        if self._sequence_up_to_date:
            return
        elements = []
        # this duplication of code could be done nicer, with some more time
        if self._outer_setpoints:
            for outer_value in self._outer_setpoints.values:
                kwarg = {self._outer_setpoints.symbol: outer_value}
                for inner_value in self._inner_setpoints.values:
                    kwarg[self._inner_setpoints.symbol] = inner_value
                    new_element = in_context(self.template_element, **kwarg)
                    elements.append(new_element)
        else:
            kwarg = {}
            for inner_value in self._inner_setpoints.values:
                kwarg[self._inner_setpoints.symbol] = inner_value
                new_element = in_context(self.template_element, **kwarg)
                elements.append(new_element)

        # make sequence repeat indefinitely
        elements[-1].sequencing['goto_state'] = 1

        if self.initial_element is not None:
            elements.insert(0, self.initial_element)

        self._sequence_object = bb.Sequence(elements)

        condition = lambda k: k != self._inner_setpoints.symbol
        if self._outer_setpoints:
            condition = lambda k: (k != self._inner_setpoints.symbol and
                                   k != self._outer_setpoints.symbol)

        self._sequence_context = {k: v for k, v in self._context.items()
                                  if condition(k)}

        self._sequence_up_to_date = True
