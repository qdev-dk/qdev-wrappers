from typing import Callable

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
                 buffer_set_points:List[float] = None):
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
        return "Not yet implemented"

    def deserialize(self, str) -> None:
        pass


class ParametricWaveformAnalysator:
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


    # implementations
    def update_sequencer(self, sequencer):
        self.sequencer = sequencer
        station.components['sequencer'] = self.sequencer.serialize()  # see how this needs to be converted, to and from the json config
        seq = self.sequencer.create_sequence()
        # set alazar in the right averaging mode
        # self.awg.upload(seq)
        # self.awg.start


    def get(self):
        # must have called update_sequence before
        # trigger alazar


# def load_aquisition_parametes(metadata_from_station)->Dict:
#     pass

# implement shownums equivalent for acquisition parameters and sequencers


# application examples:
# 1. Cavity resonance

# load some channel mapping, instantiat instruments

npoints=100
parameters = [[{'readout_delay': 1,
              'readout_duration': 1,
              'readout_amplitude': 1,
              'readout_marker_delay': 1,
              'readout_marker_duration': 1,
              'readout_stage_duration': 1,
              'drive_stage_duration': 1}]*npoints]

sequencer = ParametricSequencer(channel_base_name = 'qubit1_cavity',
                      parameters=parameters,
                      pulse_builder=create_pulse)
exp = ParametricWaveformAnalysator()
