from qcodes import Instrument
from qcodes import ManualParameter
from qcodes import Parameter
from qcodes.utils import validators as vals
from qdev_wrappers.transmon.math import exp_decay_sin
from scipy.optimize import curve_fit
import numpy as np

class QubitDerivedParam(Parameter):
    def __init__(self, name, instrument, update_fn,
                 default_value=None):
        super().__init__(name)
        self._instrument = instrument
        self._save_val(default_value)
        self._update_fn = update_fn
        # self.up_to_date = False

    def set_raw(self, value):
        raise NotImplementedError("Cannot directly set {}".format(self.name))

    def get_raw(self):
    	# if not self.up_to_date:
    	# 	raise RuntimeError('Cannot get value as instr')
        return self._latest['value']

    def update(self):
        val = self._update_fn()
        # self.up_to_date = True
        self._save_val(val)


class QubitCalculatedParam(Parameter)
    def __init__(self, name, instrument, calculate_fn,
                 default_value=None):
        super().__init__(name)
        self._instrument = instrument
        self._save_val(default_value)
        self._update_fn = update_fn
        # self.up_to_date = False

    def calculate(self):
        val = self.calculate_fn()
        self._save_val(val)

    def get_raw(self):
        return self._latest['value']


# class Sample(Instrument):
# 	def __init__(self, name):
# 		int_time = 5e-7
# 		int_delay = 1e-6
# 		localos_pow = 15
# 		cycle_time = 20e-6
# 		pulse_end = 10e-6
# 		pulse_mod_time = 1.5e-6
# 		pulse_readout_delay = 30e-9
# 		readout_amp = 1
# 		readout_time = 4e-6
# 		sample_rate = 1e9	


class Qubit(Instrument):
	def __init__(self, name, spec_acq_ctrl, rabi_acq_ctrl, t1_acq_ctrl, vna, qubit_source):

		drag_coef = 0.5
		marker_readout_delay = 0
		marker_time = 500e-9
		pi_half_pulse_amp = 0.5
		pi_pulse_amp = 1
		pi_pulse_sigma = None
		qubit_spec_time = 1e-6
		sigma_cutoff = 4
		z_half_pulse_amp = None
		z_pulse_amp = None
		z_pulse_dur = None

		# parameters derived from vna
        self.add_parameter(name='readout_power',
        				   parameter_class=QubitCalibrationParam,
        				   update_fn=self._vna.SPEC.readout_power)

        self.add_parameter(name='readout_frequency',
        				   parameter_class=QubitCalibrationParam,
        				   update_fn=self._vna.SPEC.readout_frequency)

        # parameters derived from alazar setup 
        self.add_parameter(name='gate_drive_power',
        				   parameter_class=QubitCalibrationParam,
        				   update_fn=self._qubit_source.power)

        self.add_parameter(name='pi_pulse_duration',
        				   get_cmd=self._get_pi_pulse_dur,
        				   set_cmd=None,
        				   parameter_class=ManualParameter)

        for instr in ['vna', 'alazar']:
	        self.add_parameter(name='spectroscopy_drive_power_{}'.format(instr),
	        				   parameter_class=ManualParameter,
	        				   get_cmd=partial(self._get_spectroscopy_drive_power, instr),
	        				   set_cmd=None)

	        self.add_parameter(name='drive_frequency',
	        				   parameter_class=ManualParameter,
	        				   get_cmd=partial(self._get_spectroscopy_drive_frequency, instr),
	        				   set_cmd=None)



        self.add_parameter(name='t1',
        				   get_cmd=self._get_t1,
        				   set_cmd=None,
        				   parameter_class=ManualParameter)


        self._t1_acq_ctrl = t1_acq_ctrl

        self._rabi_acq_ctrl = rabi_acq_ctrl

        self._spec_acq_ctrl = spec_acq_ctrl

        self._vna = vna

        self._qubit_source = qubit_source

        # self._ave_ctrl = ave_ctrl

    def _get_pi_pulse_dur(self):
    	rabi_trace = self._rabi_acq_ctrl.acquisition
    	mag_array = rabi_trace.get_latest()[1][0]
    	time = rabi_trace.setpoints[0][0]
        popt, pcov = curve_fit(exp_decay_sin, time, mag_array,
                               p0=initial_fit_params)
        rabi_freq = popt[2]
        pi_pulse_dur = np.int(np.pi * 1e9 / rabi_freq) * 1e-9
        if  5e-9 < pi_pulse_dur < 100e-9:                      
        	return pi_pulse_dur
        else:
            raise RuntimeError('rabi_acq_ctrl does not yeild reasonable pi pulse dur result')

    def _get_t1(self):
    	rabi_trace = self._rabi_acq_ctrl.acquisition
    	mag_array = rabi_trace.get_latest()[1][0]
    	time = rabi_trace.setpoints[0][0]
        popt, pcov = curve_fit(exp_decay_sin, time, mag_array,
                               p0=initial_fit_params)
        rabi_freq = popt[2]
        pi_pulse_dur = np.int(np.pi * 1e9 / rabi_freq) * 1e-9
        if  5e-9 < pi_pulse_dur < 100e-9:                      
        	return pi_pulse_dur
        else:
            raise RuntimeError('rabi_acq_ctrl does not yeild reasonable pi pulse dur result')

    def _get_drive_frequency(self):
    	if self.drive_calibration_instr() == 'VNA':
    		SPEC_trace = vna.SPEC.trace
    		mag_array = SPEC_trace.get_latest()	    
		    if extremum is 'max':
		        idx = np.argmax(mag_array)
		    elif extremum is 'min':
		        idx = np.argmin(mag_array)	    
		    f = SPEC_trace.setpoints[0]
		    fqubit = f[idx]
		    return fqubit
		elif self.drive_calibration:

    def _get_drive_frequency_alazar(self):
    	rabi_trace = self._rabi_acq_ctrl.acquisition
    	mag_array = rabi_trace.get_latest()[1][0]
    	time = rabi_trace.setpoints[0][0]
        popt, pcov = curve_fit(exp_decay_sin, time, mag_array,
                               p0=initial_fit_params)
        rabi_freq = popt[2]
        pi_pulse_dur = np.int(np.pi * 1e9 / rabi_freq) * 1e-9
        if  5e-9 < pi_pulse_dur < 100e-9:                      
        	return pi_pulse_dur
        else:
            raise RuntimeError('rabi_acq_ctrl does not yeild reasonable pi pulse dur result')

    def _get_drive_frequency_vna(self):


    def _galibrate_readout_vna(self):
    	pass