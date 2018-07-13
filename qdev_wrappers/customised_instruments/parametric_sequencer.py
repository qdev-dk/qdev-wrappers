import logging

from typing import Dict
from broadbean.types import ContextDict, ForgedSequenceType

from copy import copy
from functools import partial

import numpy as np

from qcodes.instrument.base import Instrument
from broadbean.element import Element
from broadbean.sequence import Sequence
from broadbean.segment import in_context


log = logging.getLogger(__name__)

class AWGInterface:

    def upload(self, forged_sequence: ForgedSequenceType):
        raise NotImplementedError()

    def set_infinit_loop(self, element_index: int,
                         true_on_false_off: bool):
        raise NotImplementedError()
        
    def step(self, from_index, to_index):
        raise NotImplementedError()

    def get_SR(self):
        raise NotImplementedError()

# possibly extract everything that is not relevant for the instrument communication into another layer
# i.e. the triple (template_element, context, setpoints) plus building sequence
# contra: units are not included here
# start out with 1D tests
class ParametricSequencer(Instrument):

    def __init__(self, name:str,
                 awg:AWGInterface,
                 template_element: Element,
                 context: ContextDict,
                 setpoints: Dict,
                 initial_element: Element=None) -> None:
        super().__init__(name)
        self.awg = awg
        self.template_element = template_element
        self.initial_element = initial_element
        self.context = context
        self.setpoints = setpoints


        # TODO: implement context manager like in alazar driver
        # until then cheat to avoid multiple uploads:
        self._do_update_on_set = False

        # add non-step parameters
        for name, value in self.context.items():
            # TODO: add units
            self.add_parameter(name=name,
                               get_cmd=None,
                               set_cmd=partial(self._set_context_parameter,
                                               name),
                               initial_value=value)
        self._do_update_on_set = True
        self._update_sequence()
        self._upload_sequence()

        # add step parameters
        symbol = self.setpoints["symbol"]
        parameter_name = f'step_{symbol}'
        self.add_parameter(name=parameter_name,
                           get_cmd=None,
                           set_cmd=self._set_step)
        self._step_parameter = self.parameters[parameter_name]
        self._step_parameter(None)

        # TODO: add setpoints and template to metadata


    def _set_context_parameter(self, parameter, val):
        self.context[parameter] = val
        self._update_sequence()
        self._upload_sequence()

    def _set_step(self, value):
        if value is None:
            to_index = None
        else:
            to_index = self._set_point_to_element_index(value)
        old_value = self._step_parameter.get_latest()
        if old_value is not None:
            from_index = self._set_point_to_element_index(old_value)
        else:
            from_index = to_index
        self.awg.step(from_index, to_index)

    def _set_point_to_element_index(self, setpoint_value):
        index = (np.abs(self.setpoints['values']
                        - setpoint_value)).argmin() + 1
        if self.initial_element is not None:
            index += 1
        return index


    def _update_sequence(self):
        if self._do_update_on_set:
            elements = []
            for value in self.setpoints['values']:
                kwarg = {self.setpoints['symbol']: value}
                new_element = in_context(self.template_element,
                                        **kwarg)
                elements.append(new_element)

            # make sequence repeat indefinitely
            elements[-1].sequencing['goto_state'] = 1

            if self.initial_element is not None:
                elements.insert(0, self.initial_element)

            self.sequence = Sequence(elements)
            self.sequence_context = {k: v for k,v in self.context.items()
                                    if k != self.setpoints['symbol']}

    def _upload_sequence(self):
        if self._do_update_on_set:
            self.awg.upload(self.sequence.forge(SR=self.awg.get_SR(),
                                                context=self.sequence_context))

