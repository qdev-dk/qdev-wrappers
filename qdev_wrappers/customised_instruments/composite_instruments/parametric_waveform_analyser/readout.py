from functools import partial
from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qcodes.utils import validators as vals
from typing import Optional
from warnings import warn
from qdev_wrappers.customised_instruments.composite_instruments.sidebander.sidebander import Sidebander
from qdev_wrappers.customised_instruments.composite_instruments.sidebander.pulse_building_parameter import PulseBuildingParameter
from qdev_wrappers.customised_instruments.composite_instruments.multiplexer.multiplexer import Multiplexer
from qdev_wrappers.customised_instruments.composite_instruments.parametric_sequencer.parametric_sequencer import ParametricSequencer
from qdev_wrappers.customised_instruments.composite_instruments.parametric_waveform_analyser.alazar_channel_ext import AlazarChannel_ext
from qdev_wrappers.customised_instruments.composite_instruments.heterodyne_source.heterodyne_source import HeterodyneSource
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateParameter
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateMultiChannelParameter
from qcodes.utils.helpers import create_on_off_val_mapping


class ReadoutSidebander(InstrumentChannel, Sidebander):
    def __init__(self, parent, name: str,
                 sequencer: ParametricSequencer,
                 carrier: HeterodyneSource,
                 symbol_prepend: Optional[str]=None):
        super().__init__(parent=parent,
                         name=name,
                         sequencer_name=sequencer.name,
                         carrier_if_name=carrier.name,
                         symbol_prepend=symbol_prepend)
        del self.parameters['I_offset']
        del self.parameters['Q_offset']
        del self.parameters['gain_offset']
        del self.parameters['phase_offset']

        alazar_chan_list = ChannelList(
            self, 'alazar_channels', AlazarChannel_ext)
        self._alazar_channels = alazar_chan_list
        settings = self.root_instrument.get_alazar_ch_settings()
        self._create_alazar_channels(settings)
        self.add_parameter(name='data',
                           channels=alazar_chan_list,
                           param_name='data',
                           set_allowed=False,
                           get_fn=self._check_seq_updated,
                           parameter_class=DelegateMultiChannelParameter)
        self.add_parameter(name='demodulation_frequency',
                           set_fn=False)
        self.sideband_frequency._save_val(0)
        self.amplitude._save_val(1)
        self.state._save_val(1)
        demod_freq = self.parent.carrier_frequency() + \
            self.parent.base_demodulation_frequency()
        self._set_demod_frequency(demod_freq)


    def _set_frequency(self, val):
        super()._set_frequency(val)
        new_demod = val - self.parent.carrier_frequency() + \
            self.parent.base_demodulation_frequency()
        self._set_demod_frequency(new_demod)

    def _set_demod_frequency(self, val):
        try: 
            self._alazar_channels.demod_freq(val)
        except IndexError:
            pass
        self.demodulation_frequency._save_val(val)

    def _check_seq_updated(self):
        if not self.root_instrument.sequence._sequencer_up_to_date:
            raise RuntimeError('Sequence not up to date')

    def update_alazar(self):
        pwa = self.root_instrument
        settings = pwa.get_alazar_ch_settings()
        if settings is None:
            warn('Alazar will not be updated until sequencer is updated.')
        else:
            reinstate_needed = False
            for ch in self._alazar_channels:
                try:
                    ch.update(settings)
                except RuntimeError:
                    reinstate_needed = True
                    pwa.alazar_controller.channels.remove(ch)
            if reinstate_needed:
                self._alazar_channels.clear()
                self._create_alazar_channels(settings=settings)
                for ch in self._alazar_channels:
                    ch.update(settings)
            self.data.update()

    def _create_alazar_channels(self, settings):
        """
        Create alazar channel pair based on the pwa settings dictionary to
        readout at this sidebanded frequency. Put channels alazar_channels
        submodule and pwa.alazar_controller.channels.
        """
        pwa = self.root_instrument
        if settings is None:
            settings = {'average_records': True,
                        'average_buffers': True,
                        'integrate_time': True,
                        'records': 1,
                        'buffers': 1}
        chan1 = AlazarChannel_ext(
            parent=pwa.alazar_controller,
            name=self.full_name + '_realmag',
            demod=True,
            average_records=settings['average_records'],
            average_buffers=settings['average_buffers'],
            integrate_samples=settings['integrate_time'])
        chan2 = AlazarChannel_ext(
            parent=pwa.alazar_controller,
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
        for ch in [chan1, chan2]:
            self._alazar_channels.append(ch) 
            pwa.alazar_controller.channels.append(ch)


class ReadoutChannel(InstrumentChannel, Multiplexer):
    SIDEBANDER_CLASS = ReadoutSidebander

    def __init__(self, parent, name: str,
                 sequencer: ParametricSequencer,
                 carrier: HeterodyneSource,
                 alazar_controller):
        super().__init__(parent=parent, name=name, sequencer_name=sequencer.name,
                         carrier_if_name=carrier.name)
        self.alazar_controller = alazar_controller
        self.add_parameter(name='data',
                           channels=alazar_controller.channels,
                           param_name='data',
                           set_allowed=False,
                           get_fn=self._check_seq_updated,
                           parameter_class=DelegateMultiChannelParameter)

        # heterodyne source parameters
        self.add_parameter(name='carrier_power',
                           source=carrier.power,
                           parameter_class=DelegateParameter)
        self.add_parameter(name='state',
                           source=carrier.state,
                           parameter_class=DelegateParameter)
        self.add_parameter(name='base_demodulation_frequency',
                           set_fn=self._set_base_demod_frequency,
                           source=carrier.demodulation_frequency,
                           label='Base Demodulation Frequency',
                           parameter_class=DelegateParameter)
        self.add_parameter(name='carrier_pulse_modulation_state',
                           source=carrier.pulse_modulation_state,
                           parameter_class=DelegateParameter)
        self.add_parameter(name='carrier_IQ_modulation_state',
                           source=carrier.IQ_modulation_state,
                           parameter_class=DelegateParameter)

        # alazar channel parameters
        self.add_parameter(name='demodulation_type',
                           set_cmd=partial(self._set_alazar_parm,
                                           'demodulation_type'),
                           vals=vals.Enum('magphase', 'realimag'))
        self.add_parameter(name='single_shot',
                           set_cmd=partial(self._set_alazar_parm,
                                           'single_shot'),
                           val_mapping=create_on_off_val_mapping())
        self.add_parameter(name='num',
                           set_cmd=partial(self._set_alazar_parm,
                                           'num'),
                           vals=vals.Ints())
        self.add_parameter(name='average_time',
                           set_cmd=partial(self._set_alazar_parm,
                                           'average_time'),
                           val_mapping=create_on_off_val_mapping())
        self.average_time._latest['raw_value'] = True
        self.single_shot._latest['raw_value'] = False

        # alazar controller parameters
        self.add_parameter(name='measurement_duration',
                           label='Measurement Duration',
                           unit='s',
                           set_cmd=partial(self._set_alazar_parm,
                                           'measurement_duration'))
        self.add_parameter(name='measurement_delay',
                           label='Measurement Delay',
                           unit='s',
                           set_cmd=partial(self._set_alazar_parm,
                                           'measurement_delay'))

        # pulse building parameters
        self.add_parameter(name='cycle_duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='marker_duration',
                           symbol_name='readout_marker_duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='marker_readout_delay',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='pulse_duration',
                           symbol_name='readout_pulse_duration',
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
            s._set_demod_frequency(demod)

    def _set_alazar_parm(self, paramname, val):
        self.parameters[paramname]._save_val(val)
        if paramname == 'demodulation_type':
            for s in self.sidebanders:
                if val == 'magphase':
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
            self.update_all_alazar()
        elif paramname in ['measurement_duration', 'measurement_delay']:
            if paramname == 'measurement_duration':
                param = self.alazar_controller.parameters['int_time']
            else:
                param = self.alazar_controller.parameters['int_delay']
            param(val)
            if not self.average_time():
                self.update_all_alazar()

    def _check_seq_updated(self):
        if not self.parent.sequence._sequencer_up_to_date:
            raise RuntimeError('Sequence not up to date')

    def update_all_alazar(self):
        for s in self.sidebanders:
            s.update_alazar()
        self.data.update()

