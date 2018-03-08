class ParametricPulseBuilder:

    def build_pulse(parameters: Dict[]) -> bb.Element:
        pass

    def serialize(stream: )


class ParametricSequence:
"""
    Attributes:
         parameters (List[List[Dict]]): represents a sequence -> can become a strucutred array at some point
         set_points_x, set_points_y: represents the axis of the parameter 2D List.
         pulse_builder: function that takes the attributes to make some elements

"""
    def __init__(channel_base_name,
                 parameters: List[List[Dict]]=None,
                 pulse_builder: ParametricPulseBuilder,
                 set_points: Tuple[List[float], List[float]]=None):
        self.channel_base_name = channel_base_name
        self.parameters = parameters
        self.pulse_builder = pulse_builder

    def create_sequence(self) -> bb.Sequence:
        # sequence = broabbean magic with paramters
        # consider caching at later stage
        for list in self.parameters:
            for shot in list:
                sequence.append(self.pulse_builder(self.channel_base_name, shot))
        return sequence

    def serialize(self, stream):
        # load from metadata stored in station
        # needs fixed set of atomic puls builders
        pass

    def deserialize(self, stream):
        # prepare for storing in station
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


    def update_sequencer(self, sequencer: ParametricSequencer) -> None:
        """
        """
        # save the current sequencer from parameters
        self.sequencer = sequencer
        station.components['sequencer'] = self.sequencer.store()  # see how this needs to be converted, to and from the json config

    def set_up_acquisition(self, acquisition_parameters: Dict)
        # this should be simple, everything from the alazar is a parameter, so it gets stored
        self.acquisition_parameters = acquisition_parameters
        pass

    def run_experiment(self,
                       before_each_record,
                       after_each_record,
                       before_each_buffer,
                       after_each_buffer):
        pass
        # check if aqucisition mode agrees with actions


    # implementations
    def upload_sequence(self, sequencer=None):
        if sequencer is not None:
            self.update_sequencer(sequencer)
        seq = self.sequencer.create_sequence()
        # self.awg.upload(seq)

def load_aquisition_parametes(metadata_from_station)->Dict:
    pass

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
