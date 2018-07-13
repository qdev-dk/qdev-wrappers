import logging

from typing import Dict, Union
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
        self._context = {}
        self._setpoints = {}
        self._sequence_up_to_date = False

        self.load_sequence(template_element=template_element,
                           context=context,
                           initial_element=initial_element,
                           setpoints=setpoints,
                           upload=True)

    def load_sequence(self,
                      template_element: Element,
                      context: ContextDict,
                      setpoints: Union[Dict, None]=None,
                      initial_element: Union[Element, None]=None,
                      upload=False):

        self._sequence_up_to_date = False

        self.template_element = template_element
        self.initial_element = initial_element
        # context:
        for k in self._context:
            self.parmeters[k].pop()
        self._context = context
        
        # TODO: implement context manager like in alazar driver
        # until then cheat to avoid multiple uploads:
        self._do_upload_on_set = False

        # add non-step parameters
        for name, value in self._context.items():
            # TODO: add units
            self.add_parameter(name=name,
                               get_cmd=None,
                               set_cmd=partial(self._set_context_parameter,
                                               name),
                               initial_value=value)
        self._do_upload_on_set = True

        # add metadata, that gets added to the snapshot automatically
        self.metadata['template_element'] = template_element
        self.metadata['initial_element'] = template_element
        self.metadata['context'] = context

        if setpoints is not None:
            self.load_setpoints(setpoints, upload=upload)
        elif upload:
            self._upload_sequence()
        

    def load_setpoints(self,
                       setpoints: Dict,
                       upload=True):
        self._sequence_up_to_date = False
        # add step parameters
        symbol = setpoints["symbol"]
        parameter_name = f'step_{symbol}'
        self.add_parameter(name=parameter_name,
                           get_cmd=None,
                           set_cmd=self._set_step)
        self._step_parameter = self.parameters[parameter_name]
        self._step_parameter(None)

        self._setpoints = setpoints
        # add metadata, that gets added to the snapshot automatically
        self.metadata['setpoints'] = setpoints

        if upload:
            self._upload_sequence()


    def _set_context_parameter(self, parameter, val):
        self._context[parameter] = val
        if self._do_upload_on_set:
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
        index = (np.abs(self._setpoints['values']
                        - setpoint_value)).argmin() + 1
        if self.initial_element is not None:
            index += 1
        return index

    def _upload_sequence(self):
        if not self._sequence_up_to_date:
            self._update_sequence()
        if self._do_upload_on_set:
            self.awg.upload(self.sequence.forge(SR=self.awg.get_SR(),
                                                context=self.sequence_context))

    def _update_sequence(self):
        if self._do_upload_on_set:
            elements = []
            for value in self._setpoints['values']:
                kwarg = {self._setpoints['symbol']: value}
                new_element = in_context(self.template_element,
                                        **kwarg)
                elements.append(new_element)

            # make sequence repeat indefinitely
            elements[-1].sequencing['goto_state'] = 1

            if self.initial_element is not None:
                elements.insert(0, self.initial_element)

            self.sequence = Sequence(elements)
            self.sequence_context = {k: v for k,v in self._context.items()
                                    if k != self._setpoints['symbol']}
# data is added to the snapshot via the metadata attribute instead
    # def snapshot_base(self, update: bool=False,
    #                   params_to_skip_update: Sequence[str]=None):
    #     # TODO: add setpoints and template to metadata
