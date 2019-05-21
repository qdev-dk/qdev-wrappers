from functools import partial
from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qdev_wrappers.customised_instruments.composite_instruments.sidebander.sidebander import Sidebander
from qdev_wrappers.customised_instruments.composite_instruments.sidebander.pulse_building_parameter import PulseBuildingParameter
from qdev_wrappers.customised_instruments.composite_instruments.multiplexer.multiplexer import Multiplexer
from qdev_wrappers.customised_instruments.composite_instruments.parametric_sequencer.parametric_sequencer import ParametricSequencer
from qdev_wrappers.customised_instruments.interfaces.microwave_source_interface import MicrowaveSourceInterface
from qdev_wrappers.customised_instruments.composite_instruments.heterodyne_source.heterodyne_source import HeterodyneSource
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateParameter
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateMultiChannelParameter


class ReadoutSidebander(InstrumentChannel, Sidebander):
    def __init__(self, parent, name: str,
                 sequencer: ParametricSequencer,
                 carrier: HeterodyneSource):
        super().__init__(parent=parent,
                         name=name,
                         sequencer=sequencer,
                         carrier=carrier,
                         pulse_building_prepend=True)
        self._alazar_up_to_date = False
        del self.parameters['I_offset']
        del self.parameters['Q_offset']
        del self.parameters['gain_offset']
        del self.parameters['phase_offset']

        alazar_channels = self._create_alazar_channels()
        alazar_chan_list = ChannelList(
            self, 'alazar_channels', AlazarChannel_ext,
            multichan_paramclass=AlazarMultiChannelParameter,
            chan_list=alazar_channels)
        self._alazar_channels = alazar_chan_list
        self.add_parameter(name='data',
                           channels=alazar_chan_list,
                           paramname='data',
                           set_allowed=False,
                           get_fn=self._check_updated,
                           parameter_class=DelegateMultiChannelParameter)
        self.add_parameter(name='demodulation_frequency',
                           set_fn=False)

    def _set_frequency(self, val):
        super()._set_frequency(val)
        new_demod = val - self.parent.carrier_frequency() + \
            self.parent.base_demodulation_frequency()
        self._set_demod_frequency(val)

    def _set_demod_frequency(self, val):
        self._alazar_channels.demod_freq(val)
        self._demodulation_frequency._save_val(val)

    def _check_updated(self):
        if not self.root_instrument.sequence._sequencer_up_to_date:
            raise RuntimeError('Sequence not up to date')
        if not self._alazar_up_to_date:
            self.update_alazar()

    def update_alazar(self):
        pwa = self.root_instrument
        settings = pwa.alazar_ch_settings
        reinstate_needed = False
        for ch in self._alazar_channels:
            try:
                ch.update(settings)
            except RuntimeError:
                reinstate_needed = True
        if reinstate_needed:
            self._alazar_channels.clear()
            self._create_alazar_channel_pair(settings)
        self._alazar_up_to_date = True

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
            integrate_samples=settings['integrate_time'])
        chan2 = AlazarChannel_ext(
            parent=pwa._alazar_controller,
            name=self.full_name + '_imaginaryphase',
            demod=True,
            average_records=settings['average_records'],
            average_buffers=settings['average_buffers'],
            integrate_samples=settings['integrate_time'])
        if pwa.readout.demodulation_type() == 'magphase':
            chan1.demod_type('magnitude')
            chan1.data.label = f'{self.name} Magnitude'
            chan2.demod_type('phase')
            chan2.data.label = f'{self.name} Phase'
        else:
            chan1.demod_type('real')
            chan1.data.label = f'{self.name} Real'
            chan2.demod_type('imag')
            chan2.data.label = f'{self.name} Imaginary'
        for ch in (chan1, chan2):
            pwa._alazar_controller.channels.append(ch)
        return [chan1, chan2]


class ReadoutChannel(InstrumentChannel, Multiplexer):
    SIDEBANDER_CLASS = ReadoutSidebander

    def __init__(self, parent, name: str,
                 sequencer: ParametricSequencer,
                 carrier: HeterodyneSource,
                 alazar_controller):
        super().__init__(parent=parent, name=name, sequencer=sequencer,
                         carrier=carrier, **kwargs)
        self.alazar_controller = alazar_controller
        self.add_parameter(name='data',
                           channels=alazar_controller.channels,
                           paramname='data',
                           set_allowed=False,
                           get_fn=self._check_all_updated,
                           parameter_class=DelegateMultiChannelParameter)

        # heterodyne source parameters
        self.add_parameter(name='base_demodulation_frequency',
                           set_fn=self._set_base_demod_frequency,
                           source=carrier.demodulation_frequency,
                           label='Base Demodulation Frequency',
                           parameter_class=DelegateParameter)
        self.base_demodulation_frequency()
        self.carrier_frequency()
        self.carrier_status()

        # alazar controller parameters
        self.add_parameter(name='measurement_duration',
                           label='Measurement Duration',
                           unit='s',
                           set_cmd=partial(self._set_alazar_parm,
                                           'int_time'))
        self.add_parameter(name='measurement_delay',
                           label='Measurement Delay',
                           unit='s',
                           set_cmd=partial(self._set_alazar_parm,
                                           'int_delay'))

        # alazar channel parameters
        self.add_parameter(name='demodulation_type',
                           set_cmd=partial(self._set_alazar_parm,
                                           'demod_type'),
                           vals=vals.Enum('magphase', 'realimag'))
        self.add_parameter(name='single_shot',
                           set_cmd=partial(self._set_alazar_parm,
                                           'single_shot'),
                           vals=vals.Bool())
        self.add_parameter(name='num',
                           set_cmd=partial(self._set_alazar_parm,
                                           'num'),
                           vals=vals.Ints(),)
        self.add_parameter(name='average_time',
                           set_cmd=partial(self._set_alazar_parm,
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
        self.add_parameter(name='I_offset',
                           symbol_name='readout_I_offset',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='Q_offset',
                           symbol_name='readout_Q_offset',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='gain_offset',
                           symbol_name='readout_gain_offset',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='phase_offset',
                           symbol_name='readout_phase_offset',
                           parameter_class=PulseBuildingParameter)

    def _set_base_demod_frequency(self, val):
        for s in self.sidebanders:
            demod = s.frequency() - self.carrier_frequency() + val
            s._set_demod_frequency(demod)

    def _set_carrier_frequency(self, val):
        super()._set_carrier_frequency(val)
        for s in self.sidebanders:
            demod = s.frequency() - val + self.base_demodulation_frequency()
            s._set_demod_frequency(val)

    def _set_alazar_parm(self, paramname, val):
        if paramname == 'demod_type':
            for s in self.sidebanders:
                if demod_type == 'magphase':
                    s._alazar_channels[0].demod_type('magnitude')
                    s._alazar_channels[0].data.label = f'{s.name} Magnitude'
                    s._alazar_channels[1].demod_type('phase')
                    s._alazar_channels[1].data.label = f'{s.name} Phase'
                else:
                    s._alazar_channels[0].demod_type('real')
                    s._alazar_channels[0].data.label = f'{s.name} Real'
                    s._alazar_channels[1].demod_type('imag')
                    s._alazar_channels[1].data.label = f'{s.name} Imaginary'
        elif paramname in ['single_shot', 'num', 'average_time']:
            self.set_alazar_not_up_to_date()
        elif paramname in ['int_time', 'int_delay']:
            self.alazar_controller.parameters[paramname](val)
            if not self.average_time():
                self.set_alazar_not_up_to_date()

    def _check_all_updated(self):
        if not self.parent.sequence._sequencer_up_to_date:
            raise RuntimeError('Sequence not up to date')
        self.update_all_alazar()

    def update_all_alazar(self):
        for s in self.sidebanders:
            if not s._alazar_up_to_date:
                s.update_alazar()

    def set_alazar_not_up_to_date(self):
        for s in self.sidebanders:
            self._alazar_up_to_date = False
