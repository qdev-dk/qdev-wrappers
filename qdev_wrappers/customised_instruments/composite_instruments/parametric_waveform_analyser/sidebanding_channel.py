from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qdev_wrappers.alazar_controllers.alazar_multidim_parameters import AlazarMultiChannelParameter
from qdev_wrappers.customised_instruments.composite_instruments.parametric_waveform_analyser.parameters import AlazarMultiChannelParameterHack, PulseBuildingParameter
from typing import Optional, Dict, Union
from qdev_wrappers.alazar_controllers.acquisition_parameters import NonSettableDerivedParameter
from qdev_wrappers.customised_instruments.composite_instruments.parametric_waveform_analyser.alazar_channel_ext import AlazarChannel_ext

class SidebandingChannel(InstrumentChannel):
    """
    An InstrumentChannel intended to belong to a ReadoutChannel or a
    DriveChannel of a ParametricWaveformAnalyser. A SidebandingChannel
    is used to control and keep track of the drive (readout) signal
    at one frequency (eg for one qubit) and also contains the
    PulseBuildingParameters which relate to the parts of the
    pulse sequence which generate the sideband signal.

    A carrier microwave source is assumed, the signal of which is mixed
    with a signal at the 'sideband_frequency' to produce a signal at the
    'frequency'.
    """

    # TODO: add power parameter which takes into account carrier_power,
    #   awg channel amplitude and pulse amplitude

    def __init__(self, parent, name: str, ch_num: int):
        super().__init__(parent, name)
        self.ch_num = ch_num
        if isinstance(self, ReadoutSidebandingChannel):
            str_type = 'readout'
        elif isinstance(self, DriveSidebandingChannel):
            str_type = 'drive'
        else:
            raise RuntimeError(
                'SidebandingChannel should not be used outside of child'
                'class.')
        pre_str = f'Q{ch_num}_{str_type}'
        self.add_parameter(name='sideband_frequency',
                           pulse_building_name='{pre_str}_sideband_frequency',
                           set_fn=False,
                           docstring='set via frequency or'
                           'readout.carrier_frequency',
                           parameter_class=PulseBuildingParameter)

        self.add_parameter(name='frequency',
                           set_cmd=self.update,
                           docstring='Sets sideband frequency '
                           'in order to get the required '
                           'drive and updates the demodulation '
                           'frequencies on the relevant '
                           'alazar channels if relevant')

        self.frequency._save_val(self._parent.carrier_frequency())
        self.sideband_frequency._save_val(0)

    @property
    def _pulse_building_parameters(self):
        return {p.pulse_building_name: p for p in self.parameters.values() if
                isinstance(p, PulseBuildingParameter)}

    def update(self, frequency: Optional[float]=None):
        """
        Based on the carrier frequency the sideband and drive
        frequencies are updated (and the demodulation_frequency where
        relevant). If a drive is specified then this is used to choose
        the sideband_frequency and the sequence is updated, otherwise
        the existing sideband value is used and the frequency
        is updated.
        """

        # get old sideband and drive and new carrier and drive
        old_sideband = self.sideband_frequency()
        old_drive = self.frequency()
        carrier = self._parent.carrier_frequency()
        drive = frequency

        # if drive is specified sets sidebend from drive, if not sets
        # drive from sideband.
        if drive is not None:
            sideband = carrier - drive
        else:
            sideband = old_sideband
            drive = carrier - sideband

        self.sideband_frequency._save_val(sideband)
        self.frequency._save_val(drive)

        # if sideband has changed updates the parameter, uploads a new
        # sequence and updates the alazar channels demod freqs,
        # if the drive has changed updates the alazar channels setpoints
        # NB: This assumes that the readout frequencies are not swept in seq
        #   mode with the alazar
        if sideband != old_sideband:
            if not self._parent._parent.sequence.suppress_sequence_upload:
                self._parent._parent.sequence._update_sequence()
        elif drive != old_drive:
            self._update_alazar(sideband)

    def _update_alazar(self):
        raise NotImplementedError


class DriveSidebandingChannel(SidebandingChannel):
    """
    A SidebandingChannel inteded to model a drive tone and as such also
    contains the pulse building parameters for the specific qubit drive.
    """

    def __init__(self, parent, name: str, ch_num: int):
        super().__init__(parent, name, ch_num)
        pre_str = f'Q{ch_num}_drive'
        self.add_parameter(name='I_offset',
                           pulse_building_name='{pre_str}_I_offset',
                           label='I Offset',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='Q_offset',
                           pulse_building_name='{pre_str}_Q_offset',
                           label='Q Offset',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='gain_offset',
                           pulse_building_name='{pre_str}_gain_offset',
                           label='Gain Offset',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='phase_offset',
                           pulse_building_name='{pre_str}_phase_offset',
                           label='Phase Offset',
                           unit='degrees',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='DRAG_amplitude',
                           pulse_building_name='{pre_str}_DRAG_amplitude',
                           label='DRAG amplitude',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='spectroscopy_pulse_amplitude',
            pulse_building_name='{pre_str}_spectroscopy_pulse_amplitude',
            label='Spectroscopy Pulse Amplitude',
            unit='s',
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='gate_pulse_amplitude',
            pulse_building_name='{pre_str}_gate_pulse_amplitude',
            label='Gate Pulse Amplitude',
            unit='s',
            parameter_class=PulseBuildingParameter)

    def _update_alazar(self):
        self._parent._parent.readout._update_alazar_channels()


class ReadoutSidebandingChannel(SidebandingChannel):
    """
    A SidebandingChannel inteded to model a readout tone using
    heterodyne readout. It is assumed that this is done by mixing
    the signal from the carrier down with the signal from a localos
    microwave souce (which together with the carrier microwave source
    comprises a heterodyne_source) to produce a signal at
    'demodulation_frequency' which can be measured using an Alazar card.
    In this case both a 'demodulation_frequency' parameter and an
    'alazar_channels' ChannelList of the associated alazar
    channels are effective attributes.
    """

    def __init__(self, parent, name: str, ch_num: int):
        super().__init__(parent, name, ch_num)
        initial_demod_freq = self._parent.base_demodulation_frequency()
        pre_str = f'Q{ch_num}_readout'
        self.add_parameter(name='demodulation_frequency',
                           alternative='frequency',
                           parameter_class=NonSettableDerivedParameter)
        self.add_parameter(name='pulse_amplitude',
                           pulse_building_name='{pre_str}_pulse_amplitude',
                           label='Pulse Amplitude',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.demodulation_frequency._save_val(initial_demod_freq)
        alazar_chan_list = ChannelList(
            self, 'alazar_channels', AlazarChannel_ext,
            multichan_paramclass=AlazarMultiChannelParameter)
        self.add_submodule('alazar_channels', alazar_chan_list)
        multichanalazarparam = AlazarMultiChannelParameterHack(
            'data', self, alazar_chan_list)
        self.parameters['data'] = multichanalazarparam
        settings = self._parent._parent.alazar_channel_settings
        self._create_alazar_channel_pair(settings)

    def _update_alazar(self, new_sideband):
        base_demod = self._parent.base_demodulation_frequency()
        demod = base_demod + new_sideband
        self.demodulation_frequency._save_val(abs(demod))
        for ch in self.alazar_channels:
            ch.demod_freq(initial_demod_freq)

    def _create_alazar_channel_pair(
            self, settings: Dict[str, Union[int, float, str, bool]]):
        """
        Create alazar channel pair based on the settings dictionary to readout
        at this sidebanded frequency. Put channels alazar_channels submodule
        and pwa._alazar_controller.channels.
        """
        chan1 = AlazarChannel_ext(
            self._parent._parent._alazar_controller,
            name=f'Q{self.ch_num}_realmag',
            demod=True,
            average_records=settings['average_records'],
            average_buffers=settings['average_buffers'],
            integrate_samples=self._parent.integrate_time())
        chan2 = AlazarChannel_ext(
            self._parent._parent._alazar_controller,
            name=f'Q{self.ch_num}_imaginaryphase',
            demod=True,
            average_records=settings['average_records'],
            average_buffers=settings['average_buffers'],
            integrate_samples=self._parent.integrate_time())
        if self._parent.demodulation_type() == 'magphase':
            chan1.demod_type('magnitude')
            chan1.data.label = f'Q{self.ch_num} Magnitude'
            chan2.demod_type('phase')
            chan2.data.label = f'Q{self.ch_num} Phase'
        else:
            chan1.demod_type('real')
            chan1.data.label = f'Q{self.ch_num} Real'
            chan2.demod_type('imag')
            chan2.data.label = f'Q{self.ch_num} Imaginary'
        for ch in alazar_chans:
            self.alazar_channels.append(ch)
            self._parent._parent._alazar_controller.channels.append(ch)
            ch.demod_freq(self.demodulation_frequency())
