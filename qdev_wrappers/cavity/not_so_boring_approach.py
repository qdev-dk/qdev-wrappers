from typing import Callable
from copy import deepcopy

# broadbean extentions
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
    def __init__(builder: Callable,
                 integration_delay:float = None,
                 integration_time:float = None,
                 record_set_points:List[float] = None,
                 buffer_set_points:List[float] = None,
                 sequencing_mode:bool =True,
                 n_averages = 1):
        # TODO: add units and labels
        self.integration_delay = integration_delay
        self.integration_time = integration_time
        self.record_set_points = record_set_points
        self.buffer_set_points = buffer_set_points

        self.average_records = self.record_set_points is not None:
        self.average_buffers = self.buffer_set_points is not None:
        self.average_time = self.integration_delay is not None and self.integration_time is not None

    def create_sequence(self) -> bb.Sequence:
        # this is the simple and naïve way, without any repeat elements
        # but one can simply add them here
        sequence = bb.Sequence()
        for buffer_index, buffer_set_point in enumerate(self.buffer_set_points):
            for record_index, record_set_point in enumerate(self.record_set_points):
                element = build_element(buffer_index, buffer_setpoint,
                                        record_index, record_setpoint)
                sequence.pushElement(element)
        return sequence

    # TODO: implement
    # TODO: implement as stream
    def serialize(self) -> str:
        # TODO: explain this to Natalie ;)
        return "Not yet implemented"

    def deserialize(self, str) -> None:
        # TODO: explain this to Natalie ;)
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
    def __init__(station: Station=None, awg=None, alazar=None) -> None:
        self.station, self.awg, self.alazar = station, awg, alazar
        # create alazar controller
        # TODO: why create alazar controller here but not the alazar or awg?
        self.alazar_controller = ATSChannelController(name='PWA_controller',
                                                      alazar_name='Alazar')
        self.alazar_channel = None

    # implementations
    def update_sequencer(self, sequencer):
        self.sequencer = sequencer
        station.components['sequencer'] = self.sequencer.serialize()  # see how this needs to be converted, to and from the json config
        seq = self.sequencer.create_sequence()


        # self.awg.upload(seq)
        # self.awg.start

    def setup_alazar(self, f_demod = None):
        # Magnitude, phase,I, Q?
        # need to be called when setting a new sequencer
        # set alazar in the right averaging mode
        if self.alazar_channel is not None:
            del self.alazar_channel
            # TODO: try to remove it from the channel list
            # self.alazar_controller.channels.remove(chan_m)
            # remove all channels
        # setup controller
        self.alazar_controller.int_time(self.sequencer.integration_time)
        self.alazar_controller.int_delay(self.sequencer.integration_delay)
        # setup channels
        chan_m = AlazarChannel(self.alazar_controller,
                             demod=f_demod is not None,
                             average_buffers = self.sequencer.average_buffers,
                             average_records = self.sequencer.average_records,
                             integrate_samples = self.sequencer.average_time)
        chan_m.demod_freq(f_demod)
        chan_m.num_averages(self.sequencer.n_averages)
        chan_m.prepare_channel() # sets setpoints and labels
        # this is a problem, can I not get magnitude and phase at the same time?
        chan_p = deepcopy(chan_m)
        chan_m.demod_type('magnitude')
        chan_p.demod_type('phase')
        # set the labels correctly here chan_m.data.setpoint_labels/units setpoints....
        # data is MultidimParameter
        self.alazar_controller.channels.append(chan_m)
        self.alazar_channel = chan_m

    def get(self):
        # must have called update_sequence before
        # trigger alazar


# def load_aquisition_parametes(metadata_from_station)->Dict:
#     pass

# implement shownums equivalent for acquisition parameters and sequencers

