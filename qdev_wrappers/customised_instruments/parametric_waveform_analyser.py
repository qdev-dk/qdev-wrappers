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

# TODO: docstrings
logger = logging.getLogger(__name__)


class PulseBuildingParameter(Parameter):
    """
    A Parameter representing a parameter of a pulse sequence running
    on a ParametricSequencer.
    It has a pulse_building_name attribute for use in sequence building
    and updates the sequence on setting.
    """

    def __init__(self, name, instrument, pulse_building_name=None,
                 label=None, unit=None, set_cmd=None,
                 vals=None):
        if set_cmd is None:
            set_cmd = self._set_and_update_sequence
        super().__init__(
            name, instrument=instrument, label=label, unit=unit,
            get_cmd=None, set_cmd=set_cmd,
            vals=vals)
        pulse_building_name = pulse_building_name or name
        self.pulse_building_name = pulse_building_name

    def _set_and_update_sequence(self, val):
        self._save_val()
        if isinstance(self.instrument, SidebandingChannel):
            pwa_instr = self.instrument._parent._parent
        elif isinstance(self.instrument, (ReadoutChannel, DriveChannel)):
            pwa_instr = instrument._parent
        else:
            logger.warning(f'could not establish how to update sequence '
                           'while setting {self.name} PulseBuildingParameter')
        if not pwa_instr.suppress_sequence_upload:
            pwa._update_sequence()


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
        else:
            self.prepare_channel(**settings)


class SidebandingChannel(InstrumentChannel):
    """
    An InstrumentChannel intended to belong to a ReadoutChannel or a
    DriveChannel of a ParametricWaveformAnalyser. One sidebanding channel
    is used to control and keep track of the drive or readout signals
    at one frequency (eg for one qubit) and also contains the
    pulse building parameters which relate to the aspects of the
    pulse sequence which create the sideband signal.

    A carrier microwave source is assumed, the signal of which is mixed
    with a signal at the 'sideband_frequency' to produce a signal at the
    'drive_frequency'.

    If readout is intended at then it is assumed that this is done by mixing
    the signal back down with the signal from a localos microwave souce
    (which together with the carrier microwave source comprises a
    heterodyne_source) to produce a signal at
    'demodulation_frequency' which can be measured using an Alazar card.
    In this case both a 'demodulation_frequency' parameter and an
    'alazar_channels' ChannelList of the associated alazar
    channels are effective attributes.
    """

    def __init__(self, parent, name: str, ch_num: int,
                 drive_frequency=frequency):
        super().__init__(parent, name)
        self.ch_num = ch_num

        # pulse building parameters
        pre_str = f'Q{ch_num}_{self.type}_'
        self.add_parameter(name='sideband_frequency',
                           pulse_building_name=pre_str + 'sideband_frequency',
                           set_cmd=False,
                           parameter_class=PulseBuildingParameter,
                           docstring='set via drive_frequency or'
                           'readout.carrier_frequency')
        self.add_parameter(name='pulse_amplitude',
                           pulse_building_name=pre_str + 'pulse_amplitude',
                           label='Pulse Amplitude',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='I_offset',
                           pulse_building_name=pre_str + 'I_offset',
                           label='I Offset',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='Q_offset',
                           pulse_building_name=pre_str + 'Q_offset',
                           label='Q Offset',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='gain_offset',
                           pulse_building_name=pre_str + 'gain_offset',
                           label='Gain Offset',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='phase_offset',
                           pulse_building_name=pre_str + 'phase_offset',
                           label='Phase Offset',
                           unit='degrees',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='DRAG_amplitude',
                           pulse_building_name=pre_str + 'DRAG_amplitude',
                           label='DRAG amplitude',
                           parameter_class=PulseBuildingParameter)

        self.add_parameter(name='drive_frequency',
                           set_cmd=self._set_drive_freq,
                           docstring='Sets sideband frequency '
                           'in order to get the required '
                           'drive and updates the demodulation '
                           'frequencies on the relevant '
                           'alazar channels if relevant')

        if isinstance(parent, ReadoutChannel):
            self._type = 'readout'
            self.add_parameter(name='demodulation_frequency',
                               alternative='drive_frequency',
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

        self._pulse_building_parameters = {
            p.pulse_building_name: p for n, p in self.parameters.items() if
            isinstance(p, PulseBuildingParameter)}

        if drive_frequency is not None:
            self.drive_frequency(drive_frequency)

    def _set_drive_freq(self, drive_frequency):
        sideband = self._parent.carrier_frequency() - drive_frequency
        self.sideband_frequency._set_and_update_sequence(sideband)
        self._parent._sequence_up_to_date = False

        if self._type == 'readout':
            demod = self._parent.base_demodulation_frequency() + sideband
            self.demodulation_frequency._save_val(demod)
            for ch in self.alazar_channels:
                ch.demod_freq(demod)

    def _clear_alazar_channels(self):
        if self._type == 'readout':
            self.alazar_channels.clear()
        else:
            raise RuntimeError('SidebandingChannel has type drive so no '
                               'associated alazar channels to clear')

    def update(self, drive_frequency=None):
        """
        Based on the carrier frequency the sideband and drive
        frequencies are updated (and the demodulation_frequency where
        relevant). If a drive is specified then this is used to choose
        the sideband_frequency and the sequence is updated, otherwise
        the existing sideband value is used and the drive_frequency
        is updated.
        """
        carrier = self._parent.carrier_frequency()
        old_sideband = self.sideband_frequency()
        drive = drive_frequency

        if drive is not None:
            sideband = carrier - drive
        else:
            sideband = old_sideband
            drive = carrier - sideband

        self.sideband_frequency._set_and_update_sequence(sideband)
        self.drive_frequency._save_val(drive)

        if self._type == 'readout':
            old_demod = self.demodulation_frequency()
            base_demod = self._parent.base_demodulation_frequency()
            demod = base_demod + sideband
            if demod != old_demod:
                self.demodulation_frequency._save_val(demod)
                for ch in self.alazar_channels:
                    ch.demod_freq(demod)


class ReadoutChannel(InstrumentChannel):
    """
    An InstrumentChannel intended to belong to a ParametricWaveformAnalyser
    and which effectively groups the parameters related to readout including
    heterodyne_source parameters, alazar_controller parameters and
    pulse building parameters.

    Sidebanding channels can be added for each readout frequency, the alazar
    channels of these can be accessed by the 'all_readout_channels' attribute.
    """

    def __init__(self, parent, name):
        super().__init__(parent, name)

        # heterodyne source parameters
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

        # alazar controller parameters
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

        # alazar channel parameters
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
                           vals=vals.Ints(),
                           docstring='number of repetitions if single_shot, '
                           'number of averages otherwise')
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

    @property
    def _pulse_building_parameters(self):
        pulse_building_parameters = {}
        for n, p in self.parameters.items():
            if isinstance(p, PulseBuildingParameter):
                pulse_building_parameters[p.pulse_building_name] = p
        for demod_ch in self._sidebanding_channels:
            pulse_building_parameters.update(
                demod_ch._pulse_building_parameters)
        return pulse_building_parameters

    def _set_carrier_frequency(self, carrier_freq):
        self._parent.heterodyne_source.frequency(carrier_freq)
        for demod_ch in self._sidebanding_channels:
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

    def _set_single_shot(self, val):
        self.single_shot._save_val(val)
        self._reinstate_alazar_channels()

    def _set_num(self, num):
        self._save_val(num)
        elif self._parent._inner_setpoints

    def _set_integrate_time(self, val):
        self.integrate_time._save_val(val)
        self._reinstate_alazar_channels()

    def _reinstate_alazar_channels(self):
        self._parent.alazar_controller.channels.clear()
        settings = get_alazar_ch_settings(self._parent)
        for demod_ch in self._sidebanding_channels:
            demod_ch.alazar_channels.clear()
            self._create_and_add_alazar_channels(settings, demod_ch)

    def _create_and_add_alazar_channels(self, settings, demod_ch):
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
                                  integrate_samples=self.integrate_time())
        chan2 = AlazarChannel_ext(self._parent.alazar_controller,
                                  name=f'Q{demod_ch_num}_imaginaryphase',
                                  demod=True,
                                  average_records=settings['average_records'],
                                  average_buffers=settings['average_buffers'],
                                  integrate_samples=self.integrate_time())
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

    def _add_sidebanding_channel(self, frequency):
        """
        Creates a SidebandingChannel with a drive_frequency as
        specified and a pair of alazar channels which will readout
        at the drive_frequency of the SidebandingChannel but whose
        other settings are controlled by parameters of the readout
        channel (single_shot, demodulation_type, integrate_time, num)
        """
        demod_ch_num = len(self._sidebanding_channels)
        demod_ch = SidebandingChannel(
            self, 'Q{demod_ch_num}_readout'.format(demod_ch_num), demod_ch_num,
            drive_frequency=frequency)
        settings = get_alazar_ch_settings(self._parent)
        self._create_and_add_alazar_channels(settings, demod_ch)
        self._sidebanding_channels.append(demod_ch)
        self.add_submodule(f'Q{demod_ch_num}', demod_ch)
        return demod_ch

    @contextmanager
    def sideband_update(self):
        """
        Can be used for maintaining the drive_frequencies of the
        SidebandingChannels while changing the carrier_frequency
        """
        old_drives = [demod_ch.drive_frequency()
                      for demod_ch in self._sidebanding_channels]
        yield
        for i, demod_ch in enumerate(self.demod_chan_sidebanding_channelsnels):
            demod_ch.update(drive=old_drives[i])

    def update_all_alazar_channels(self):
        """
        Updates all of the alazar channels based on the current settings
        of the ParametricWaveformAnalyser. This is relevant if the
        ParametricSequencer sequence has been updated and the setpoints
        need to be changed or if 'num' (of repetitions or averages) has been
        changed.
        """
        settings = get_alazar_ch_settings(self._parent)
        for ch in self._parent.alazar_controller.channels:
            ch.update(settings)


class DriveChannel(InstrumentChannel):
    """
    An InstrumentChannel intended to belong to a ParametricWaveformAnalyser
    and which effectively groups the parameters related to drive including
    qubit_source parameters and pulse building parameters.

    Sidebanding channels can be added for each drive frequency.
    """

    def __init__(self, parent, name):
        super().__init(parent, name)

        # qubit source parameters
        self.add_parameter(name='power',
                           label='Drive Power',
                           unit='dBm',
                           parameter_class=DelegateParameter,
                           source=parent.qubit_source.power)
        self.add_parameter(name='carrier_frequency',
                           set_cmd=self._set_carrier_frequency,
                           initial_value=parent.qubit_source.frequency(),
                           label='Drive Carrier Frequency',
                           unit='Hz')

        # pulse building parameters
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
        self._sidebanding_channels = []

    @property
    def _pulse_building_parameters(self):
        pulse_building_parameters = {}
        for n, p in self.parameters.items():
            if isinstance(p, PulseBuildingParameter):
                pulse_building_parameters[p.pulse_building_name] = p
        for demod_ch in self._sidebanding_channels:
            pulse_building_parameters.update(
                demod_ch._pulse_building_parameters)
        return pulse_building_parameters

    def _set_carrier_frequency(self, carrier_freq):
        self._parent.qubit_source.frequency(carrier_freq)
        for demod_ch in self._sidebanding_channels:
            demod_ch.update()

    def _add_sidebanding_channel(self, frequency):
        """
        Creates a SidebandingChannel with a drive_frequency as
        specified.
        """
        demod_ch_num = len(self._demod_channels)
        demod_ch = SidebandingChannel(
            self, 'Q{}_drive'.format(demod_ch_num), demod_ch_num,
            drive_frequency=frequency)
        self._sidebanding_channels.append(demod_ch)
        self.add_submodule(f'Q{demod_ch_num}', demod_ch)
        return demod_ch

    @contextmanager
    def sideband_update(self):
        """
        Can be used for maintaining the drive_frequencies of the
        SidebandingChannels while changing the carrier_frequency
        """
        old_drives = [demod_ch.drive_frequency()
                      for demod_ch in self._sidebanding_channels]
        yield
        for i, demod_ch in enumerate(self.demod_chan_sidebanding_channelsnels):
            demod_ch.update(drive=old_drives[i])


class ParametricWaveformAnalyser(Instrument):
    """
    The PWA represents a composite instrument. It comprises a parametric
    sequencer, an Alazar card, a heterodyne source and a qubit source. The
    idea is that the parametric sequencer is used to sideband the heterodyne
    and the qubit source to create various drive and readout tones and also
    optionally to vary some parameter in a sequence. The
    setpoints of this sequence and the demodulation frequencies
    calculated from the heterodyne source demodulation frequency and the
    parametric sequencer sideband frequencies are communicated to the Alazar
    controller.
    """

    # TODO: write code for single microwave source

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
        self.suppress_sequence_upload = True
        readout_channel = ReadoutChannel(self, 'readout')
        self.add_submodule('readout', readout_channel)
        drive_channel = ReadoutChannel(self, 'drive')
        self.add_submodule('drive', drive_channel)
        self.qubits = {}

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

    @property
    def _pulse_building_parameters(self):
        pulse_building_parameters = {}
        pulse_building_parameters.update(
            self.readout._pulse_building_parameters)
        pulse_building_parameters.update(self.drive._pulse_building_parameters)
        return pulse_building_parameters

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
        self._save_val(mode)
        self.readout._reinstate_alazar_channels()

    def add_qubit(self, readout_frequency, drive_frequency):
        q_num = len(self.qubits)
        readout_ch = self.readout._add_sidebanding_channel(readout_frequency)
        drive_ch = self.drive._add_sidebanding_channel(drive_frequency)
        qubits['Q' + q_num] = {'readout': readout_ch, 'drive': drive_ch}

    def clear_qubits(self):
        qubits.clear()
        self.alazar_controller.alazar_channels.clear()
        self.readout._sidebanding_channels.clear()
        self.drive._sidebanding_channels.clear()

    @contextmanager
    def single_sequence_update(self):
        """
        For use when changing multiple PulseBuildingParameters at once
        ensures only one sequence upload.
        """
        initial_supression_value = self.suppress_sequence_upload
        self.suppress_sequence_upload = False
        yield
        self._update_sequence()
        self.suppress_sequence_upload = initial_supression_value

    def set_setpoints(self, inner_setpoints, outer_setpoints=None):
        """
        Sets the inner and outer setpoints on the sequencer and updates
        the alazar channels.

        NB works regardless of the status of suppress_sequence_upload
        """
        self.sequencer.set_setpoints(inner_setpoints, outer_setpoints)
        self.readout.update_all_alazar_channels()
        self._inner_setpoints = inner_setpoints
        self._outer_setpoints = outer_setpoints

    def set_template_element(self, template_element, first_element=None,
                             inner_setpoints=None, outer_setpoints=None,
                             context=None, labels=None, units=None):
        """
        Sets the template_element and the inner and outer setpoints on
        the sequencer and updates alazar channels. Generates context from
        pulse building parameters on readout and drive channels and their
        sidebanding channels and updates with any further context, labels
        and units provided.

        NB works regardless of the status of suppress_sequence_upload
        """
        self._template_element = template_element
        self._first_element = first_element
        alazar_needs_updating = False
        if self._inner_setpoints is None:
            if inner_setpoints is None:
                inner_setpoints = ('dummy_setpoint', [0])
            else:
                alazar_needs_updating = True
                self._inner_setpoints = inner_setpoints
        else:
            if inner_setpoints is None:
                self._inner_setpoints = None
                alazar_needs_updating = True
                inner_setpoints = ('dummy_setpoint', [0])
            elif not np.allclose(inner_setpoints, self._inner_setpoints):
                alazar_needs_updating = True
                self._inner_setpoints = inner_setpoints
        if self._outer_setpoints is None:
            if outer_setpoints is None:
                outer_setpoints = ('dummy_setpoint', [0])
            else:
                alazar_needs_updating = True
                self._outer_setpoints = outer_setpoints
        else:
            if outer_setpoints is None:
                self._outer_setpoints = None
                outer_setpoints = ('dummy_setpoint', [0])
            elif not np.allclose(outer_setpoints, self._outer_setpoints):
                alazar_needs_updating = True
                self._outer_setpoints = outer_setpoints

        context_to_upload, labels_to_upload, units_to_upload = self._generate_context()
        if context is None:
            context_to_upload.update(context)
        if labels is None:
            labels_to_upload.update(labels)
        if units is None:
            units_to_upload.update(units)
        self.sequencer.set_template(
            template_element,
            first_sequence_element=first_element,
            inner_setpoints=inner_setpoints,
            outer_setpoints=outer_setpoints,
            context=context_to_upload,
            labels=labels_to_upload,
            unit=units_to_upload)
        if alazar_needs_updating:
            self.readout.update_all_alazar_channels()

    def _generate_context(self):
        context = {}
        labels = {}
        units = {}
        for name, param in self._pulse_building_parameters.items():
            context[name] = param()
            labels[name] = param.label
            units[name] = param.unit
        return context, labels, units

    def _update_sequence(self):
        self.set_template_element(
            self._template_element, first_element=self._first_element,
            inner_setpoints=self._inner_setpoints, outer_setpoints=self._outer_setpoints)


def get_alazar_ch_settings(pwa):
    """
    Based on the current instrument settings calculates the settings
    configuration for an alazar channel as a dictionary with keys:

    buffers: int
    average_buffers: bool
    records: int
    average_records: bool

    and optionally:

    buffer_setpoints: array
    buffer_setpoint_name: str, None 
    buffer_setpoint_label: str, None 
    buffer_setpoint_unit: str, None 
    records_setpoints: array, None
    records_setpoint_name: str, None 
    records_setpoint_label: str, None 
    records_setpoint_unit: str, None 
    """
    seq_mode = pwa.seq_mode()
    num = pwa.readout.num()
    single_shot = pwa.readout.single_shot()
    if not single_shot:
        settings['average_buffers'] = True
        if (seq_mode and
                len(sequencer.get_inner_setpoints().values) > 1):
            if sequencer.get_outer_setpoints() is not None:
                logger.warn('Averaging channel will average over '
                            'outer setpoints of sequencer sequence')
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
            settings['buffer_setpoints'] = np.arange(buffers)
            settings['buffer_setpoint_name'] = 'buffer_repetitions'
            settings['buffer_setpoint_label'] = 'Buffer Repetitions'
    return settings
