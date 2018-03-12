import qcodes as qc
from somewhere_else import make_parametric_sequence
from qdev_wrappers.customised_instruments import ParametricSequencer, \
    ParametricWaveformAnalysator
from qdev_wrappers.customised_instruments.AWG5014_ext import AWG5014_ext
from qdev_wrappers.customised_instruments.AlazarTech_ATS9360_ext import AlazarTech_ATS9360_ext
from qdev_wrappers.alazar_controllers.ATSChannelController import ATSChannelController

station = qc.Station()
awg = AWG5014_ext('awg', 'address')
alazar = AlazarTech_ATS9360_ext('alazar')
acq_ctrl = ATSChannelController('alazar_controller', 'alazar')

pulse_parameters = [[{'readout_delay': 1,
                      'readout_duration': 1,
                      'readout_amplitude': 1,
                      'readout_marker_delay': 1,
                      'readout_marker_duration': 1,
                      'readout_stage_duration': 1,
                      'drive_stage_duration': 1}]]


sequencer = ParametricSequencer(parameters=pulse_parameters,
                                pulse_builder=make_parametric_sequence,
                                sequencing_mode=False,
                                n_averages=1000)

pwa = ParametricWaveformAnalysator(station, awg, alazar, acq_ctrl)

pwa.update_sequencer(sequencer)
pwa.setup_alazar(f_demod=15e6)

qc.Measure(pwa.alazar_channels.data).run()
