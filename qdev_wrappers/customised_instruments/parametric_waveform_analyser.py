from typing import Callable, Dict, List
from copy import deepcopy
import re
from itertools import compress
from functools import partial
from os.path import sep
import numpy as np
from qcodes import Station, Instrument
from qdev_wrappers.alazar_controllers.ATSChannelController import ATSChannelController
from qdev_wrappers.alazar_controllers.acquisition_parameters import NonSettableDerivedParameter
from qdev_wrappers.alazar_controllers.alazar_channel import AlazarChannel
from qdev_wrappers.transmon.file_helpers import get_subfolder_location
from qcodes.instrument.channel import InstrumentChannel
from qcodes import Parameter
logger = logging.getLogger(__name__)


class DemodulationChannel(InstrumentChannel):
    def __init__(self, parent, name: str, drive_frequency=None) -> None:
        """
        This is a channel which does the logic assuming a carrier microwave source
        and a local os separated by 'base_demod' which the parent of this channel
        knows about. The channel then takes care of working out what frequency will actually
        be output ('drive') if we sideband the carrier byt a 'sideband' and what the total
        demodulation frequency is in this case 'demodulation'.

        Note that no actual mocrowave sources are updated and we expect any heterodyne source used
        with this to do the legwork and update the parent carrier and base_demod

        Note that no awg is actaully connected so all it does is mark a flag as False

        Note that it DOES however have access to alazar channels so it can update their demod
        frequency and there is also a channel list so you could get the measurmenemts for everything
        demodulated at this one frequency which should correspond to measuring one qubit :)

        # TODO: what about if we have new fancy version with only one microwave source
        or if we don't sideband?
        """
        super().__init__(parent, name)
        self._parent.sequencer.sequence_up_to_date = False
        self.add_parameter(
            name='sideband_frequency',
            alternative='drive_frequency, heterodyne_source.frequency',
            parameter_class=NonSettableDerivedParameter)
        self.add_parameter(  # TODO: lose this as a parameter since it already lives on the alazar channels and can always be worked out..?
            name='demodulation_frequency',
            alternative='drive_frequency, heterodyne_source.demodulation_frequency',
            parameter_class=NonSettableDerivedParameter)
        self.add_parameter(
            name='drive_frequency',
            set_cmd=self._set_drive_freq)
        alazar_channels = ChannelList(
            self, "Channels", AlazarChannel,
            multichan_paramclass=AlazarMultiChannelParameter)
        self.add_submodule("alazar_channels", channels)
        if drive_frequency is not None:
            self.drive_frequency(drive_frequency)

    def _set_drive_freq(self, index, drive_frequency):
        """
        changes the sideband frequencies in order to get the required drive,
        marks the awg as not up to date and updates the demodulation
        frequencies on the relevant alazar channels
        """
        sideband = self._parent._carrier_frequency - drive_frequency
        demod = self._parent._base_demodulation_frequency + sideband
        self.sideband_frequency._save_val(sideband)
        self._parent.sequencer._sequence_up_to_date = False
        self.demodulation_frequency._save_val(demod)
        for ch in self.averaging_channels:
            ch.demod_freq(demod)

    def update(self, sideband=None, drive=None):
        """
        updates everything based on the carrier and base demod of the parent, either 
        using existing settings or if a new drive is specified will update the sideband
        or a new sideband specified will cause the drive to be updated
        """
        base_demod = self._parent._base_demod_freq
        carrier = self._parent._carrier_freq
        old_sideband = self.sideband_frequency()
        old_demod = self.demodulation_frequency()
        if sideband is not None and drive is not None:
            raise RuntimeError('Cannot set drive and sideband simultaneously')
        elif sideband is not None:
            drive = carrier - sideband
        elif drive is not None:
            sideband = carrier - drive
        else:
            sideband = self.sideband_frequency()
            drive = self.drive_frequency()
        demod = base_demod + sideband
        if old_sideband != sideband:
            self.sideband_frequency._save_val(sideband)
            self._parent.sequencer._sequence_up_to_date = False
        self.drive_frequency._save_val(drive)
        if demod != old_demod:
            self.demodulation_frequency._save_val(demod)
            for ch in self.averaging_channels:
                ch.demod_freq(demod)




class ParametricWaveformAnalyser(Instrument):
    """
    The PWA represents a composite instrument. It is similar to a
    spectrum analyzer, but instead of a sine wave it probes using
    waveforms described through a set of parameters.
    For that functionality it compises an AWG and a Alazar as a high speed ADC.
    """
    # TODO: write code for single microwave source
    def __init__(self,
                 name: str,
                 sequencer,
                 alazar,
                 station: Station=None) -> None:
        super().__init__(name)
        self.add_parameter('')
        self.station, self.sequencer, self.alazar = station, sequencer, alazar
        self.alazar_controller = ATSChannelController(
            'pwa_controller', alazar.name)
        self._alazar_up_to_date = False
        self._base_demod_freq = None  # TODO: make this a parameter?
        self._carrier_freq = None  # TODO: make this a parameter?
        self.add_parameter(name='int_time',
                           set_cmd=self._set_int_time,
                           parameter_class=DelegateParameter,
                           source=self.alazar_controller.int_time)
        self.add_parameter(name='int_delay',
                           set_cmd=self._set_int_delay,
                           parameter_class=DelegateParameter,
                           source=self.alazar_controller.int_delay)
        self.add_parameter(name='seq_mode',
                           set_cmd=self._set_seq_mode,
                           get_cmd=self._get_seq_mode)
        demod_channels = ChannelList(self, "Channels", DemodulationChannel)
        self.add_submodule("demodulation_channels", channels)
        self.alazar_channels = self.alazar_controller.alazar_channels

    def _set_int_delay(self, int_delay):  # TODO: nicer way to do this?
        self._alazar_up_to_date = False

    def _set_int_time(self, int_delay):  # TODO: nicer way to do this?
        self._alazar_up_to_date = False

    def _set_seq_mode(self, mode):
        """
        updated the sequencing mode on the alazar and the awg and reset all the alazar
        channels so that they average over everything which is a sensible default for 
        if we are just playing one element on loop
        # TODO: what if we also want statistics or a time trace?
        # TODO: num_averages
        # TODO: the newest alazar doesn't actually have seq_mode...
        """
        self.sequencer.seq_mode(mode)
        self.alazar.seq_mode(mode)
        if not mode:
            self.clear_alazar_channels()
            for i in range(len(self.demodulation_channels)):
                self.add_alazar_channel(i, 'm', [True, True, True])
                self.add_alazar_channel(i, 'm', [True, True, True])

    def _get_seq_mode():
        if self.alazar.seq_mode() and self.sequencer.seq_mode():
            return True
        elif not self.alazar.seq_mode() and not self.sequencer.seq_mode():
            return False
        else:
            raise RuntimeError(
                'seq modes on sequencer and alazar do not match')

    def update_base_demod_frequency(self, f_demod):
        """
        update the demodulation frequency locally and also runs update
        on the demodulation channels to propagate this to the demodulation
        frequencies after sidebanding which should end up on the alazar channels
        """
        self._base_demod_freq = f_demod
        for demod_ch in self.demodulation_channels:
            demod_ch.update()

    def update_carrier_frequency(self, carrier_freq, update_sidebands=True):
        """
        update the carrier frequency locally and also runs update
        on the demodulation channels to propagate this to the demodulation
        frequencies after sidebanding which should end up on the alazar channels
        there is option to change the sidebands to keep the resultant drive
        frequencies the same or to leave them as is and then the drive changes
        """
        self._carrier_freq = carrier_freq
        for demod_ch in self.demodulation_channels:
            if update_sidebands:
                old_drive = demod_ch.drive_frequency()
                demod_ch.update(drive=old_drive)
            else:
                demod_ch.update()

    def add_sidebanded_readout_channel(self, drive_frequency):
        """
        adds a demodulation frequency for readout and then adds alazar
        channels with averaging settings and setpoints based on the current
        sequence
        """
        demod_ch_num = len(self.demodulation_channels)
        demod_ch = DemodulationChannel(
            self, 'readout_demod_ch_{}'.format(demod_ch_num),
            drive_frequency=drive_frequency)
        self.demodulation_channels.append(demod_ch)
        self.add_alazar_channel(demod_ch_num, 'm')
        self.add_alazar_channel(demod_ch_num, 'p')

    def clear_demodulation_channels():
        """
        clears all demodulation_channels and the alazar_channels
        """
        for ch in list(self.demodulation_channels):
            self.demodulation_channels.remove(ch)
        for ch in list(self.alazar_channels):
            self.alazar_channels.remove(ch)
        self._alazar_up_to_date = False
        self.sequencer.sequence_up_to_date = False

    def add_alazar_channel(self, demod_ch_num, dtype, averaging_settings=None):
        """
        adds an alazar channel with the demodulation frequency matching the demod_ch
        with demod_ch_num, dtype is 'm' or 'p' for magnitude or phase and the
        averaging settings will default to those defined by the sequencing but
        you can always choose your own sensible ones

        Args: averaging_settings: [int_samples, ave_rec, ave buf]
        """
        name = '{}_{}_{}'.format(self.sequencer.name, demod_ch_num, dtype)
        if averaging_settings is None:
            name = '{}_{}_{}'.format(self.sequencer.name, demod_ch_num, dtype)
            average_records = self.sequencer.inner_setpoints()[
                'setpoints'] is None
            average_buffers = self.sequencer.outer_setpoints()[
                'setpoints'] is None
            integrate_samples = True
        else:
            appending_string = '_'.join(
                list(compress(
                    ['samples', 'records', 'buffers'], averaging_settings)))
            name.append(list(appending_string))
            integrate_samples, average_records, average_buffers = averaging_settings
        chan = AlazarChannel(self.alazar_controller,
                             name=name,
                             demod=True,
                             average_buffers=average_buffers,
                             average_records=average_records,
                             integrate_samples=integrate_samples)
        chan.demod_freq(
            self.demodulation_channels[demod_ch_num].demodulation_frequency())
        if not average_records:
            chan.records_per_buffer(
                len(self.sequencer.inner_setpoints()['setpoints']))
        if not average_buffers:
            chan.buffers_per_acquisition(
                len(self.sequencer.outer_setpoints()['setpoints']))
        chan.num_averages(num_averages)
        chan.prepare_channel(
            record_setpoints=self.sequencer.inner_setpoints()['setpoints'],
            buffer_setpoints=self.sequencer.outer_setpoints()['setpoints'],
            record_setpoint_name=self.sequencer.inner_setpoints()['name'],
            record_setpoint_label=self.sequencer.inner_setpoints()['label'],
            record_setpoint_unit=self.sequencer.inner_setpoints()['unit'],
            buffer_setpoint_name=self.sequencer.outer_setpoints()['name'],
            buffer_setpoint_label=self.sequencer.outer_setpoints()['label'],
            buffer_setpoint_unit=self.sequencer.outer_setpoints()['unit'])
        if dtype == 'm':
            chan.demod_type('magnitude')
            chan.data.label = 'Cavity Magnitude Response'
        elif dtype == 'p':
            chan.demod_type('phase')
            chan.data.label = 'Cavity Phase Response'
        else:
            raise NotImplementedError(
                'only magnitude and phase currently implemented')
        self.alazar_controller.channels.append(chan)
        self.demodulation_channels.alazar_channels.append(chan)

    def update_alazar(self):
        """
        deletes all alazar channels and makes new ones at each demod freq and which
        match the current sequence
        """
        self.clear_alazar_channels()
        for i in range(len(self.demodulation_channels)):
            self.add_alazar_channel(i, 'm')
            self.add_alazar_channel(i, 'p')
        self._alazar_up_to_date = True

    def clear_alazar_channels(self):
        """
        clears all alzar channels
        """
        if self.alazar_channels is not None:
            for ch in list(self.alazar_channels):
                self.alazar_channels.remove(ch)
            for demod_ch in list(self.demodulation_channels):
                for alazar_ch in demod_ch.alazar_channels:
                    demod_ch.alazar_channels.remove(alazar_ch)
        self._alazar_up_to_date = False

    def update_sequencer(self, builder=None, inner_setpoints=None,
                         outer_setpoints=None, default_builder_parms=None):
        """
        a way to update the sequencer through the pwa to update any of the sequencer
        settings but also updates the sudebands based on the current demodulation
        channel parameters and runs update_sequence on the sequencer
        """
        if builder is not None:
            self.sequencer.builder(builder)
        if inner_setpoints is not None:
            self.inner_setpoints(inner_setpoints)
        if outer_setpoints is not None:
            self.outer_setpoints(outer_setpoints)
        if default_builder_parms is not None:
            self.default_builder_parms(default_builder_parms)
        ssb_frequencies = [ch.sideband_frequency()
                           for ch in self.demodulation_channels]
        self.sequence.default_builder_parms(
            {'readout_ssb_frequencies': ssb_frequencies})
        self.sequencer.update_sequence()
