from somewhere_else import make_readout_sequence
from qdev_wrappers.customised_instruments import ParametricSequencer, \
    ParametricWaveformAnalysator

pulse_parameters = [{'readout_delay': 1,
                     'readout_duration': 1,
                     'readout_amplitude': 1,
                     'readout_marker_delay': 1,
                     'readout_marker_duration': 1,
                     'readout_stage_duration': 1,
                     'drive_stage_duration': 1}]

readout_parameters = {'int_delay': 0.5e-6,
                      'int_time': 1e-6}

sequencer = ParametricSequencer(
    parameters=pulse_parameters,
    pulse_builder=make_readout_sequence,
    integration_delay=readout_parameters['int_delay'],
    integration_time=readout_parameters['int_time'],
)

exp = ParametricWaveformAnalysator()
