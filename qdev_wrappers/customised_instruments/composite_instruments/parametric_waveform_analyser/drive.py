from functools import partial
from typing import Union, Optional
from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qcodes.utils import validators as vals
from qdev_wrappers.customised_instruments.composite_instruments.sidebander.sidebander import Sidebander
from qdev_wrappers.customised_instruments.composite_instruments.sidebander.pulse_building_parameter import PulseBuildingParameter
from qdev_wrappers.customised_instruments.composite_instruments.multiplexer.multiplexer import Multiplexer
from qdev_wrappers.customised_instruments.composite_instruments.parametric_sequencer.parametric_sequencer import ParametricSequencer
from qdev_wrappers.customised_instruments.interfaces.microwave_source_interface import MicrowaveSourceInterface
from qdev_wrappers.customised_instruments.composite_instruments.heterodyne_source.heterodyne_source import HeterodyneSource
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateParameter
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateMultiChannelParameter

# TODO: move mode to microwave source interface

class DriveSidebander(InstrumentChannel, Sidebander):
    def __init__(self, parent, name: str,
                 sequencer: ParametricSequencer,
                 carrier: Union[MicrowaveSourceInterface, HeterodyneSource],
                 symbol_prepend: Optional[str]=None):
        super().__init__(parent=parent,
                         name=name,
                         sequencer_name=sequencer.name,
                         carrier_if_name=carrier.name,
                         symbol_prepend=symbol_prepend)
        self.add_parameter(
            name='DRAG_amplitude',
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='spectroscopy_amplitude',
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='gate_amplitude',
            parameter_class=PulseBuildingParameter)


class DriveChannel(InstrumentChannel, Multiplexer):
    SIDEBANDER_CLASS = DriveSidebander

    def __init__(self, parent, name: str,
                 sequencer: ParametricSequencer,
                 carrier: Union[MicrowaveSourceInterface, HeterodyneSource]):
        super().__init__(parent=parent, name=name, sequencer_name=sequencer.name,
                         carrier_if_name=carrier.name)

        # heterodyne source parameters
        self.add_parameter(name='carrier_power',
                           source=carrier.power,
                           parameter_class=DelegateParameter)
        self.add_parameter(name='carrier_status',
                           source=carrier.status,
                           parameter_class=DelegateParameter)
        mode_vals = []
        if carrier._IQ_option:
            mode_vals.append('basic')
            mode_vals.append('bsidebandedasic') # TODO HEREEE
        raise RuntimeError('BAD')
        self.add_parameter(name='carrier_mode',
                           get_cmd=self._get_carrier_mode,
                           set_cmd=self._set_carrier_mode,
                           parameter_class=DelegateParameter)

        # pulse building parameters
        self.add_parameter(name='stage_duration',
                           symbol_name='drive_stage_duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='sigma_cutoff',
                           symbol_name='sigma_cutoff',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='drive_readout_delay',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='modulation_marker_duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='pulse_separation',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='spectroscopy_pulse_duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='pulse_duration',
                           symbol_name='drive_pulse_duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='gate_separation',
                           unit='s',
                           parameter_class=PulseBuildingParameter)

    def _get_carrier_mode(self):
        if self.carrier.IQ_state() and self.carrier.pulsemod_state():
            return 'sidebanded_modulated'
        elif self.carrier.IQ_state():
            return 'sidebanded'
        elif self.carrier.pulsemod_state():
            return 'modulated'
        else:
            return 'basic'

    def _set_carrier_mode(self, val):
        if val == 'sidebanded_modulated':
            self.carrier.IQ_state(1)
            self.carrier.pulsemod_state(1)
        elif val == 'sidebanded':
            self.carrier.IQ_state(1):
            self.carrier.pulsemod_state(0)
        elif 'modulated':
            self.carrier.IQ_state(0):
            self.carrier.pulsemod_state(1)
        else:
            return 'basic'

    def _set_carrier_frequency(self, val):
        super()._set_carrier_frequency(val)
        setpoint_symbols = [self.sequencer.inner_setpoints[0], self.sequencer.outer_setpoints[0]]
        sideband_symbols = [s.sideband_frequency.symbol_name for s in self.sidebanders]
        if any(s in setpoint_symbols for s in sideband_symbols):
            # self.parent.readout.set_alazar_not_up_to_date()
            self.parent.readout.update_all_alazar()
