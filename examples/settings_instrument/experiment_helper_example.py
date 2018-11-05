from qdev_wrappers.fitting.LeastScaresFit import Cosine
from qdev_wrappers.customised_instruments.experiment_helper import ExperimentHelper

rabi_measurement = ExperimentHelper(settings_instrument, 'rabi',
								    pwa=pwa, fitclass=Cosine)


#%%

rabi_measurement.measure(exp.drive.carrier_frequency,
                         exp.drive.carrier_frequency() - 10e6,
                         exp.drive.carrier_frequency() + 10e6,
                         21, 0,
                         exp.readout.Q0.data)

fit_results = rabi_measurement.fit()

pi_pulse_dur = np.pi / fit_results[0]['param_values']['w']

exp.drive.gate_pulse_duration(pi_pulse_dur)
