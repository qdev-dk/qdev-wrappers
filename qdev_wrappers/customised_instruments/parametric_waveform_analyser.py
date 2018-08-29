from typing import Dict, List, Tuple, Sequence
from broadbean.element import Element
from broadbean.types import ContextDict, Symbol
import logging
import numpy as np
from contextlib import contextmanager
from qcodes import Station, Instrument, ChannelList
from qcodes.instrument.channel import InstrumentChannel
from qdev_wrappers.parameters import DelegateParameter
from qdev_wrappers.alazar_controllers.ATSChannelController import (
    ATSChannelController, AlazarMultiChannelParameter)
from qdev_wrappers.alazar_controllers.acquisition_parameters import NonSettableDerivedParameter
from qdev_wrappers.alazar_controllers.alazar_channel import AlazarChannel
from qcodes.utils import validators as vals


logger = logging.getLogger(__name__)


class AlazarChannel_ext(AlazarChannel):
    """
    An extension to the Alazar channel which has added functionality
    for nun_reps/num_averages based on whether or not it is a
    single shot channel and the settings on the associated
    parametric waveform analyser

    Args:
        parent (alazar controller)
        pwa (parametric_waveform_analyser)
        name (str)
        demod (bool, default False)
        alazar_channel (str, default A): phsyical alazar channel
        average_buffers (bool, default True)
        average_records (bool, default True)
        integrate_samples (bool, default True)
    """

    def __init__(self, parent, pwa, name: str,
                 demod: bool=False,
                 demod_ch=None,
                 alazar_channel: str='A',
                 average_buffers: bool=True,
                 average_records: bool=True,
                 integrate_samples: bool=True):
        super().__init__(parent, name, demod=demod,
                         alazar_channel=alazar_channel,
                         average_buffers=average_buffers,
                         average_records=average_records,
                         integrate_samples=integrate_samples)
        del self.parameters['num_averages']
        self.add_parameter(name='single_shot',
                           set_cmd=False,
                           get_cmd=self._get_single_shot_status,
                           docstring='Specifies whether there is any'
                           'averaging allowed (other than in time)')
        if self.single_shot():
            self.add_parameter(name='num_reps',
                               set_cmd=self._set_num,
                               get_cmd=lambda: self._num)
        else:
            self.add_parameter(name='num_averages',
                               set_cmd=self._set_num,
                               get_cmd=lambda: self._num)
        self._demod_ch = demod_ch
        self._pwa = pwa
        self._num = 1

    def _get_single_shot_status(self):
        if not self._average_records and not self._average_buffers:
            return True
        return False

    def _set_num(self, val):
        settings = self._pwa.get_alazar_ch_settings(val, self.single_shot())
        self.update(settings)
        self._num = val

    def update(self, settings):
        """
        """

        fail = False
        if settings['average_records'] != self._average_records:
            fail = True
        elif settings['average_buffers'] != self._average_buffers:
            fail = True
        if fail:
            raise RuntimeError(
                'alazar channel cannot be updated to change averaging '
                'settings, run clear_channels before changing settings')
        self.records_per_buffer._save_val(settings['records'])
        self.buffers_per_acquisition._save_val(settings['buffers'])
        if self.dimensions == 1 and self._integrate_samples:
            self.prepare_channel(
                setpoints=settings['record_setpoints'],
                setpoint_name=settings['record_setpoint_name'],
                setpoint_label=settings['record_setpoint_label'],
                setpoint_unit=settings['record_setpoint_unit'])
        elif self.dimensions == 1:
            self.prepare_channel()
        else:
            self.prepare_channel(
                record_setpoints=settings['record_setpoints'],
                buffer_setpoints=settings['buffer_setpoints'],
                record_setpoint_name=settings['record_setpoint_name'],
                buffer_setpoint_name=settings['buffer_setpoint_name'],
            )
        self._num = settings['num']
        if self.single_shot():
            self.num_reps._save_val(settings['num'])
        else:
            self.num_averages._save_val(settings['num'])


class DemodulationChannel(InstrumentChannel):
    def __init__(self, parent, name: str, index: int, drive_frequency=None):
        """
        This is a channel which does the logic assuming a heterodyne_source
        comprising a 'carrier' microwave source and a 'localos' microwave
        source outputting signals separated by 'base_demod'. This
        heterodyne_source lives on the parametric_waveform_analyser which is
        also the parent of this channel. The channel then takes care of working
        out which frequency will actually be output ('drive') if we sideband
        the 'carrier' by a 'sideband' generated on an AWG and what is then the
        total difference between this 'drive' frequency and the 'localos'
        frequency. This is the 'demodulation' frequency which any associated
        alazar channels must be told about.

        Args:
            parent (parametric_waveform_analyser)
            name (str)
            index (int): used for labelling this channel
            drive_frequency (float, default None): if specified this sets up
                the heterodyne_source and awg sideband so that the heterodyne
                source is sidebanded to output a tone at this frequency.
        """
        super().__init__(parent, name)
        self.index = index
        self.add_parameter(
            name='sideband_frequency',
            alternative='drive_frequency, heterodyne_source.frequency',
            parameter_class=NonSettableDerivedParameter)
        self.add_parameter(
            name='demodulation_frequency',
            alternative='drive_frequency, '
            'heterodyne_source.demodulation_frequency',
            parameter_class=NonSettableDerivedParameter)
        self.add_parameter(
            name='drive_frequency',
            set_cmd=self._set_drive_freq,
            docstring='Sets sideband frequency in order to get the required '
            'drive and updates the demodulation frequencies on the relevant '
            'alazar channels')
        alazar_channels = ChannelList(
            self, "Channels", AlazarChannel,
            multichan_paramclass=AlazarMultiChannelParameter)
        self.add_submodule("alazar_channels", alazar_channels)
        if drive_frequency is not None:
            self.drive_frequency(drive_frequency)

    def _set_drive_freq(self, drive_frequency):
        sideband = self._parent._carrier_freq - drive_frequency
        demod = self._parent._base_demod_freq + sideband
        sequencer_sideband = getattr(
            self._parent.sequencer.sequence,
            'readout_sideband_{}'.format(self.index))
        sequencer_sideband(sideband)
        self.sideband_frequency._save_val(sideband)
        self.demodulation_frequency._save_val(demod)
        for ch in self.alazar_channels:
            ch.demod_freq(demod)

    def update(self, sideband=None, drive=None):
        """
        Based on the carrier and base demod of
        the parent updates the sideband and drive frequencies,
        either using existing settings or a specified
        sideband OR drive to set the other of the two.

        Args:
            sideband (float, default None)
            drive (float, default None)
        """
        base_demod = self._parent._base_demod_freq
        carrier = self._parent._carrier_freq
        old_sideband = self.sideband_frequency()
        old_demod = self.demodulation_frequency()
        if sideband is not None and drive is not None:
            raise RuntimeError('Cannot set drive and sideband simultaneously')
        elif drive is not None:
            sideband = carrier - drive
        elif sideband is not None:
            drive = carrier - sideband
        else:
            sideband = self.sideband_frequency()
            drive = carrier - sideband
        demod = base_demod + sideband
        if old_sideband != sideband:
            sequencer_sideband = getattr(
                self._parent.sequencer.sequence,
                'readout_sideband_{}'.format(self.index))
            sequencer_sideband(sideband)
            self.sideband_frequency._save_val(sideband)
        self.drive_frequency._save_val(drive)
        if demod != old_demod:
            self.demodulation_frequency._save_val(demod)
            for ch in self.alazar_channels:
                ch.demod_freq(demod)


class ParametricWaveformAnalyser(Instrument):
    """
    The PWA represents a composite instrument. It comprises a parametric
    sequencer, a high speed ADC (currently only works with the Alazar card)
    and a heterodyne source. The idea is that the parametric sequencer is used
    to sideband the heterodyne source to create various readout tones and also
    optionally to vary some parameter in a sequence. The
    setpoints of this sequence and the demodulation frequencies
    calculated from the heterodyne source demodulation frequency and the
    parametric sequencer sideband frequencies are communicated to the Alazar
    controller.

    Args:
        name
        sequencer
        alazar
        heterodyne_source
        initial_sequence_settings (optional dict): symbols and their units,
            labels and values to be passed to the parameteric_sequencer
            eg {'context': {'cycle_duration': 1, 'cycle_time': 2},
                'units': {'cycle_duration': 's', 'cycle_time': 's'},
                'labels': {'cycle_duration': '', 'cycle_time': 'Time'}}
    """
    # TODO: write code for single microwave source
    # TODO: go through and use right types of parameters

    def __init__(self,
                 name: str,
                 sequencer,
                 alazar,
                 heterodyne_source,
                 initial_sequence_settings: Dict=None) -> None:
        super().__init__(name)
        self.add_parameter('')
        self.sequencer, self.alazar = sequencer, alazar
        self.heterodyne_source = heterodyne_source
        self.alazar_controller = ATSChannelController(
            'alazar_controller', alazar.name)
        self.alazar_channels = self.alazar_controller.channels
        demod_channels = ChannelList(self, "Channels", DemodulationChannel)
        self.add_submodule("demod_channels", demod_channels)
        self._base_demod_freq = heterodyne_source.demodulation_frequency()
        self._carrier_freq = heterodyne_source.frequency()
        self.add_parameter(name='int_time',
                           set_cmd=self._set_int_time,
                           initial_value=1e-6)
        self.add_parameter(name='int_delay',
                           set_cmd=self._set_int_delay,
                           initial_value=0)
        self.add_parameter(name='seq_mode',
                           set_cmd=self._set_seq_mode,
                           get_cmd=self._get_seq_mode,
                           docstring='Sets the repeat_mode on the sequencer'
                           'and the seq_mode on the alazar and reinstates all'
                           'existing alazar channels accordingly.')
        self.add_parameter(name='carrier_frequency',
                           set_cmd=self._set_carrier_frequency,
                           initial_value=self._carrier_freq,
                           docstring='Sets the frequency on the '
                           'heterodyne_source and updates the demodulation '
                           'channels carrier_freq so that the resultant '
                           'sidebanded readout tones are updated.')
        self.add_parameter(name='base_demodulation_frequency',
                           set_cmd=self._set_base_demod_frequency,
                           initial_value=self._base_demod_freq,
                           docstring='Sets the demodulation_frequency of the'
                           ' heterodyne_source and updates the base '
                           'demodulation frequency of the demodulation '
                           'channels which propagate the information to the '
                           'alazar channels so that they have the correct  '
                           'demodulation frequencies (base_demod_freq + '
                           'sideband_freq).')
        self._sequence_settings = {'context': {}, 'units': {}, 'labels': {}}
        if initial_sequence_settings is not None:
            self._sequence_settings.update(initial_sequence_settings)
        if self.sequencer.repeat_mode() == 'sequence':
            self.seq_mode(True)
        else:
            self.seq_mode(False)

    def _set_int_time(self, int_time):
        self.alazar_controller.int_time(int_time)
        for ch in self.alazar_channels:
            if not ch._integrate_samples:
                ch.prepare_channel()

    def _set_int_delay(self, int_delay):
        self.alazar_controller.int_delay(int_delay)
        for ch in self.alazar_channels:
            if not ch._integrate_samples:
                ch.prepare_channel()

    def _set_seq_mode(self, mode):
        if str(mode).upper() in ['TRUE', '1', 'ON']:
            self.alazar.seq_mode('on')
            self.sequencer.repeat_mode('sequence')
        else:
            self.alazar.seq_mode('off')
            self.sequencer.repeat_mode('element')
        settings_list = []
        for ch in self.alazar_channels:
            settings = {'demod_channel_index': ch._demod_ch.index,
                        'demod_type': ch.demod_type()[0],
                        'integrate_time': ch._integrate_samples,
                        'single_shot': ch.single_shot(),
                        'num': ch._num}
            settings_list.append(settings)
        self.clear_alazar_channels()
        for settings in settings_list:
            self.add_alazar_channel(**settings)

    def _get_seq_mode(self):
        if (self.alazar.seq_mode() == 'on' and
                self.sequencer.repeat_mode() == 'sequence'):
            return True
        elif (self.alazar.seq_mode() == 'off' and
              self.sequencer.repeat_mode() == 'element'):
            return False
        elif ((self.alazar.seq_mode() == 'off') and
                (len(self.sequencer.get_inner_setpoints()) == 1 and
                    self.sequencer.get_outer_setpoints() is None)):
            return False
        else:
            raise RuntimeError(
                'seq modes on sequencer and alazar do not match')

    def _set_base_demod_frequency(self, demod_freq):
        self._base_demod_freq = demod_freq
        self.heterodyne_source.demodulation_frequency(demod_freq)
        for demod_ch in self.demod_channels:
            demod_ch.update()

    @contextmanager
    def sideband_update(self):
        old_drives = [demod_ch.drive_frequency()
                      for demod_ch in self.demod_channels]
        yield
        for i, demod_ch in enumerate(self.demod_channels):
            demod_ch.update(drive=old_drives[i])

    def _set_carrier_frequency(self, carrier_freq):
        self._carrier_freq = carrier_freq
        self.heterodyne_source.frequency(carrier_freq)
        for demod_ch in self.demod_channels:
            demod_ch.update()

    def add_demodulation_channel(self, drive_frequency):
        demod_ch_num = len(self.demod_channels)
        demod_ch = DemodulationChannel(
            self, 'ch_{}'.format(demod_ch_num), demod_ch_num,
            drive_frequency=drive_frequency)
        self.demod_channels.append(demod_ch)

    def clear_demodulation_channels(self):
        for ch in list(self.demod_channels):
            self.demod_channels.remove(ch)
        for ch in list(self.alazar_channels):
            self.alazar_channels.remove(ch)

    def add_alazar_channel(
            self, demod_ch_index: int, demod_type: str,
            single_shot: bool=False, num: int=1, integrate_time: bool=True):
        """
        Creates an alazar channel attached to the specified demodulation
        channel and with setting which match the demodulation channel and
        the current sequence uploaded.

        Args:
            demod_ch_index (int): the demodulation channel index for the alazar
                channel to be associated with
            demod_type ('m', 'p', 'i' or 'r'): magnitude, phase, real or
                imaginary, choose one!
            single_shot (bool, default False): whether ot not averaging is
                used, if True then num_averages can be set, if False then
                num_reps can be set
            num (int, default 1): specifies num_averages or num_reps depending
                on single_shot status
            integrate_time (bool, default True): determines whether to average
                samples
        """
        settings = self.get_alazar_ch_settings(num, single_shot)
        demod_ch = self.demod_channels[demod_ch_index]
        name = 'ch_{}_{}'.format(demod_ch_index, demod_type)
        averaging_settings = {
            'integrate_time': integrate_time,
            **{k: settings[k] for k in ('average_records', 'average_buffers')}}
        appending_string = '_'.join(
            [k.split('_')[1] for k, v in averaging_settings.items() if not v])
        if appending_string:
            name += '_' + appending_string
        chan = AlazarChannel_ext(self.alazar_controller,
                                 self,
                                 name=name,
                                 demod=True,
                                 demod_ch=demod_ch,
                                 average_records=settings['average_records'],
                                 average_buffers=settings['average_buffers'],
                                 integrate_samples=integrate_time)
        chan.demod_freq(demod_ch.demodulation_frequency())
        if demod_type in 'm':
            chan.demod_type('magnitude')
            chan.data.label = 'Cavity Magnitude Response'
        elif demod_type == 'p':
            chan.demod_type('phase')
            chan.data.label = 'Cavity Phase Response'
        elif demod_type == 'i':
            chan.demod_type('imag')
            chan.data.label = 'Cavity Imaginary Response'
        elif demod_type == 'r':
            chan.demod_type('real')
            chan.data.label = 'Cavity Real Response'
        else:
            raise NotImplementedError(
                'only magnitude, phase, imaginary and real currently '
                'implemented')
        self.alazar_controller.channels.append(chan)
        chan.update(settings)
        demod_ch.alazar_channels.append(chan)

    def set_sequencer_template(
            self,
            template_element: Element,
            inner_setpoints: Tuple[Symbol, Sequence],
            outer_setpoints: Tuple[Symbol, Sequence]=None,
            context: ContextDict=None,
            units: Dict[Symbol, str]=None,
            labels: Dict[Symbol, str]=None,
            first_sequence_element: Element=None,
            initial_element: Element=None):
        """
        Sets up the sequencing on the parametric sequencer and the
        setpoints on alazar channels. The context updates the existing
        one but does not overwrite it.

        Args:
            template_element (Element)
            inner_setpoints (tuple): symbol and the sequence of values it takes
            outer_setpoints (tuple): symbol and the sequence of values it takes
            context (dict, default None): used to update sequence_settings
            units (dict, default None): used to update sequence_settings
            labels (dict, default None): used to update sequence_settings
            first_sequence_element (Element, default None)
            initial_element (Element, default None)
        """
        self.update_sequence_settings(context, units, labels)
        self.sequencer.set_template(
            template_element,
            inner_setpoints=inner_setpoints,
            outer_setpoints=outer_setpoints,
            context=self._sequence_settings['context'],
            units=self._sequence_settings['units'],
            labels=self._sequence_settings['labels'],
            first_sequence_element=first_sequence_element,
            initial_element=initial_element)
        for ch in list(self.alazar_channels):
            settings = self.get_alazar_ch_settings(
                ch._num, single_shot=ch.single_shot())
            ch.update(settings)

    def update_sequence_settings(self, context: Dict=None,
                                 units: Dict=None, labels: Dict=None):
        """
        Updates the sequence settings which are used when the sequencer
        template is updated

        Args:
            context (dict, default None): dict used to updated the existing
                context dictionary which is then used to create the sequence
            units (dict, default None): updates units so that parametric
                sequencer parameters and alazar setpoints are meaningful
            labels (dict, default None): updates labels so that parametric
                sequencer parameters and alazar setpoints plot well
        """
        self._sequence_settings['context'].update(context or {})
        self._sequence_settings['units'].update(units or {})
        self._sequence_settings['labels'].update(labels or {})

    def clear_sequence_settings(self):
        """
        Clears the sequence settings which are used when the sequencer
        template is updated.
        """
        self._sequence_settings = {'context': {}, 'units': {}, 'labels': {}}

    def clear_alazar_channels(self):
        """
        Clears all alazar channels and removes references from the demodulation
        channels
        """
        for demod_ch in list(self.demod_channels):
            for alazar_ch in demod_ch.alazar_channels:
                demod_ch.alazar_channels.remove(alazar_ch)
                self.alazar_channels.remove(alazar_ch)
                del alazar_ch

    def make_all_alazar_channels_play_nice(self):
        raise NotImplementedError

    def get_alazar_ch_settings(self, num: int, single_shot: bool):
        """
        Based on the current instrument settings calculates the settings
        configuration for an alazar channel.

        Args:
            num (int): sets num_reps if single_shot, num_averages otherwise
            single_shot (bool): whether averaging is allowed

        Returns:
            settings (dict): dictionary which specified averaging settings
                for records and buffers dimensions and accompanying setpoints,
                setpoint names, labels and units
        """
        seq_mode = self.seq_mode()
        settings = {'num': num}
        if not single_shot:
            settings['average_buffers'] = True
            settings['buffer_setpoints'] = None
            settings['buffer_setpoint_name'] = None
            settings['buffer_setpoint_label'] = None
            settings['buffer_setpoint_unit'] = None
            if (seq_mode and
                    len(self.sequencer.get_inner_setpoints().values) > 1):
                if self.sequencer.get_outer_setpoints() is not None:
                    logger.warn('Averaging channel will average over '
                                'outer setpoints of AWG sequence')
                record_symbol = self.sequencer.get_inner_setpoints().symbol
                record_setpoints = self.sequencer.get_inner_setpoints().values
                record_param = getattr(self.sequencer.repeat, record_symbol)
                settings['records'] = len(record_setpoints)
                settings['buffers'] = num
                settings['average_records'] = False
                settings['record_setpoints'] = record_setpoints
                settings['record_setpoint_name'] = record_symbol
                settings['record_setpoint_label'] = record_param.label
                settings['record_setpoint_unit'] = record_param.unit

            else:
                settings['average_records'] = True
                max_samples = self.alazar_controller.board_info['max_samples']
                samples_per_rec = self.alazar_controller.samples_per_record()
                tot_samples = num * samples_per_rec
                if tot_samples > max_samples:
                    settings['records'] = math.floor(
                        max_samples / samples_per_rec)
                    settings['buffers'] = math.ceil(max_samples / records)
                else:
                    settings['records'] = num
                    settings['buffers'] = 1
                settings['record_setpoints'] = None
                settings['record_setpoint_name'] = None
                settings['record_setpoint_label'] = None
                settings['record_setpoint_unit'] = None
        else:
            settings['average_buffers'] = False
            settings['average_records'] = False
            if (seq_mode and
                    len(self.sequencer.get_inner_setpoints().values) > 1):
                if (self.sequencer.get_outer_setpoints() is not None and
                        num > 1):
                    raise RuntimeError(
                        'Cannot have outer setpoints and multiple nreps')
                record_symbol = self.sequencer.get_inner_setpoints().symbol
                record_setpoints = self.sequencer.get_inner_setpoints().values
                records_param = getattr(self.sequencer.repeat, record_symbol)
                settings['records'] = len(record_setpoints)
                settings['record_setpoints'] = record_setpoints
                settings['record_setpoint_name'] = record_symbol
                settings['record_setpoint_label'] = records_param.label
                settings['record_setpoint_unit'] = records_param.unit
                if self.sequencer.get_outer_setpoints() is not None:
                    buffers_symbol = self.sequencer.get_outer_setpoints().symbol
                    buffers_setpoints = self.sequencer.get_outer_setpoints().values
                    buffers_param = getattr(
                        self.sequencer.repeat, buffers_symbol)
                    settings['buffer_setpoints'] = buffers_setpoints
                    settings['buffer_setpoint_name'] = buffers_symbol
                    settings['buffer_setpoint_label'] = buffers_param.label
                    settings['buffer_setpoint_unit'] = buffers_param.unit
                    settings['buffers'] = len(buffer_setpoints)
                else:
                    settings['buffers'] = num
                    settings['buffer_setpoints'] = np.arange(num)
                    settings['buffer_setpoint_name'] = 'repetitions'
                    settings['buffer_setpoint_label'] = 'Repetitions'
                    settings['buffer_setpoint_unit'] = None
            else:
                max_samples = self.alazar_controller.board_info['max_samples']
                samples_per_rec = self.alazar_controller.samples_per_record()
                tot_samples = num * samples_per_rec
                if tot_samples > max_samples:
                    records = math.floor(max_samples / samples_per_rec)
                    buffers = math.ceil(max_samples / records)
                else:
                    records = num
                    buffers = 1
                settings['records'] = records
                settings['buffers'] = buffers
                settings['record_setpoints'] = np.arange(records)
                settings['record_setpoint_name'] = 'record_repetitions'
                settings['record_setpoint_label'] = 'Record Repetitions'
                settings['record_setpoint_unit'] = None
                settings['buffer_setpoints'] = np.arange(buffers)
                settings['buffer_setpoint_name'] = 'buffer_repetitions'
                settings['buffer_setpoint_label'] = 'Buffer Repetitions'
                settings['buffer_setpoint_unit'] = None
        return settings
