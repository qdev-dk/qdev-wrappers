from typing import Callable
from copy import deepcopy

# broadbean extentions
import broadbean as bb
from broadbean import Element

def pushElement(self, element: bb.Element) -> None:
    self.addElement(self.length_sequenceelements, element)


bb.Sequence.pushElement = pushElement


class ParametricSequencer:
    """
    Take a step back to make it more general, and keep the ParametricWaveforms in the background
    Args:
    builder:  f_with_footprint(buffer_index:int, buffer_setpoint:float,
    record_index: int, record_setpoint:float) -> bb.Element

    """

    def __init__(self,
                 builder: Callable,
                 parameters: List[List[Dict[str, float]]],
                 integration_delay: float = None,
                 integration_time: float = None,
                 record_set_points: List[float] = None,
                 buffer_set_points: List[float] = None,
                 sequencing_mode: bool =True,
                 n_averages=1):
        # TODO: add units and labels
        self.integration_delay = integration_delay
        self.integration_time = integration_time
        self.record_set_points = record_set_points
        self.buffer_set_points = buffer_set_points
        self.parameters = parameters

        self.average_records = self.record_set_points is not None:
        self.average_buffers = self.buffer_set_points is not None:
        self.average_time = self.integration_delay is not None and self.integration_time is not None
        self.records_per_buffer = len(
            self.record_set_points) if not self.average_records else None
        self.buffers_per_acquisition = len(
            self.buffer_set_points) if not self.average_buffers else None

        if not self.average_records and not self.average_buffers and n_averages > 1:
            raise RuntimeError(
                'You are not averaging records or buffers so you cannot really '
                'expect to have n_averages > 1 can you now?')
        self.n_averages = n_averages

        self.check_parameters()

    def check_parameters(self):
        # check buffer setpoints with parameters
        if not self.average_buffers:
            if len(self.parameters) > 1 and len(self.buffer_set_points) != len(self.parameters):
            raise RuntimeError(
                'Number of buffers implied by parameter '
                'list does not match buffer_set_points.')

        # check record setpoints with parameters
        if not self.average_records:
            record_paremeter_lengths = [len(rec_p)
                                        for rec_p in self.parameters]
            if len(set(record_paremeter_lengths)) != 1:
                raise RuntimeError(
                    'Number of records per buffer implied by '
                    'parameter list is not consistent between buffers')
            if record_paremeter_lengths[0] > 1 and len(self.record_set_points) != record_paremeter_lengths[0]:
                raise RuntimeError(
                    'Number of records implied by parameter '
                    'list does not match record_set_points.')

    def create_sequence(self) -> bb.Sequence:
        # this is the simple and naïve way, without any repeat elements
        # but one can simply add them here
        sequence = bb.Sequence()
        for buffer_index, buffer_set_point in enumerate(self.buffer_set_points or 1):
            for record_index, record_set_point in enumerate(self.record_set_points or 1):
                parms = parameters[buffer_index][record_index]
                element = builder(parms)
                sequence.pushElement(element)
        return sequence

    # TODO: implement
    # TODO: implement as stream
    def serialize(self) -> str:
        return "Not yet implemented"

    def deserialize(self, str) -> None:
        pass


class ParametricWaveformAnalyser:


"""
The PWA represents a composite instrument. It is similar to a spectrum analyzer, but instead of a sine wave it probes using waveforms described through a set of parameters.
For that functionality it compises an AWG and a Alazar as a high speed ADC.
    Attributes:
        sequencer (ParametricSequencer): represents the current sequence in parametric form and can be rendered into an uploadable sequence
            alazar
        awg
"""
    # TODO: make instruments private?
    def __init__(self, station: Station=None, awg=None, alazar=None, alazar_controller=None) -> None:
        self.station, self.awg, self.alazar = station, awg, alazar
        self.alazar_controller = alazar_controller
        self.alazar_channels = self.alazar_controller.channels
        self._demod_ref = None

    # implementations
    def update_sequencer(self, sequencer):
        self.sequencer = sequencer
        # see how this needs to be converted, to and from the json config
        station.components['sequencer'] = self.sequencer.serialize()
        seq = self.sequencer.create_sequence()

        self.awg.upload(seq)
        self.awg.start()

    def set_demod_freq(self, f_demod):
        for ch in self.alazar_channels:
            ch.demod_freq(f_demod)
        self._demod_ref = f_demod

    def setup_alazar(self):
        # Magnitude, phase,I, Q?
        # need to be called when setting a new sequencer
        # set alazar in the right averaging mode
        if self.alazar_channels is not None:
            del self.alazar_channels
            # TODO: try to remove it from the channel list
            # self.alazar_controller.channels.remove(chan_m)
            # remove all channels
        # setup controller
        self.alazar_controller.int_time(self.sequencer.integration_time)
        self.alazar_controller.int_delay(self.sequencer.integration_delay)
        # setup channels
        chan_m = AlazarChannel(self.alazar_controller,
                               demod=self._demod_ref is not None,
                               average_buffers=self.sequencer.average_buffers,
                               average_records=self.sequencer.average_records,
                               integrate_samples=self.sequencer.average_time)
        chan_m.demod_freq(self._demod_ref)
        chan_m.num_averages(self.sequencer.n_averages)
        if not self.sequencer.average_records:
            chan_m.records_per_buffer(len(self.sequencer.records_per_buffer))
        chan_m.prepare_channel()  # sets setpoints and labels
        # this is a problem, can I not get magnitude and phase at the same time?
        chan_p = deepcopy(chan_m)
        chan_m.demod_type('magnitude')
        chan_p.demod_type('phase')
        # set the labels correctly here chan_m.data.setpoint_labels/units setpoints....
        # data is MultidimParameter
        self.alazar_controller.channels.append(chan_m)
        self.alazar_controller.channels.append(chan_p)
        self.alazar_channels = self.alazar_controller.channels

    # def get(self):
    #     # must have called update_sequence before
    #     # trigger alazar
    #     return self.alazar_controller.channels.data

    # def load_aquisition_parametes(metadata_from_station)->Dict:
    #     pass

    # implement shownums equivalent for acquisition parameters and sequencers
