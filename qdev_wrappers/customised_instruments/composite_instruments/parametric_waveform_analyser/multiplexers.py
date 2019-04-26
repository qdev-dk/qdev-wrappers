from functools import partial
from qdev_wrappers.customised_instruments.composite_instruments.sidebander.sidebander import Sidebander
from qdev_wrappers.customised_instruments.composite_instruments.sidebander.pulse_building_parameter import PulseBuildingParameter
from qdev_wrappers.customised_instruments.composite_instruments.multiplexer.multiplexer import Multiplexer
from qdev_wrappers.customised_instruments.composite_instruments.parametric_sequencer.parametric_sequencer import ParametricSequencer
from qdev_wrappers.customised_instruments.interfaces.microwave_source_interface import MicrowaveSourceInterface
from qdev_wrappers.customised_instruments.composite_instruments.heterodyne_source.heterodyne_source import HeterodyneSource
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateParameter


class DriveSidebander(Sidebander):
    def __init__(self, name: str,
                 sequencer: ParametricSequencer,
                 carrier: Union[MicrowaveSourceInterface, HeterodyneSource],
                 pulse_building_prepend: bool=False,
                 **kwargs):
        super().__init__(name=name,
                         sequencer=sequencer,
                         carrier=carrier,
                         pulse_building_prepend=pulse_building_prepend,
                         **kwargs)
        self.add_parameter(
            name='DRAG_amplitude',
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='spectroscopy_amplitude',
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='gate_amplitude',
            set_cmd=partial(self._set_pulse_building_param,
                            'gate_amplitude'),
            get_cmd=partial(self._get_pulse_building_param,
                            'gate_amplitude'),
            parameter_class=PulseBuildingParameter)


class ReadoutSidebander(Sidebander):
    def __init__(self, name: str,
                 sequencer: ParametricSequencer,
                 carrier: Union[MicrowaveSourceInterface, HeterodyneSource],
                 pulse_building_prepend: bool=False,
                 **kwargs):
        super().__init__(name=name,
                         sequencer=sequencer,
                         carrier=carrier,
                         pulse_building_prepend=pulse_building_prepend,
                         **kwargs)
        del sidebander.parameters['I_offset']
        del sidebander.parameters['Q_offset']
        del sidebander.parameters['gain_offset']
        del sidebander.parameters['phase_offset']


class DriveChannel(InstrumentChannel, Multiplexer):
    def __init__(self, parent, name: str,
                 sequencer: ParametricSequencer,
                 carrier: Union[MicrowaveSourceInterface, HeterodyneSource],
                 **kwargs):
        super().__init__(parent=parent, name=name, sequencer=sequencer,
                         carrier=carrier, **kwargs)
        self._pulse_building_prepend = False
        # pulse building parameters
        self.add_parameter(name='stage_duration',
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
        self.add_parameter(name='drive_pulse_duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)

    # def add_qubit(self, )


class ReadoutChannel(InstrumentChannel, Multiplexer):
    SIDEBANDER_CLASS = Sidebander

    def __init__(self, parent, name: str,
                 sequencer: ParametricSequencer,
                 carrier: HeterodyneSource,
                 alazar_controller,  # TODO
                 **kwargs):
        super().__init__(parent=parent, name=name, sequencer=sequencer,
                         carrier=carrier, **kwargs)
        self.alazar_controller = alazar_controller
        self.all_readout_channels = alazar_controller.channels
        self._pulse_building_prepend = False
        multichanalazarparam = DelegateMultiChannelParameter(
            'data', self, alazar_controller.channels, 'data')
        self.parameters['data'] = multichanalazarparam

        # heterodyne source parameters
        self.add_parameter(name='base_demodulation_frequency',
                           set_fn=self._set_base_demod_frequency,
                           source=carrier.demodulation_frequency,
                           label='Base Demodulation Frequency',
                           parameter_class=DelegateParameter)
        self.base_demodulation_frequency()

        # delegate alazar controller parameters
        self.add_parameter(name='measurement_duration',
                           label='Measurement Duration',
                           unit='s',
                           set_cmd=partial(self._set_alazar_contr_param,
                                           'int_time'))
        self.add_parameter(name='measurement_delay',
                           label='Measurement Delay',
                           unit='s',
                           set_cmd=partial(self._set_alazar_contr_param,
                                           'int_delay'))

        # alazar channel parameters
        self.add_parameter(name='demodulation_type',
                           set_cmd=self._set_demod_type,
                           vals=vals.Enum('magphase', 'realimag'))
        self.add_parameter(name='single_shot',
                           set_cmd=partial(self._set_alazar_ch_parm,
                                           'single_shot'),
                           vals=vals.Bool())
        self.add_parameter(name='num',
                           set_cmd=partial(self._set_alazar_ch_parm,
                                           'num'),
                           vals=vals.Ints(),)
        self.add_parameter(name='average_time',
                           set_cmd=partial(self._set_alazar_ch_parm,
                                           'average_time'),
                           vals=vals.Bool(),)

        # pulse building parameters
        self.add_parameter(name='cycle_duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='marker_duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='marker_readout_delay',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='readout_pulse_duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='readout_I_offset',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='readout_Q_offset',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='readout_gain_offset',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='readout_phase_offset',
                           parameter_class=PulseBuildingParameter)

    def _set_base_demod_frequency(self, val):
        for s in self.sidebanding_channels:
            s.update(base_demod_freq=val)

    def _set_demod_type(self, demod_type):
        for ch in self._sidebanding_channels:
            if demod_type == 'magphase':
                ch.alazar_channels[0].demod_type('magnitude')
                ch.alazar_channels[0].data.label = f'Q{ch.ch_num} Magnitude'
                ch.alazar_channels[1].demod_type('phase')
                ch.alazar_channels[1].data.label = f'Q{ch.ch_num} Phase'
            else:
                ch.alazar_channels[0].demod_type('real')
                ch.alazar_channels[0].data.label = f'Q{ch.ch_num} Real'
                ch.alazar_channels[1].demod_type('imaginary')
                ch.alazar_channels[1].data.label = f'Q{ch.ch_num} Imaginary'

    def _set_alazar_ch_parm(self, paramname, val):
        self.parameters[paramname]._save_val(val)
        self.update_alazar_channels()

    def _set_alazar_contr_param(self, paramname, val):
        self.parent.alazar_controller.parameters[paramname](val)
        for ch in self.all_readout_channels:
            if not ch._integrate_samples:
                ch.prepare_channel()

    def add_sidebander(self):
        sidebander = super().add_sidebander()


    def update_alazar_channels(self):
        """
        Updates all of the alazar channels based on the current settings
        of the ParametricWaveformAnalyser.
        This is necessary if single_shot, num or integrate_time
        """
        settings = self._parent._get_alazar_ch_settings()
        try:
            for ch in self._parent._alazar_controller.channels:
                ch.update(settings)
        except RuntimeError:
            self._reinstate_alazar_channels(settings)

    def _reinstate_alazar_channels(self, settings):
        """
        Clears all the alazar channels and creates new ones.
        This is necessary if average_records, average_buffers or
        integrate_samples are changed.
        """
        self._parent._alazar_controller.channels.clear()
        for ch in self._sidebanding_channels:
            ch.alazar_channels.clear()
            ch._create_alazar_channel_pair(settings)
