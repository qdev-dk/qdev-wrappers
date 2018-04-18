from typing import Callable, Dict, List
from copy import deepcopy
import re
from qcodes import Station, Instrument
from qdev_wrappers.alazar_controllers.ATSChannelController import ATSChannelController
from qdev_wrappers.alazar_controllers.alazar_channel import AlazarChannel
from qdev_wrappers.transmon.awg_helpers import make_save_send_load_awg_file


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

#        self.check_parameters()

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

    def create_sequence(self):  # -> bb.Sequence:
        return self.builder(**self.builder_parms)
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
    # TODO: make instruments private?

    def __init__(self,
                 name: str,
                 station: Station=None,
                 awg=None, alazar=None) -> None:
        super().__init__(name)
        self.station, self.awg, self.alazar = station, awg, alazar
        self.alazar_controller = ATSChannelController(
            'pwa_controller', alazar.name)
        self.alazar_channels = self.alazar_controller.channels
        self._demod_refs = None

    def set_up_sequence(self, sequencer, save_sequence=True,
                        update_alazar=True):
        self.sequencer = sequencer
        # see how this needs to be converted, to and from the json config
#        self.station.components['sequencer'] = self.sequencer.serialize()
        sequence = self.sequencer.create_sequence()
        unwrapped_seq = sequence.unwrap()[0]
        if save_sequence:
            self.awg.make_and_save_awg_file(
                *unwrapped_seq, filename=sequence.name + '.awg')
        self.awg.make_send_and_load_awg_file(*unwrapped_seq)
        self.awg.all_channels_on()
        self.awg.run()
        if update_alazar:
            self.clear_alazar_channels()
            self.alazar_controller.int_time(self.sequencer.integration_time)
            self.alazar_controller.int_delay(self.sequencer.integration_delay)
            self.set_alazar_channels()

    @classmethod
    def name_stripper(name):
        return re.search(r'(.*)_(\d*)_([a-z])', name).groups()

    def set_demod_freq(self, *f_demods, update_alazar=True):
        self._demod_refs = f_demods
        if update_alazar:
            self.clear_alazar_channels()
            self.set_alazar_channels()

    def add_alazar_channel_single(self, sequencer, dtype='m', demod_index=0):
        chan = AlazarChannel(self.alazar_controller,
                             '{}_{}_{}'.format(
                                 sequencer.name, demod_index, dtype),
                             demod=self._demod_ref is not None,
                             average_buffers=sequencer.average_buffers,
                             average_records=sequencer.average_records,
                             integrate_samples=sequencer.average_time)
        if self._demod_refs is not None:
            chan.demod_freq(self._demod_ref[demod_index])
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
        self.alazar_controller.channels.append(chan)

    def set_alazar_channels(self):
        for i in range(len(self._demod_refs)):
            self.add_alazar_channel_single(
                self.sequencer, dtype='m', demod_index=i)
            self.add_alazar_channel_single(
                self.sequencer, dtype='p', demod_index=i)

    def clear_alazar_channels(self):
        if self.alazar_channels is not None:
            for ch in list(self.alazar_channels):
                self.alazar_channels.remove(ch)

    # def get(self):
    #     # must have called update_sequence before
    #     # trigger alazar
    #     return self.alazar_controller.channels.data

    # def load_aquisition_parametes(metadata_from_station)->Dict:
    #     pass

    # implement shownums equivalent for acquisition parameters and sequencers
