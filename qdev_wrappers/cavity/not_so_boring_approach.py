from typing import Callable, Dict, List
from copy import deepcopy
import re
from os.path import sep
from qcodes import Station, Instrument
from qdev_wrappers.alazar_controllers.ATSChannelController import ATSChannelController
from qdev_wrappers.alazar_controllers.acquisition_parameters import NonSettableDerivedParameter
from qdev_wrappers.alazar_controllers.alazar_channel import AlazarChannel
from qdev_wrappers.transmon.file_helpers import get_subfolder_location
from qcodes.instrument.channel import InstrumentChannel


class ParametricSequencer:
    """
    Take a step back to make it more general, and keep the
    ParametricWaveforms in the background
    Args:
    builder:  f_with_footprint(buffer_index:int, buffer_setpoint:float,
    record_index: int, record_setpoint:float) -> bb.Element

    """

    def __init__(self,
                 builder: Callable,
                 builder_parms: Dict=None,
                 default_parms: Dict[str, float] = None,
                 integration_delay: float = 0,
                 integration_time: float = 1e-6,
                 average_time: bool = True,
                 record_setpoints: List[float] = None,
                 buffer_setpoints: List[float] = None,
                 record_set_parameter: str = None,
                 buffer_set_parameter: str = None,
                 record_setpoint_name: str = None,
                 record_setpoint_label: str = None,
                 record_setpoint_unit: str = None,
                 buffer_setpoint_name: str = None,
                 buffer_setpoint_label: str = None,
                 buffer_setpoint_unit: str = None,
                 sequencing_mode: bool = True,
                 n_averages=1):
        self.integration_delay = integration_delay
        self.integration_time = integration_time
        self.record_setpoints = record_setpoints
        self.buffer_setpoints = buffer_setpoints
        self.record_setpoint_name = record_setpoint_name
        self.record_setpoint_label = record_setpoint_label or record_setpoint_name
        self.record_setpoint_unit = record_setpoint_unit
        self.buffer_setpoint_name = buffer_setpoint_name
        self.buffer_setpoint_label = buffer_setpoint_label or buffer_setpoint_name
        self.buffer_setpoint_unit = buffer_setpoint_unit
        self.builder = builder
        self.builder_parms = builder_parms or {}

        self.average_records = self.record_setpoints is None
        self.average_buffers = self.buffer_setpoints is None
        self.average_time = average_time
        if record_setpoints is not None:
            self.records_per_buffer = len(record_setpoints)
        if buffer_setpoints is not None:
            self.buffers_per_acquisition = len(buffer_setpoints)
        self.n_averages = n_averages

        self.check_parameters()

    def check_parameters(self):
        # check record setpoints with parameters
        if not self.average_records:
            record_paremeter_lengths = [len(rec_p)
                                        for rec_p in self.parameters]
            if len(set(record_paremeter_lengths)) != 1:
                raise RuntimeError(
                    'Number of records per buffer implied by '
                    'parameter list is not consistent between buffers')
            if (record_paremeter_lengths[0] > 1 and
                    len(self.record_setpoints) != record_paremeter_lengths[0]):
                raise RuntimeError(
                    'Number of records implied by parameter '
                    'list does not match record_setpoints.')

        # check labels, units, names
        if self.record_setpoints is None:
            if any([self.record_setpoint_label, self.record_setpoint_name,
                    self.record_setpoint_unit]):
                raise RuntimeError(
                    'Not able to set record setpoint name,'
                    ' label or unit as no record setpoints are specified.')
        if self.buffer_setpoints is None:
            if any([self.buffer_setpoint_label, self.buffer_setpoint_name,
                    self.buffer_setpoint_unit]):
                raise RuntimeError(
                    'Not able to set buffer setpoint name,'
                    ' label or unit as no buffer setpoints are specified.')

    def create_sequence(self, **kwargs):  # -> bb.Sequence:
        return self.builder(**self.builder_parms, **kwargs)
#        # this is the simple and naïve way, without any repeat elements
#        # but one can simply add them here
#        sequence = bb.Sequence()
#        for buffer_index, buffer_setpoint in enumerate(self.buffer_setpoints or 1):
#            for record_index, record_setpoint in enumerate(self.record_setpoints or 1):
#                parms = parameters[buffer_index][record_index]
#                element = builder(parms)
#                sequence.pushElement(element)
#        return sequence

    # TODO: implement
    # TODO: implement as stream
    def serialize(self) -> str:
        return "Not yet implemented"

    def deserialize(self, str) -> None:
        pass


class DemodulationChannel(InstrumentChannel):
    def __init__(self, parent, name: str, drive_frequency=None) -> None:
        # TODO: somehow couple to alazar channel?
        # TODO: smarter logic on when sequence and alazar are 'out of date'
        super().__init__(parent, name)
        self.add_parameter(
            name='sideband_frequency',
            alternative='drive_frequency, heterodyne_source.frequency',
            parameter_class=NonSettableDerivedParameter)
        self.add_parameter(
            name='demodulation_frequency',
            alternative='drive_frequency, heterodyne_source.demodulation_frequency',
            parameter_class=NonSettableDerivedParameter)
        self.add_parameter(
            name='drive_frequency',
            set_cmd=self._set_drive_freq)
        if drive_frequency is not None:
            self.drive_frequency(drive_frequency)

    def _set_drive_freq(self, index, drive_frequency):
        sideband = self._parent._carrier_frequency - drive_frequency
        demod = self._parent._base_demodulation_frequency + sideband
        self.sideband_frequency._save_val(sideband)
        self.demodulation_frequency._save_val(demod)
        self._parent._sequence_up_to_date = False
        self._parent._alazar_up_to_date = False

    def update(self, sideband=None, drive=None):
        base_demod = self._parent._base_demod_freq
        carrier = self._parent._carrier_freq
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
        self.sideband_frequency._save_val(sideband)
        self.demodulation_frequency._save_val(demod)
        self.drive_frequency._save_val(drive)
        self._parent._sequence_up_to_date = False
        self._parent._alazar_up_to_date = False


class ParametricWaveformAnalyser(Instrument):
    """
    The PWA represents a composite instrument. It is similar to a
    spectrum analyzer, but instead of a sine wave it probes using
    waveforms described through a set of parameters.
    For that functionality it compises an AWG and a Alazar as a high speed ADC.
        Attributes:
            sequencer (ParametricSequencer): represents the current
                sequence in parametric
            form and can be rendered into an uploadable sequence
                alazar
            awg
    """
    # TODO: write code for single microwave source
    # TODO: alazar seq mode on/off

    def __init__(self,
                 name: str,
                 station: Station=None,
                 awg=None, alazar=None) -> None:
        super().__init__(name)
        self.station, self.awg, self.alazar = station, awg, alazar
        self.alazar_controller = ATSChannelController(
            'pwa_controller', alazar.name)
        self.alazar_channels = self.alazar_controller.channels
        self.sequencer = None
        self._sequence_up_to_date = False
        self._alazar_up_to_date = False
        self._rogue_mode = False
        self._base_demod_freq = None
        self._carrier_freq = None

        channels = ChannelList(self, "Channels", DemodulationChannel)
        self.add_submodule("sidebanded_readout_channels", channels)

        self.alazar_channels.data.get = partial(self.get_alazar_channels)

    def update_base_demod_frequency(self, f_demod, update_alazar=True):
        self._base_demod_freq = f_demod
        for demod_ch in self.sidebanded_readout_channels:
            demod_ch.update()
        if update_alazar:
            self.clear_alazar_channels()
            self.set_alazar_channels()
        else:
            self._alazar_up_to_date = False

    def update_carrier_frequency(self, carrier_freq, update_sidebands=True,
                                 update_alazar=True):
        self._carrier_freq = carrier_freq
        for demod_ch in self.sidebanded_readout_channels:
            if update_sidebands:
                old_drive = demod_ch.drive_frequency()
                demod_ch.update(drive=old_drive)
            else:
                demod_ch.update()
        if update_alazar:
            self.clear_alazar_channels()
            self.set_alazar_channels()
        else:
            self._alazar_up_to_date = False

    def add_sidebanded_readout_channel(self, drive_frequency):
        ch_num = len(self.sidebanded_readout_channels)
        # TODO: chennel naming here and generally
        ch = DemodulationChannel(self, 'readout_demod_ch_{}'.format(ch_num),
                                 drive_frequency=drive_frequency)

    def clear_sidebanded_readout_channels():
        for ch in list(self.sidebanded_readout_channels):
            self.sidebanded_readout_channels.remove(ch)

    def update_sequencer(self, save_sequence=True, update_alazar=True):
        sideband_frequencies = [ch.sideband_frequency()
                                for ch in self.sidebanded_readout_channels]
        sequence = self.sequencer.create_sequence(
            readout_SSBfreqs=sideband_frequencies)
        unwrapped_seq = sequence.unwrap()[0]
        awg_file = self.awg.make_awg_file(*unwrapped_seq)
        filename = sequence.name + '.awg'
        self.awg.send_and_load_awg_file(awg_file, filename)
        self.awg.all_channels_on()
        self.awg.run()
        self._sequence_up_to_date = True
        if save_sequence:
            local_filename = sep.join(
                [get_subfolder_location('waveforms'), filename])
            with open(local_filename, 'wb') as fid:
                fid.write(awg_file)
        if update_alazar:
            self.clear_alazar_channels()
            self.alazar_controller.int_time(self.sequencer.integration_time)
            self.alazar_controller.int_delay(self.sequencer.integration_delay)
            self.set_alazar_channels()
        else:
            self._alazar_up_to_date = False
        self.alazar.seq_mode('on')

    def set_up_sequence(self, sequencer, save_sequence=True,
                        update_alazar=True):
        # see how this needs to be converted, to and from the json config
        #        self.station.components['sequencer'] = self.sequencer.serialize()
        self.sequence = sequencer
        self.update_sequencer(save_sequence=save_sequence,
                              update_alazar=update_alazar)

    def add_alazar_channel_single(self, name, sequencer, dtype='m',
                                  demod_freq=None):
        chan = AlazarChannel(self.alazar_controller,
                             name=name,
                             demod=demod_freq is not None,
                             average_buffers=sequencer.average_buffers,
                             average_records=sequencer.average_records,
                             integrate_samples=sequencer.average_time)
        if demod_freq is not None:
            chan.demod_freq(demod_freq)
        chan.num_averages(sequencer.n_averages)
        if not sequencer.average_records:
            chan.records_per_buffer(sequencer.records_per_buffer)
        if not sequencer.average_buffers:
            chan.buffers_per_acquisition(
                sequencer.buffers_per_acquisition)
        chan.prepare_channel(
            record_setpoints=sequencer.record_setpoints,
            buffer_setpoints=sequencer.buffer_setpoints,
            record_setpoint_name=sequencer.record_setpoint_name,
            record_setpoint_label=sequencer.record_setpoint_label,
            record_setpoint_unit=sequencer.record_setpoint_unit,
            buffer_setpoint_name=sequencer.buffer_setpoint_name,
            buffer_setpoint_label=sequencer.buffer_setpoint_label,
            buffer_setpoint_unit=sequencer.buffer_setpoint_unit)
        if dtype == 'm':
            chan.demod_type('magnitude')
            chan.data.label = 'Cavity Magnitude Response'
        elif dtype == 'p':
            chan.demod_type('phase')
            chan.data.label = 'Cavity Phase Response'
        else:
            raise NotImplementedError(
                'only magnitude and phase currently implemented')
        chan.data.get = partial(get_alazar_data)
        self.alazar_controller.channels.append(chan)

    def set_alazar_channels(self):
        if len(self.sidebanded_readout_channels) > 0:
            for demod_ch, i in enumerate(self.sidebanded_readout_channels):
                m_name = '{}_{}_{}'.format(self.sequencer.name, i, 'm')
                p_name = '{}_{}_{}'.format(self.sequencer.name, i, 'm')
                self.add_alazar_channel_single(
                    m_name, self.sequencer, dtype='m',
                    demod_freq=demod_ch.demodulation_frequency())
                self.add_alazar_channel_single(
                    p_name, self.sequencer, dtype='p',
                    demod_freq=demod_ch.demodulation_frequency())
        else:
            m_name = '{}_{}'.format(self.sequencer.name, 'm',)
            p_name = '{}_{}'.format(self.sequencer.name, 'm')
            self.add_alazar_channel_single(
                m_name, self.sequencer, dtype='m',
                demod_freq=self._base_demod_freq)
            self.add_alazar_channel_single(
                p_name, self.sequencer, dtype='p',
                demod_freq=self._base_demod_freq)
        self._alazar_up_to_date = True

    def clear_alazar_channels(self):
        if self.alazar_channels is not None:
            for ch in list(self.alazar_channels):
                self.alazar_channels.remove(ch)

    def get_alazar_data(self, alazar_ch_get_fn_to_check):
        if not self._rouge mode:
            if not self._sequence_up_to_date:
                raise RuntimeError(
                    'sequencer not up to date, run "update_sequencer"')
            if not self._alazar_up_to_date:
                raise RuntimeError(
                    'alazar not up to date, run "set_alazar_channels"')
        return alazar_ch_get_fn_to_check

    # def get(self):
    #     # must have called update_sequence before
    #     # trigger alazar
    #     return self.alazar_controller.channels.data

    # def load_aquisition_parametes(metadata_from_station)->Dict:
    #     pass

    # implement shownums equivalent for acquisition parameters and sequencers
