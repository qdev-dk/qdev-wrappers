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
    An extension to the Alazar channel which has added
    convenience function for updating records, buffers
    and setpoints from dictionary
    """

    def __init__(self, parent, name: str,
                 demod: bool=False,
                 alazar_channel: str='A',
                 average_buffers: bool=True,
                 average_records: bool=True,
                 integrate_samples: bool=True):
        super().__init__(parent, name, demod=demod,
                         alazar_channel=alazar_channel,
                         average_buffers=average_buffers,
                         average_records=average_records,
                         integrate_samples=integrate_samples)

    def update(self, settings: Dict):
        """
        Updates the setpoints, setpoint names and setpoint labels and
        the num_averages/num_reps of the channel.

        NB Fails if the new settings require a change in averaging
            settings such as changing the state of 'average_records'
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
        elif dimensions == 2:
            self.prepare_channel(
                record_setpoints=settings['record_setpoints'],
                buffer_setpoints=settings['buffer_setpoints'],
                record_setpoint_name=settings['record_setpoint_name'],
                buffer_setpoint_name=settings['buffer_setpoint_name'],
            )
        else:
            self.prepare_channel()
        self._stale_setpoints = False


class SidebandingChannel(InstrumentChannel):
    def __init__(self, parent, name: str, ch_num: int,
                 drive_frequency=None):
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
            ch_num (int): used for labelling this channel
            drive_frequency (float, default None): if specified this sets up
                the heterodyne_source and awg sideband so that the heterodyne
                source is sidebanded to output a tone at this frequency.
        """
        super().__init__(parent, name)
        self.ch_num = ch_num
        self.add_parameter(
            name='sideband_frequency',
            alternative='drive_frequency',
            parameter_class=NonSettableDerivedParameter)
        self.add_parameter(
            name='drive_frequency',
            set_cmd=self._set_drive_freq,
            docstring='Sets sideband frequency in order to get the required '
            'drive and updates the demodulation frequencies on the relevant '
            'alazar channels')

        # pulse building parameters
        self.add_parameter(name='pulse_amplitude',
                           label='Pulse Amplitude',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='I_offset',
                           label='I Offset',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='Q_offset',
                           label='Q Offset',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='gain_offset',
                           label='Gain Offset',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='phase_offset',
                           label='Phase Offset',
                           unit='degrees',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='DRAG_amplitude',
                           label='DRAG amplitude',
                           parameter_class=PulseBuildingParameter)
        if isinstance(parent, ReadoutChannel):
            self._type = 'readout'
            self.add_parameter(
                name='demodulation_frequency',
                alternative='drive_frequency, '
                'heterodyne_source.demodulation_frequency',
                parameter_class=NonSettableDerivedParameter)
            alazar_chan_list = ChannelList(
                self,
                'alazar_channels',
                AlazarChannel_ext,
                multichan_paramclass=AlazarMultiChannelParameter)
            self.add_submodule('alazar_channels', alazar_chan_list)
        elif isinstance(parent, DriveChannel):
            self._type = 'drive'
        else:
            raise RuntimeError('parent of SidebandingChannel must be'
                               'DriveChannel or ReadoutChannel')
        if drive_frequency is not None:
            self.drive_frequency(drive_frequency)

    def _set_drive_freq(self, drive_frequency):
        sideband = self._parent.carrier_frequency() - drive_frequency
        self.sideband_frequency._save_val(sideband)
        self._parent._sequence_up_to_date = False

        if self._type == 'readout':
            demod = self._parent.base_demodulation_frequency() + sideband
            self.demodulation_frequency._save_val(demod)

            for ch in self.alazar_channels:
                ch.demod_freq(demod)

    def update(self, sideband=None, drive=None):
        """
        Based on the carrier and optionally base demod of
        the parent updates the sideband and drive frequencies,
        either using existing settings or a specified
        sideband OR drive to set the other of the two.

        Args:
            sideband (float, default None)
            drive (float, default None)
        """
        carrier = self._parent.carrier_frequency()
        old_sideband = self.sideband_frequency()
        old_demod = self.demodulation_frequency()

        if sideband is not None and drive is not None:
            raise RuntimeError('Cannot set drive and sideband simultaneously')
        elif drive is not None:
            sideband = carrier - drive
        elif sideband is not None:
            drive = carrier - sideband
        else:
            sideband = old_sideband
            drive = carrier - sideband

        if self._type == 'readout':
            base_demod = self._parent.base_demodulation_frequency()
            demod = base_demod + sideband
            if old_sideband != sideband:
                self._parent._sequence_up_to_date = False
                self.sideband_frequency._save_val(sideband)
            self.drive_frequency._save_val(drive)
            if demod != old_demod:
                self.demodulation_frequency._save_val(demod)
                for ch in self.alazar_channels:
                    ch.demod_freq(demod)


class ReadoutChannel(InstrumentChannel):
    def __init__(self, parent, name):
        super().__init__(parent, name)
        self.add_parameter(name='meas_duration',
                           set_cmd=parent._set_meas_dur,
                           label='Measurement Duration',
                           unit='s',
                           initial_value=1e-6)
        self.add_parameter(name='meas_delay',
                           label='Measurement Delay',
                           unit='s',
                           set_cmd=parent._set_meas_delay,
                           initial_value=0)
        self.add_parameter(name='carrier_frequency',
                           set_cmd=self._set_carrier_frequency,
                           initial_value=parent.heterodyne_source.frequency(),
                           label='Readout Carrier Frequency',
                           unit='Hz',
                           docstring='Sets the frequency on the '
                           'heterodyne_source and updates the demodulation '
                           'channels carrier_freq so that the resultant '
                           'sidebanded readout tones are updated.')
        self.add_parameter(name='power',
                           label='Readout Power',
                           unit='dBm',
                           parameter_class=DelegateParameter,
                           source=parent.heterodyne_source.power)
        self.add_parameter(name='base_demodulation_frequency',
                           set_cmd=self._set_base_demod_frequency,
                           label='Base Demodulation Frequency',
                           unit='Hz',
                           initial_value=parent.heterodyne_source.demodulation_frequency())
        self.add_parameter(name='demodulation_type',
                           set_cmd=self._set_demod_type,
                           initial_value='magphase',
                           vals=vals.Enum('magphase', 'IQ'))
        self.add_parameter(name='single_shot',
                           set_cmd=self._set_single_shot,
                           initial_value=True,
                           vals=vals.Bool())
        self.add_parameter(name='num',
                           set_cmd=self._set_num,
                           initial_value=1,
                           vals=vals.Ints())
        self.add_parameter(name='integrate_time',
                           set_cmd=self._set_integrate_time,
                           initial_value=True,
                           vals=vals.Bool())
        # pulse building parameters
        self.add_parameter(name='total_duration',
                           label='Cycle Time',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='marker_readout_delay',
                           label='Marker Readout Delay',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='readout_pulse_duration',
                           label='Readout Pulse Duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='marker_duration',
                           label='Marker Duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.all_readout_channels = parent.alazar_controller.channels
        self._sidebanding_channels = []
        self._pulse_building_parameters = {
            n: p for n, p in self.parameters.items() if
            isinstance(p, PulseBuildingParameter)}

    def _set_carrier_frequency(self, carrier_freq):
        self._parent.heterodyne_source.frequency(carrier_freq)
        for demod_ch in self._demod_channels:
            demod_ch.update()

    def _set_base_demod_frequency(self, demod_freq):
        self.heterodyne_source.demodulation_frequency(demod_freq)
        for demod_ch in self._demod_channels:
            demod_ch.update()

    def _set_meas_dur(self, meas_dur):
        self.parent.alazar_controller.int_time(meas_dur)
        for ch in self.all_readout_channels:
            if not ch._integrate_samples:
                ch.prepare_channel()

    def _set_meas_delay(self, meas_delay):
        self.parent.alazar_controller.int_delay(meas_delay)
        for ch in self.all_readout_channels:
            if not ch._integrate_samples:
                ch.prepare_channel()

    def _set_demod_type(self, demod_type):
        for demod_ch in self._sidebanding_channels:
            if demod_type == 'magphase':
                demod_ch.alazar_channels[0].demod_type('magnitude')
                demod_ch.alazar_channels[0].data.label = f'Q{demod_ch_num} Magnitude'
                demod_ch.alazar_channels[1].demod_type('phase')
                demod_ch.alazar_channels[1].data.label = f'Q{demod_ch_num} Phase'
            else:
                demod_ch.alazar_channels[0].demod_type('real')
                demod_ch.alazar_channels[0].data.label = f'Q{demod_ch_num} Real'
                demod_ch.alazar_channels[1].demod_type('imaginary')
                demod_ch.alazar_channels[1].data.label = f'Q{demod_ch_num} Imaginary'

    def _set_num(self, num):
        self._save_val(num)
        self.update_all_alazar_channels()

    def _set_integrate_time(self, num):
        self._parent.alazar_controller.channels.clear()
        settings = get_alazar_ch_settings(self._parent)
        for demod_ch in self._sidebanding_channels:
            demod_ch.alazar_channels.clear()
            self._add_alazar_channels(settings, demod_ch)

    def add_sidebanding_channel(self, frequency):
        demod_ch_num = len(self._sidebanding_channels)
        demod_ch = SidebandingChannel(
            self, 'Q{demod_ch_num}'.format(demod_ch_num), demod_ch_num,
            drive_frequency=frequency)
        settings = get_alazar_ch_settings(self._parent)
        self._add_alazar_channels(settings, demod_ch)
        self._sidebanding_channels.append(demod_ch)
        self.add_submodule(f'Q{demod_ch_num}', demod_ch)

    @contextmanager
    def sideband_update(self):
        old_drives = [demod_ch.drive_frequency()
                      for demod_ch in self._sidebanding_channels]
        yield
        for i, demod_ch in enumerate(self.demod_chan_sidebanding_channelsnels):
                demod_ch.update(drive=old_drives[i])
        self._parent.update_sequence()

    def _add_alazar_channels(self, settings, demod_ch):
        alazar_channels = self._create_alazar_channel_pair(
            settings, demod_ch.ch_num)
        for ch in alazar_channels:
            ch.demod_freq(demod_ch.demodulation_frequency())
            self._parent.alazar_controller.channels.append(ch)
            demod_ch.alazar_channels.append(ch)

    def _create_alazar_channel_pair(self, settings, demod_ch_num):
        chan1 = AlazarChannel_ext(self._parent.alazar_controller,
                                  name=f'Q{demod_ch_num}_realmag',
                                  demod=True,
                                  average_records=settings['average_records'],
                                  average_buffers=settings['average_buffers'],
                                  integrate_samples=integrate_time)
        chan2 = AlazarChannel_ext(self._parent.alazar_controller,
                                  name=f'Q{demod_ch_num}_imaginaryphase',
                                  demod=True,
                                  average_records=settings['average_records'],
                                  average_buffers=settings['average_buffers'],
                                  integrate_samples=integrate_time)
        if self.demodulation_type() == 'magphase':
            chan1.demod_type('magnitude')
            chan1.data.label = f'Q{demod_ch_num} Magnitude'
            chan2.demod_type('phase')
            chan1.data.label = f'Q{demod_ch_num} Phase'
        else:
            chan1.demod_type('real')
            chan1.data.label = f'Q{demod_ch_num} Real'
            chan2.demod_type('imaginary')
            chan1.data.label = f'Q{demod_ch_num} Imaginary'
        return chan1, chan2

    def update_all_alazar_channels(self):
        settings = get_alazar_ch_settings(self._parent)
        for ch in self._parent.alazar_controller.channels:
            ch.update(settings)

    def clear_channels(self):
        self._parent.alazar_controller.alazar_channels.clear()
        self._sidebanding_channels.clear()  # TODO should I also delete?
        self.submodules.clear()


class DriveChannel(InstrumentChannel):
    def __init__(self, parent, name):
        super().__init(parent, name)
        self.add_parameter(name='power',
                           label='Drive Power',
                           unit='dBm',
                           parameter_class=DelegateParameter,
                           source=parent.qubit_source.power)
        self.add_parameter(name='carrier_frequency',
                           set_cmd=parent._set_carrier_frequency,
                           initial_value=parent.qubit_source.frequency,
                           label='Drive Carrier Frequency',
                           unit='Hz')
        self.add_parameter(name='drive_stage_duration',
                           label='Drive Stage Duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='sigma_cutoff',
                           label='Sigma Cutoff',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='drive_readout_delay',
                           label='Drive Readout Delay',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='modulation_marker_duration',
                           label='Drive Modulation Duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='pulse_separation',
                           label='Pulse Separation',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='drive_readout_delay',
                           label='Drive Readout Delay',
                           unit='s',
                           parameter_class=PulseBuildingParameter)

        self.add_parameter(name='readout_duration',
                           label='Readout Pulse Duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='sigma_cutoff',
                           label='Sigma Cutoff',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='drive_readout_delay',
                           label='Drive Readout Delay',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='modulation_marker_duration',
                           label='Drive Modulation Duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='pulse_separation',
                           label='Pulse Separation',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='marker_readout_delay',
                           label='Marker Readout Delay',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='readout_pulse_duration',
                           label='Readout Pulse Duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='marker_duration',
                           label='Marker Duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='readout_pulse_duration',
                           label='Pulse Separation',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self._sidebanding_channels = []
        self._pulse_building_parameters = {
            n: p for n, p in self.parameters.items() if
            isinstance(p, PulseBuildingParameter)}

    def add_sidebanding_channel(self, frequency):
        demod_ch_num = len(self._demod_channels)
        demod_ch = SidebandingChannel(
            self, 'Q{}'.format(demod_ch_num), demod_ch_num,
            drive_frequency=frequency)

    @contextmanager
    def sideband_update(self):
        old_drives = [demod_ch.drive_frequency()
                      for demod_ch in self._sidebanding_channels]
        yield
        for i, demod_ch in enumerate(self.demod_chan_sidebanding_channelsnels):
                demod_ch.update(drive=old_drives[i])
        self._parent.update_sequence()

    def clear_channels(self):
        self._sidebanding_channels.clear()  # TODO should I also delete?
        self.submodules.clear()


class PulseBuildingParameter(Parameter):
    def __init__(self, name, instrument,
                 label=None, unit=None, get_cmd=None,
                 vals=None):
        super().__init__(
            name, instrument=instrument, label=label, unit=unit,
            get_cmd=get_cmd, set_cmd=self._set_and_stale_setpoints, vals=vals)

    def _set_and_stale_setpoints(self, val):
        self._save_val()
        self.instrument._parent._set_stale_setpoints()


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
        qubit_source
    """
    # TODO: write code for single microwave source
    # TODO: go through and use right types of parameters

    def __init__(self,
                 name: str,
                 sequencer,
                 alazar,
                 heterodyne_source,
                 qubit_source) -> None:
        super().__init__(name)
        self.add_parameter('')
        self.sequencer = sequencer
        self.alazar = alazar
        self.heterodyne_source = heterodyne_source
        self.qubit_source = qubit_source
        self.alazar_controller = ATSChannelController(
            'alazar_controller', alazar.name)
        self._inner_setpoints = None
        self._outer_setpoints = None
        self._template_element = None
        self._first_element = None
        readout_channel = ReadoutChannel(self, 'readout')
        self.add_submodule('readout', readout_channel)
        drive_channel = ReadoutChannel(self, 'drive')
        self.add_submodule('drive', drive_channel)

        self.add_parameter(name='seq_mode',
                           set_cmd=self._set_seq_mode,
                           get_cmd=self._get_seq_mode,
                           docstring='Sets the repeat_mode on the sequencer'
                           'and the seq_mode on the alazar and reinstates all'
                           'existing alazar channels accordingly.')

        if self.sequencer.repeat_mode() == 'sequence':
            self.seq_mode(True)
        else:
            self.seq_mode(False)
        self._pulse_building_parameters = {
            **self.readout._pulse_building_parameters,
            **self.drive._pulse_building_parameters}

    def _get_seq_mode(self):
        if (self.alazar.seq_mode() and
                self.sequencer.repeat_mode() == 'sequence'):
            return True
        elif (not self.alazar.seq_mode() and
              self.sequencer.repeat_mode() == 'element'):
            return False
        elif (not self.alazar.seq_mode() and
                (len(self.sequencer.get_inner_setpoints()) == 1 and
                    self.sequencer.get_outer_setpoints() is None)):
            return False
        else:
            raise RuntimeError(
                'seq modes on sequencer and alazar do not match')

    def _set_seq_mode(self, mode):
        if str(mode).upper() in ['TRUE', '1', 'ON']:
            self.alazar.seq_mode(True)
            self.sequencer.repeat_mode('sequence')
        else:
            self.alazar.seq_mode(False)
            self.sequencer.repeat_mode('element')
        settings_list = []
        for ch in self.readout.all_readout_channels:
            settings = {'demod_ch_index': ch._demod_ch.index,
                        'demod_type': ch.demod_type()[0],
                        'integrate_time': ch._integrate_samples,
                        'single_shot': ch.single_shot(),
                        'num': ch._num}
            settings_list.append(settings)
        self.clear_channels()
        for settings in settings_list:
            self.add_alazar_channel(**settings)

    def _set_stale_setpoints(self):
        for ch in self.alazar_controller.alazar_channels:
            ch._stale_setpoints = True

    @contextmanager
    def sequence_updating(self):
        yield
        self.update_sequence()

    def set_setpoints(self, inner_setpoints, outer_setpoints=None):
        if inner_setpoints is None:
            self._set_stale_setpoints()
            return
        self.sequencer.set_setpoints(inner_setpoints, outer_setpoints)
        self._inner_setpoints = inner_setpoints
        self._outer_setpoints = outer_setpoints

    def set_template_element(self, template_element, first_element=None):
        if template_element is None:
            self._set_stale_setpoints()
            return
        context, labels, units = self._generate_context()
        self.sequencer.set_template(
            template_element,
            context=context,
            labels=labels,
            unit=units,
            first_sequence_element=first_element)
        self.readout.update_all_alazar_channels()
        self._template_element = None
        self._first_element = None

    def _generate_context(self):
        context = {}
        labels = {}
        units = {}
        for name, param in self._pulse_building_parameters.items():
            context[name] = param()
            labels[name] = param.label
            units[name] = param.unit
        return context, labels, units

    def update_sequence(self):
        self.set_template_element(self._template_element, self._first_element)
        self.set_setpoints(self._inner_setpoints, self._outer_setpoints)


def get_alazar_ch_settings(pwa):
    """
    Based on the current instrument settings calculates the settings
    configuration for an alazar channel.

    Args:
        pwa

    Returns:
        settings (dict): dictionary which specified averaging settings
            for records and buffers dimensions and accompanying setpoints,
            setpoint names, labels and units
    """
    seq_mode = pwa.seq_mode()
    num = pwa.readout.num()
    single_shot = pwa.readout.single_shot()
    settings = {'num': num}
    if not single_shot:
        settings['average_buffers'] = True
        settings['buffer_setpoints'] = None
        settings['buffer_setpoint_name'] = None
        settings['buffer_setpoint_label'] = None
        settings['buffer_setpoint_unit'] = None
        if (seq_mode and
                len(sequencer.get_inner_setpoints().values) > 1):
            if sequencer.get_outer_setpoints() is not None:
                logger.warn('Averaging channel will average over '
                            'outer setpoints of AWG sequence')
            record_symbol = sequencer.get_inner_setpoints().symbol
            record_setpoints = sequencer.get_inner_setpoints().values
            record_param = getattr(sequencer.repeat, record_symbol)
            settings['records'] = len(record_setpoints)
            settings['buffers'] = num
            settings['average_records'] = False
            settings['record_setpoints'] = record_setpoints
            settings['record_setpoint_name'] = record_symbol
            settings['record_setpoint_label'] = record_param.label
            settings['record_setpoint_unit'] = record_param.unit

        else:
            settings['average_records'] = True
            max_samples = pwa.alazar_controller.board_info['max_samples']
            samples_per_rec = pwa.alazar_controller.samples_per_record()
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
                len(pwa.sequencer.get_inner_setpoints().values) > 1):
            if (pwa.sequencer.get_outer_setpoints() is not None and
                    num > 1):
                raise RuntimeError(
                    'Cannot have outer setpoints and multiple nreps')
            record_symbol = pwa.sequencer.get_inner_setpoints().symbol
            record_setpoints = pwa.sequencer.get_inner_setpoints().values
            records_param = getattr(pwa.sequencer.repeat, record_symbol)
            settings['records'] = len(record_setpoints)
            settings['record_setpoints'] = record_setpoints
            settings['record_setpoint_name'] = record_symbol
            settings['record_setpoint_label'] = records_param.label
            settings['record_setpoint_unit'] = records_param.unit
            if pwa.sequencer.get_outer_setpoints() is not None:
                buffers_symbol = pwa.sequencer.get_outer_setpoints().symbol
                buffers_setpoints = pwa.sequencer.get_outer_setpoints().values
                buffers_param = getattr(
                    pwa.sequencer.repeat, buffers_symbol)
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
            max_samples = pwa.alazar_controller.board_info['max_samples']
            samples_per_rec = pwa.alazar_controller.samples_per_record()
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
