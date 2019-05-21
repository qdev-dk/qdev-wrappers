from functools import partial
from typing import Union
from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qdev_wrappers.customised_instruments.composite_instruments.sidebander.sidebander import Sidebander
from qdev_wrappers.customised_instruments.composite_instruments.sidebander.pulse_building_parameter import PulseBuildingParameter
from qdev_wrappers.customised_instruments.composite_instruments.multiplexer.multiplexer import Multiplexer
from qdev_wrappers.customised_instruments.composite_instruments.parametric_sequencer.parametric_sequencer import ParametricSequencer
from qdev_wrappers.customised_instruments.interfaces.microwave_source_interface import MicrowaveSourceInterface
from qdev_wrappers.customised_instruments.composite_instruments.heterodyne_source.heterodyne_source import HeterodyneSource
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateParameter
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateMultiChannelParameter


class DriveSidebander(InstrumentChannel, Sidebander):
    def __init__(self, parent, name: str,
                 sequencer: ParametricSequencer,
                 carrier: Union[MicrowaveSourceInterface, HeterodyneSource]):
        super().__init__(parent=parent,
                         name=name,
                         sequencer=sequencer,
                         carrier=carrier,
                         pulse_building_prepend=True)
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
        super().__init__(parent=parent, name=name, sequencer=sequencer,
                         carrier=carrier)
        self._pulse_building_prepend = False

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

    def _set_carrier_frequency(self, val):
        super()._set_carrier_frequency(val)
        setpoint_symbols = [self.sequencer.inner_setpoints[0], self.sequencer.outer_setpoints[0]]
        sideband_symbols = [s.sideband_frequency.symbol_name for s in self.sidebanders]
        if any(s in setpoint_symbols for s in sideband_symbols):
            self.parent.readout.set_alazar_not_up_to_date()
