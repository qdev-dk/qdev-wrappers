from qcodes.instrument.base import Instrument
from qdev_wrappers.customised_instruments.composite_instruments.parametric_sequencer.parametric_sequencer import ParametricSequencer


# from qcodes.utils import validators as vals
# from qcodes.instrument.parameter import Parameter
# from contextlib import contextmanager
# from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateParameter, DelegateMultiChannelParameter
# from qdev_wrappers.customised_instruments.composite_instruments.parametric_waveform_analyser.pulse_building_parameter import PWAPulseBuildingParameter
# from qdev_wrappers.customised_instruments.composite_instruments.parametric_waveform_analyser.sidebanding_channels import SidebandedDriveChannel, SidebandedReadoutChannel


# class CarrierFreqParam(Parameter):
#     def set_raw(self, val):
#         self.instrument._microwave_source.frequency(val)
#         self._save_val(val)
#         for demod_ch in self.instrument._sidebanding_channels:
#             demod_ch.update()


class MixingChannel(Instrument):
    """
    An InstrumentChannel intended to belong to a ParametricWaveformAnalyser
    and which effectively groups the parameters related to readout including
    heterodyne_source parameters, alazar_controller parameters and
    PulseBuildingParameters. I models a carrier tone is mixed with
    sidebanding tones which are added as SidebandingChannels.
    """

    def __init__(self, name: str,
                 sequencer: ParametricSequencer,
                 carrier,
                 **kwargs):
        super().__init__(name, **kwargs)
        self.carrier = carrier
        self.sequencer = sequencer
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
            name='')
        sidebanding_channel_list = 


        self._sidebanding_channels = []
        type_title = self._str_type.title()
        self.add_parameter(
            name='carrier_frequency',
            label=f'{type_title} Carrier Frequency',
            unit='Hz',
            initial_value=self._microwave_source.frequency(),
            docstring='Sets the frequency on the '
            'heterodyne_source and updates the sidebanding '
            'channels so that their frequencies are still'
            ' carrier + sideband.',
            parameter_class=CarrierFreqParam)
        self.add_parameter(
            name='carrier_power',
            label=f'{type_title} Power',
            unit='dBm',
            parameter_class=DelegateParameter,
            source=self._microwave_source.power)
        self.add_parameter(
            name='status',
            label=f'{type_title} Status',
            parameter_class=DelegateParameter,
            source=self._microwave_source.status)

    @property
    def _pulse_building_parameters(self):
        pulse_building_parameters = {}
        for n, p in self.parameters.items():
            if isinstance(p, PWAPulseBuildingParameter):
                pulse_building_parameters[p.pulse_building_name] = p
        for demod_ch in self._sidebanding_channels:
            pulse_building_parameters.update(
                demod_ch._pulse_building_parameters)
        return pulse_building_parameters

    def _add_sidebanding_channel(self, frequency):
        """
        Creates a SidebandingChannel with a frequency as
        specified.
        """
        ch_num = len(self._sidebanding_channels)
        if isinstance(self, ReadoutChannel):
            sidebanding_chan_class = SidebandedReadoutChannel
        elif isinstance(self, DriveChannel):
            sidebanding_chan_class = SidebandedDriveChannel
        else:
            raise RuntimeError('Could not identify parent class when '
                               ' trying to make sidebanding channel')
        sidebanding_channel = sidebanding_chan_class(
            self, f'Q{ch_num}_{self._str_type}', ch_num, frequency)
        self._sidebanding_channels.append(sidebanding_channel)
        self.add_submodule(f'Q{ch_num}', sidebanding_channel)

    @contextmanager
    def sideband_update(self):
        """
        Can be used for maintaining the drive_frequencies of the
        SidebandingChannels while changing the carrier_frequency
        """
        old_drives = [demod_ch.frequency()
                      for demod_ch in self._sidebanding_channels]
        yield
        for i, demod_ch in enumerate(self.demod_chan_sidebanding_channelsnels):
            demod_ch.update(drive=old_drives[i])


class DriveChannel(MixingChannel):
    """
    A MixingChannel which models the qubit(s) drive and thus has the requisite
    PulseBuildingParameters
    """

    def __init__(self, parent, name: str):
        super().__init__(parent, name)

        # pulse building parameters
        self.add_parameter(name='stage_duration',
                           label='Drive Stage Duration',
                           unit='s',
                           pulse_building_name=f'drive_stage_duration',
                           parameter_class=PWAPulseBuildingParameter)
        self.add_parameter(name='sigma_cutoff',
                           label='Sigma Cutoff',
                           parameter_class=PWAPulseBuildingParameter)
        self.add_parameter(name='drive_readout_delay',
                           label='Drive Readout Delay',
                           unit='s',
                           parameter_class=PWAPulseBuildingParameter)
        self.add_parameter(name='modulation_marker_duration',
                           label='Drive Modulation Duration',
                           unit='s',
                           parameter_class=PWAPulseBuildingParameter)
        self.add_parameter(name='pulse_separation',
                           label='Drive Pulse Separation',
                           unit='s',
                           parameter_class=PWAPulseBuildingParameter)
        self.add_parameter(name='spectroscopy_pulse_duration',
                           pulse_building_name='spectroscopy_pulse_duration',
                           label='Drive Pulse Duration',
                           unit='s',
                           parameter_class=PWAPulseBuildingParameter)
        self.add_parameter(name='gate_pulse_duration',
                           pulse_building_name='gate_pulse_duration',
                           label='Drive Pulse Duration',
                           unit='s',
                           parameter_class=PWAPulseBuildingParameter)


class ReadoutChannel(MixingChannel):
    """
    A MixingChannel which models the qubit(s) readout and thus has the
    requisite PulseBuildingParameters, a multichanal parmeter for aquiring
    data from all alazar channels and the requisite alzar controller
    parameters.
    """

    def __init__(self, parent, name: str):
        super().__init__(parent, name)
        self.all_readout_channels = parent._alazar_controller.channels
        multichanalazarparam = DelegateMultiChannelParameter(
            'data', self, parent._alazar_controller.channels, 'data')
        self.parameters['data'] = multichanalazarparam
        # heterodyne source parameters

        self.add_parameter(
            name='base_demodulation_frequency',
            set_cmd=self._set_base_demod_frequency,
            label='Base Demodulation Frequency',
            unit='Hz',
            initial_value=self._microwave_source.demodulation_frequency(),
            docstring='Sets the frequency difference '
            'between the carrier source and the localos '
            'source on the heterodyne source and updates '
            'the alazar channels to demodulate at this '
            'frequency plus the frequency of any sidebands.')

        # alazar controller parameters
        self.add_parameter(name='measurement_duration',
                           set_cmd=self._set_meas_dur,
                           label='Measurement Duration',
                           unit='s')
        self.add_parameter(name='measurement_delay',
                           label='Measurement Delay',
                           unit='s',
                           set_cmd=self._set_meas_delay)

        # alazar channel parameters
        self.add_parameter(name='demodulation_type',
                           set_cmd=self._set_demod_type,
                           vals=vals.Enum('magphase', 'realimag'),
                           docstring='Sets the two alazar channels '
                           'on each demodulation channel to give the '
                           'results in magnitude and phase space or '
                           'real and imaginary space')
        self.add_parameter(name='single_shot',
                           set_cmd=self._set_single_shot,
                           vals=vals.Bool())
        self.add_parameter(name='num',
                           set_cmd=self._set_num,
                           vals=vals.Ints(),
                           docstring='Number of repetitions if single_shot, '
                           'number of averages otherwise')
        self.add_parameter(name='integrate_time',
                           set_cmd=self._set_integrate_time,
                           vals=vals.Bool(),
                           docstring='Whether or not time is integrated over '
                           'in the measurement')

        # pulse building parameters
        self.add_parameter(name='total_duration',  # TODO should this live on sequence?
                           label='Cycle Duration',
                           unit='s',
                           parameter_class=PWAPulseBuildingParameter)
        self.add_parameter(name='marker_readout_delay',
                           label='Marker Readout Delay',
                           unit='s',
                           parameter_class=PWAPulseBuildingParameter)
        self.add_parameter(name='pulse_duration',
                           label='Readout Pulse Duration',
                           pulse_building_name='readout_pulse_duration',
                           unit='s',
                           parameter_class=PWAPulseBuildingParameter)
        self.add_parameter(name='marker_duration',
                           label='Marker Duration',
                           pulse_building_name='readout_marker_duration',
                           unit='s',
                           parameter_class=PWAPulseBuildingParameter)
        self.add_parameter(name='I_offset',
                           pulse_building_name='readout_I_offset',
                           label='I Offset',
                           parameter_class=PWAPulseBuildingParameter)
        self.add_parameter(name='Q_offset',
                           pulse_building_name='readout_Q_offset',
                           label='Q Offset',
                           parameter_class=PWAPulseBuildingParameter)
        self.add_parameter(name='gain_offset',
                           pulse_building_name='readout_gain_offset',
                           label='Gain Offset',
                           parameter_class=PWAPulseBuildingParameter)
        self.add_parameter(name='phase_offset',
                           pulse_building_name='readout_phase_offset',
                           label='Phase Offset',
                           unit='degrees',
                           parameter_class=PWAPulseBuildingParameter)

    def _set_base_demod_frequency(self, demod_freq):
        self._microwave_source.demodulation_frequency(demod_freq)
        for ch in self._sidebanding_channels:
            ch.update()

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

    def _set_single_shot(self, val):
        self.single_shot._save_val(val)
        self.update_alazar_channels()

    def _set_num(self, num):
        self.num._save_val(num)
        self.update_alazar_channels()

    def _set_meas_dur(self, meas_dur):
        self.parent._alazar_controller.int_time(meas_dur)
        for ch in self.all_readout_channels:
            if not ch._integrate_samples:
                ch.prepare_channel()

    def _set_meas_delay(self, meas_delay):
        self.parent._alazar_controller.int_delay(meas_delay)
        for ch in self.all_readout_channels:
            if not ch._integrate_samples:
                ch.prepare_channel()

    def _set_integrate_time(self, val):
        self.integrate_time._save_val(val)
        self.update_alazar_channels()

    def update_alazar_channels(self):
        """
        Updates all of the alazar channels based on the current settings
        of the ParametricWaveformAnalyser.
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
        This is necessary if the averaging settings
        (average_records, average_buffers, integrate_samples) are changed.
        """
        self._parent._alazar_controller.channels.clear()
        for ch in self._sidebanding_channels:
            ch.alazar_channels.clear()
            ch._create_alazar_channel_pair(settings)
