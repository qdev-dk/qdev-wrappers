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


#######################################


from qcodes import Instrument
from qcodes.instrument.channels import InstrumentChannel
from qcodes.instrument.parameter import Parameter
from qdev_wrappers.customised_instruments.parameters.delegate_parameter imp
from qdev_wrappers.alazar_controllers.alazar_multidim_parameters import AlazarMultiChannelParameter
from qdev_wrappers.customised_instruments.parametric_waveform_analyser.alazar_channel_ext import AlazarChannel_ext
from qdev_wrappers.alazar_controllers.acquisition_parameters import NonSettableDerivedParameter
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateMultiChannelParameter
from functools import partial
from warnings import warn


class PulseBuildingParameter(Parameter):
    def __init__(self, **kwargs):
        super().__init__(*args, **kwargs)


class Sidebander(Instrument):
    """
    An instrument which represents a sequencer and microwave drive where the
    sequencer is used to sideband the microwave drive.
    """

    def __init__(self, name, sequencer, carrier_param, full_name=None,
                 **kwargs):
        super().__init__(name)
        if full_name is not None:
            self.full_name = full_name

        self._carrier_frequency = carrier_param
        self._sequencer = sequencer

        # special pulse building parameters
        self.add_parameter(
            name='frequency',
            set_cmd=self._set_frequency,
            get_cmd=self._get_frequency)

        # pulse building parameters
        self.add_parameter(
            name='sideband_frequency',
            set_cmd=self._set_sideband,
            get_cmd=partial(self._get_pulse_building_param,
                            'sideband_frequency'),
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='I_offset',
            set_cmd=partial(self._set_pulse_building_param,
                            'I_offset'),
            get_cmd=partial(self._get_pulse_building_param,
                            'I_offset'),
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='Q_offset',
            set_cmd=partial(self._set_pulse_building_param,
                            'Q_offset'),
            get_cmd=partial(self._get_pulse_building_param,
                            'Q_offset'),
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='gain_offset',
            set_cmd=partial(self._set_pulse_building_param,
                            'gain_offset'),
            get_cmd=partial(self._get_pulse_building_param,
                            'gain_offset'),
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='phase_offset',
            set_cmd=partial(self._set_pulse_building_param,
                            'phase_offset'),
            get_cmd=partial(self._get_pulse_building_param,
                            'phase_offset'),
            parameter_class=PulseBuildingParameter)

    def _set_pulse_building_param(self, paramname, val):
        """
        Sets the parameter on the repeat channel of the sequencer where
        possible. If not then attempts to set on the sequence channel.
        """
        name = self.full_name + '_' + paramname
        if name in self._sequencer.repeat.parameters:
            self._sequencer.repeat.parameters[name](val)
        elif name in self._sequencer.sequence.parameters:
            self._sequencer.sequence.parameters[name](val)
        else:
            warn(f'Attempted to set {name} on sequencer but this '
                  'parameter was not found.')

    def _get_pulse_building_param(self, paramname, val):
        """
        Gets the parameter value from the repeat channel of the sequencer where
        possible. If not then attempts to get from the sequence channel.
        """
        if paramname in self._sequencer.repeat.parameters:
            return self._sequencer.repeat.parameters[paramname]()
        elif paramname in self._sequencer.sequence.parameters:
            return self._sequencer.sequence.parameters[paramname]()
        else:
            warn(f'Attempted to set {paramname} on sequencer but this '
                  'parameter was not found.')
            return None

    def _set_sideband(self, val):
        """
        Attempts set on the awg and then updates the frequency parameter
        """
        self._set_pulse_building_param(self.full_name + '_sideband_frequency')
        self.frequency._save_val(self._carrier_frequency() + val)

    def _set_frequency(self, val):
        """
        Sets new sidebandn to generate required frequency
        """
        new_sideband = val - self._carrier_frequency()
        self.sideband_frequency(new_sideband)

    def _get_frequency(self, val):
        """
        Calculates and returns resultant frequency
        """
        return self._carrier_frequency() + self.sideband_frequency()

    @property
    def pulse_building_parameters(self):
        return {n, p for n, p in self.parameters if
                isinstance(p, PulseBuildingParameter)}


class DriveChannel(Sidebander, InstrumentChannel):
    """
    An instrument channel which can be used to represent the drive of a single qubit.
    """

    def __init__(self, parent, name, sequencer, carrier_param, full_name=None):
        super().__init__(name=name,
                         parent=parent,
                         sequencer=sequencer,
                         carrier_param=carrier_param,
                         full_name=full_name)
        self.add_parameter(
            name='DRAG_amplitude',
            set_cmd=partial(self._set_pulse_building_param,
                            'DRAG_amplitude'),
            get_cmd=partial(self._get_pulse_building_param,
                            'DRAG_amplitude'),
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='spectroscopy_amplitude',
            set_cmd=partial(self._set_pulse_building_param,
                            'spectroscopy_amplitude'),
            get_cmd=partial(self._get_pulse_building_param,
                            'spectroscopy_amplitude'),
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='gate_amplitude',
            set_cmd=partial(self._set_pulse_building_param,
                            'gate_amplitude'),
            get_cmd=partial(self._get_pulse_building_param,
                            'gate_amplitude'),
            parameter_class=PulseBuildingParameter)


class SidebandedReadoutChannel(Sidebander, InstrumentChannel):
    def __init__(self, parent, name, sequencer, carrier_param, demod_param, pwa, full_name=None):
        super().__init__(name=name,
                         parent=parent,
                         sequencer=sequencer,
                         carrier_param=carrier_param,
                         full_name=full_name)
        self._base_demod_param = demod_param

        # restructuring so that each readout channel does not have access
        # to shared pulse building settings
        del self.parameters['I_offset']
        del self.parameters['Q_offset']
        del self.parameters['gain_offset']
        del self.parameters['phase_offset']

        # updating the frequency parameter to additionaly update demodulation
        # frequencies
        freq_param = self.parameters.pop('frequency')
        self.add_parameter(name='frequency',
                           set_fn=self._set_frequency,
                           source=freq_param)

        # creating alazar channels and adding the channellist and
        # multichanparam to the instrument
        alazar_channels = self._create_alazar_channels(settings)
        alazar_chan_list = ChannelList(
            self, 'alazar_channels', AlazarChannel_ext,
            multichan_paramclass=AlazarMultiChannelParameter,
            chan_list=alazar_channels)
        self.add_submodule('alazar_channels', alazar_chan_list)
        self.parameters['data'] = DelegateMultiChannelParameter(
            'data', self, alazar_chan_list, set_allowed=False)

    def _set_frequency(self, val):
        new_demod = val - self._carrier_param() + self._base_demod_param()
        self.alazar_channels.demod_freq(val)
        super()._set_frequency(val)

    def _create_alazar_channels(self, pwa):
        """
        Create alazar channel pair based on the pwa settings dictionary to
        readout at this sidebanded frequency. Put channels alazar_channels
        submodule and pwa._alazar_controller.channels.
        """
        settings = pwa.alazar_ch_settings
        chan1 = AlazarChannel_ext(
            parent=pwa._alazar_controller,
            name=self.full_name + '_realmag',
            demod=True,
            average_records=settings['average_records'],
            average_buffers=settings['average_buffers'],
            integrate_samples=pwa.readout.integrate_time())
        chan2 = AlazarChannel_ext(
            parent=pwa._alazar_controller,
            name=self.full_name + '_imaginaryphase',
            demod=True,
            average_records=settings['average_records'],
            average_buffers=settings['average_buffers'],
            integrate_samples=pwa.readout.integrate_time())
        if pwa.readout.demodulation_type() == 'magphase':
            chan1.demod_type('magnitude')
            chan1.data.label = f'Q{self.ch_num} Magnitude'
            chan2.demod_type('phase')
            chan2.data.label = f'Q{self.ch_num} Phase'
        else:
            chan1.demod_type('real')
            chan1.data.label = f'Q{self.ch_num} Real'
            chan2.demod_type('imag')
            chan2.data.label = f'Q{self.ch_num} Imaginary'
        for ch in (chan1, chan2):
            pwa._alazar_controller.channels.append(ch)
            ch.demod_freq(self.demodulation_frequency())
