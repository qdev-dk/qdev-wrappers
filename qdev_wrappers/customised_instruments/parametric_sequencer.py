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

import broadbean as bb
from broadbean.element import Element
from broadbean.segment import in_context


log = logging.getLogger(__name__)

Setpoints = NamedTuple('Setpoints', (('symbol', Symbol), ('values', Sequence)))

def make_named_tuple(named_tuple, tuple):
    if tuple is None:
        return None
    return named_tuple(*tuple)

class AWGInterface:

    def upload(self, forged_sequence: ForgedSequenceType):
        raise NotImplementedError()

    def set_infinit_loop(self, element_index: int,
                         true_on_false_off: bool):
        raise NotImplementedError()

    def set_repeated_element(self, index):
        raise NotImplementedError()

    def get_SR(self):
        raise NotImplementedError()


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

        self.add_parameter('repeat_mode', set_cmd=self._set_repeat_mode)

        # all symbols are mapped to parameters that live on the SequenceChannel
        # and RepeatChannel respectively
        sequence_channel = SequenceChannel(self, 'sequence_parameters')
        self.add_submodule('sequence', sequence_channel)
        repeat_channel = SequenceChannel(self, 'repeat_parameters')
        self.add_submodule('repeat', repeat_channel)

        # populate the sequence channel with the provided symbols
        self.load_template(template_element=template_element,
                           inner_setpoints=inner_setpoints,
                           outer_setpoints=outer_setpoints,
                           context=context,
                           units=units,
                           labels=labels,
                           initial_element=initial_element,
                           upload=True)

    def load_template(self,
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
                      inner: Tuple[Symbol, Sequence],
                      outer: Tuple[Symbol, Sequence]=None,
                      upload=True):
        inner = make_named_tuple(Setpoints, inner)
        outer = make_named_tuple(Setpoints, outer)
        self._sequence_up_to_date = False

        self.last_inner_index = 0
        self.last_outer_index = 0

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
        # assert correct mode
        if self._outer_setpoints:
            if set_inner:
                inner_index = self._value_to_index(value,
                                                   self._inner_setpoints)
                self.last_inner_index = inner_index
                outer_index = self.last_outer_index
            else:
                inner_index = self.last_inner_index
                outer_index = self._value_to_index(value,
                                                   self._outer_setpoints)
                self.last_outer_index = outer_index
            index = (outer_index*len(self._outer_setpoints.values) +
                     inner_index)
        else:
            assert set_inner
            index = self._value_to_index(value, self._inner_setpoints)
            self.last_inner_index = index
        # most awgs are 1 indexed not 0 indexed
        index+=1
        if self.initial_element is not None:
            index += 1
        self.awg.set_repeated_element(index)

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
