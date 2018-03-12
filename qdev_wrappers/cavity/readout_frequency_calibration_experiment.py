import qcodes as qc
from somewhere_else import make_parametric_sequence
from qdev_wrappers.customised_instruments import ParametricSequencer, \
    ParametricWaveformAnalysator
from qdev_wrappers.customised_instruments.AWG5014_ext import AWG5014_ext
from qdev_wrappers.customised_instruments.AlazarTech_ATS9360_ext import AlazarTech_ATS9360_ext
from qdev_wrappers.alazar_controllers.ATSChannelController import ATSChannelController
from qcodes.instrument_drivers.rohde_schwarz.SGS100A import RohdeSchwarz_SGS100A
from qdev_wrappers.cavity.lock_in import LockIn

station = qc.Station()
awg = AWG5014_ext('awg', 'address')
alazar = AlazarTech_ATS9360_ext('alazar')
acq_ctrl = ATSChannelController('alazar_controller', 'alazar')
cavity = RohdeSchwarz_SGS100A('cavity', 'address')
localos = RohdeSchwarz_SGS100A('localos', 'address')


pulse_parameters = [[{'readout_delay': 1,
                      'readout_duration': 1,
                      'readout_amplitude': 1,
                      'readout_marker_delay': 1,
                      'readout_marker_duration': 1,
                      'readout_stage_duration': 1,
                      'drive_stage_duration': 1}]]

readout_parameters = {'int_delay': 0.5e-6,
                      'int_time': 1e-6}


sequencer = ParametricSequencer(
    parameters=pulse_parameters,
    pulse_builder=make_parametric_sequence,
    sequencing_mode=False,
    n_averages=1000,
    integration_delay=readout_parameters['int_delay'],
    integration_time=readout_parameters['int_time'])

pwa = ParametricWaveformAnalysator(station, awg, alazar, acq_ctrl)

lockin = LockIn(cavity, localos, pwa, demodulation_frequency=15e6)
lockin.on()

pwa.update_sequencer(sequencer)
pwa.setup_alazar()

qc.Loop(lockin.frequency.sweep(7e9, 7.1e9, 1e6)).each(
    pwa.alazar_channels.data).run()
