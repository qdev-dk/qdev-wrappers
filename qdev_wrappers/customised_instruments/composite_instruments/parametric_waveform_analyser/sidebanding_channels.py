from qcodes import Instrument
from qcodes.instrument.channels import InstrumentChannel
from qdev_wrappers.alazar_controllers.alazar_multidim_parameters import AlazarMultiChannelParameter
from qdev_wrappers.customised_instruments.parametric_waveform_analyser.alazar_channel_ext import AlazarChannel_ext
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateMultiChannelParameter
from qdev_wrappers.customised_instruments.composite_instrument.sidebander import Sidebander
from qdev_wrappers.customised_instruments.composite_instrument.sidebander.pulse_building_parameter import PulseBuildingParameter
from functools import partial


class DriveChannel(Sidebander, InstrumentChannel):
    """
    An instrument channel which can be used to represent the drive of a single
    qubit.
    """

    def __init__(self, parent, name, sequencer, carrier, full_name=None):
        super().__init__(name=name,
                         parent=parent,
                         sequencer=sequencer,
                         carrier=carrier)
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


class SidebandedReadoutChannel(Sidebander, InstrumentChannel):
    """
    An instrument channel which can be used to represent the drive of a single
    qubit. Assumes the root instrument is a parametric waveform analyser.
    """

    def __init__(self, parent, name, sequencer, heterodyne_source):
        super().__init__(name=name,
                         parent=parent,
                         sequencer=sequencer,
                         carrier=heterodyne_source)
        self._base_demod_param = heterodyne_source.demodulation_frequency

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
        alazar_channels = self._create_alazar_channels()
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

    def _create_alazar_channels(self):
        """
        Create alazar channel pair based on the pwa settings dictionary to
        readout at this sidebanded frequency. Put channels alazar_channels
        submodule and pwa._alazar_controller.channels.
        """
        pwa = self.root_instrument
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
            chan1.data.label = f'Q{self.full_name} Magnitude'
            chan2.demod_type('phase')
            chan2.data.label = f'Q{self.full_name} Phase'
        else:
            chan1.demod_type('real')
            chan1.data.label = f'Q{self.full_name} Real'
            chan2.demod_type('imag')
            chan2.data.label = f'Q{self.full_name} Imaginary'
        for ch in (chan1, chan2):
            pwa._alazar_controller.channels.append(ch)
            ch.demod_freq(self.demodulation_frequency())
