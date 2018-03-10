from somewhere_else import make_readout_sequence
from qdev_wrappers.customised_instruments import ParametricSequencer, \
    ParametricWaveformAnalysator

parameters = [{'readout_delay': 1,
               'readout_duration': 1,
               'readout_amplitude': 1,
               'readout_marker_delay': 1,
               'readout_marker_duration': 1,
               'readout_stage_duration': 1,
               'drive_stage_duration': 1}]


sequencer = ParametricSequencer(parameters=parameters,
                                pulse_builder=make_readout_sequence,
                                sequencing_mode=False,
                                n_averages=1000)

exp = ParametricWaveformAnalysator()
