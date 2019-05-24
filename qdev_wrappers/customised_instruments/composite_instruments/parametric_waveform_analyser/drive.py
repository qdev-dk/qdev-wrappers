from typing import Union, Optional
from qcodes.instrument.channel import InstrumentChannel
from qdev_wrappers.customised_instruments.composite_instruments.sidebander.sidebander import Sidebander
from qdev_wrappers.customised_instruments.composite_instruments.sidebander.pulse_building_parameter import PulseBuildingParameter
from qdev_wrappers.customised_instruments.composite_instruments.multiplexer.multiplexer import Multiplexer
from qdev_wrappers.customised_instruments.composite_instruments.parametric_sequencer.parametric_sequencer import ParametricSequencer
from qdev_wrappers.customised_instruments.interfaces.microwave_source_interface import MicrowaveSourceInterface
from qdev_wrappers.customised_instruments.composite_instruments.heterodyne_source.heterodyne_source import HeterodyneSource
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateParameter

# TODO: clean up overlap/delay situation (nataliejpg)

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
        self.sideband_frequency._save_val(0)
        self.I_offset._save_val(0)
        self.Q_offset._save_val(0)
        self.gain_offset._save_val(0)
        self.phase_offset._save_val(0)
        self.amplitude._save_val(1)
        self.state._save_val(1)
        self.DRAG_amplitude._save_val(0)
        self.spectroscopy_amplitude._save_val(1)
        self.gate_amplitude._save_val(1)

class DelayParameter(PulseBuildingParameter):
    def set_raw(self, val):
        if val >= 0:
            self.instrument._drive_readout_overlap(0)
            super().set_raw(val)
        else:
            self.set_raw(0)
            self.instrument._drive_readout_overlap(-val)

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
        self.add_parameter(name='carrier_state',
                           source=carrier.state,
                           parameter_class=DelegateParameter)
        self.add_parameter(name='pulse_modulation_state',
                           source=carrier.pulse_modulation_state,
                           parameter_class=DelegateParameter)
        self.add_parameter(name='IQ_modulation_state',
                           source=carrier.IQ_modulation_state,
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
                           parameter_class=DelayParameter)
        self.add_parameter(name='_drive_readout_overlap',
                           symbol_name='drive_readout_overlap',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='modulation_marker_duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='gate_pulse_separation',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='spectroscopy_pulse_duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='gate_pulse_duration',
                           symbol_name='gate_pulse_duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)

    def _set_carrier_frequency(self, val):
        super()._set_carrier_frequency(val)
        setpoint_symbols = [self.parent.sequence.inner.symbol(), self.parent.sequence.outer.symbol()]
        sideband_symbols = [s.sideband_frequency.symbol_name for s in self.sidebanders]
        if any(s in setpoint_symbols for s in sideband_symbols):
            self.carrier_frequency._save_val(val)
            self.parent.readout.update_all_alazar()
