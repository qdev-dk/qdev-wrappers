from typing import Union, Optional
from contextlib import contextmanager
from qcodes.instrument.base import Instrument
import qcodes.utils.validators as vals
from qcodes.utils.helpers import create_on_off_val_mapping
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateParameter
from qdev_wrappers.customised_instruments.composite_instruments.sidebander.sidebander import check_carrier_sidebanding_status, Sidebander, sync_repeat_parameters
from qdev_wrappers.customised_instruments.composite_instruments.parametric_sequencer.parametric_sequencer import ParametricSequencer
from qdev_wrappers.customised_instruments.interfaces.microwave_source_interface import MicrowaveSourceInterface
from qdev_wrappers.customised_instruments.composite_instruments.heterodyne_source.heterodyne_source import HeterodyneSource


class SidebanderChannel(Sidebander, InstrumentChannel):
    def __init__(self, parent: Instrument, name: str,
                 sequencer: ParametricSequencer,
                 carrier: Union[MicrowaveSourceInterface, HeterodyneSource],
                 **kwargs):
        super().__init__(parent=parent, name=name, sequencer=sequencer,
                         carrier=carrier, pulse_building_prepend=True,
                         **kwargs)


class Multiplexer(Instrument):
    SIDEBANDER_CLASS = SidebanderChannel

    def __init__(self, name: str,
                 sequencer: ParametricSequencer,
                 carrier: Union[MicrowaveSourceInterface, HeterodyneSource],
                 **kwargs):
        super().__init__(name, **kwargs)
        self.carrier = carrier
        self.sequencer = sequencer
        self._pulse_building_prepend = False
        self._sequencer_up_to_date = False
        self.add_parameter(
            name='carrier_power',
            source=carrier.power,
            parameter_class=DelegateParameter)
        self.add_parameter(
            name='carrier_frequency',
            set_fn=self._set_carrier_frequency,
            source=carrier.frequency,
            parameter_class=DelegateParameter)
        self.add_parameter(
            name='carrier_status',
            source=carrier.status,
            parameter_class=DelegateParameter)
        sidebanders = ChannelList(
            self, 'sidebanders', SidebanderChannel)
        self.add_submodule('sidebanders', sidebanders)

    def _set_carrier_frequency(self, val):
        for s in self.sidebanders:
            s.frequency._save_val(val + s.sideband_frequency())

    def change_sequence(self, **kwargs):
        context_dict = self.generate_context()
        context_dict['context'].update(kwargs.pop('context', {}))
        context_dict['labels'].update(kwargs.pop('labels', {}))
        context_dict['units'].update(kwargs.pop('units', {}))
        original_do_upload_setting = self.sequencer._do_upload
        self.sequencer._do_upload = True
        self.sequencer.change_sequence(**context_dict, **kwargs)
        self._sequencer_up_to_date = True
        self.sequencer._do_upload = original_setting
        sync_repeat_parameters(self.sequencer, self.pulse_building_parameters)
        check_carrier_sidebanding_status(self.carrier)

    def generate_context(self):
        context = {}
        labels = {}
        units = {}
        for s in self.sidebanders:
            full_context = s.generate_context()
            context.update(full_context['context'])
            labels.update(full_context['labels'])
            units.update(full_context['units'])
        return {'context': context, 'labels': labels, 'units': units}

    def update_sequence(self):
        if not self._sequencer_up_to_date:
                self.change_sequence()

    def add_sidebander(self):
        ch_num = len(self.sidebanders)
        name = '{}{}'.format(self.name, ch_num)
        sidebander = self.SIDEBANDER_CLASS(
            name, self.sequencer, self.carrier)
        sidebander.carrier_frequency.set_allowed = False
        self.add_submodule(name, sidebander)
        self.sidebanders.append(sidebander)
        return sidebande

    @property
    def pulse_building_parameters(self):
        param_dict = {p.symbol_name: p for p in self.parameters.values() if
                      isinstance(p, PulseBuildingParameter)}
        for s in self.sidebanders:
            param_dict.update(s.pulse_building_parameters)
        return param_dict
