from qcodes import Parameter, ManualParameter
from qdev_wrappers.transmon.math_functions import exp_decay_sin, exp_decay
from scipy.optimize import curve_fit
import numpy as np


class ReadoutFrequency(Parameter):
    def __init__(self, name, vna, detuning, extr='min'):
        super().__init__(name, unit='Hz')
        self._vna = vna
        self.detuning = detuning
        self.extr = extr

    def get_raw(self):
        S21_trace = self._vna.S21.trace
        mag_array = S21_trace.get_latest()
        
        if self.extr is 'max':
            idx = np.argmax(mag_array)
        elif self.extr is 'min':
            idx = np.argmin(mag_array)
        else:
            raise RuntimeError('extr mus be "max" or "min"')
        
        f = S21_trace.setpoints[0]
        freadout = f[idx] + self.detuning
        return freadout

class DriveFrequencyVNA(Parameter):
    def __init__(self, name, vna, extr='min', initial_val=5e9):
        super().__init__(name, unit='Hz')
        self._vna = vna
        self.extr = extr
        self._save_val(initial_val)

    def get_raw(self):
        SPEC_trace = self._vna.SPEC.trace
        mag_array = SPEC_trace.get_latest()
    
        if self.extr is 'max':
            idx = np.argmax(mag_array)
        elif self.extr is 'min':
            idx = np.argmin(mag_array)
        else:
            raise RuntimeError('extr mus be "max" or "min"')
        
        f = SPEC_trace.setpoints[0]
        fqubit = f[idx]
        return fqubit


class DriveFrequencyAlazar(Parameter):
    def __init__(self, name, alazar_ctrl, extr='min', initial_val=5e9):
        super().__init__(name, unit='Hz')
        self._alazar_ctrl = alazar_ctrl
        self.extr = extr
        self._save_val(initial_val)

    def get_raw(self):
        spec_trace = self._alazar_ctrl.acquisition
        mag_array = spec_trace.get_latest()[1][0]
    
        if self.extr is 'max':
            idx = np.argmax(mag_array)
        elif self.extr is 'min':
            idx = np.argmin(mag_array)
        else:
            raise RuntimeError('extr mus be "max" or "min"')
        
        f = spec_trace.setpoints[0][0]
        fqubit = f[idx]
        return fqubit


class PiPulseDur(Parameter):
    def __init__(self, name, alazar_ctrl, initial_fit_params=[0.003, 1e-7, 10e7, 0, 0.01]):
        super().__init__(name, unit='S')
        self._alazar_ctrl = alazar_ctrl
        self.initial_fit_params = initial_fit_params

    def get_raw(self):
        rabi_trace = self._alazar_ctrl.acquisition
        mag_array = rabi_trace.get_latest()[1][0]
        time = rabi_trace.setpoints[0][0]
        try:
            popt, pcov = curve_fit(exp_decay_sin, time, mag_array,
                                   p0=self.initial_fit_params)
            rabi_freq = popt[2]
            pi_pulse_dur = np.int(np.pi * 1e9 / rabi_freq) * 1e-9
            if  5e-9 < pi_pulse_dur < 100e-9:
                return pi_pulse_dur   
            else:
                raise RuntimeEroror
        except Exception:
            return 0

class T1(Parameter):
    def __init__(self, name, alazar_ctrl, error_limit=0.5, initial_fit_params=[0.05, 1e-6, 0.01]):
        super().__init__(name, unit='S')
        self._alazar_ctrl = alazar_ctrl
        self.initial_fit_params = initial_fit_params
        self.error_limit = error_limit

    def get_raw(self):
        t1_trace = self._alazar_ctrl.acquisition
        mag_array = t1_trace.get_latest()[1][0]
        time = t1_trace.setpoints[0][0]
        try:
            popt, pcov = curve_fit(exp_decay, time, mag_array,
                                   p0=self.initial_fit_params)
            t1_err = np.sqrt(pcov[1, 1])
            t1 = popt[1]
            if t1_err < self.error_limit * t1:
                return t1   
            else:
                return 0
        except Exception:
            return 0

class T2(Parameter):
    def __init__(self, name, alazar_ctrl, error_limit=0.5, initial_fit_params=[0.003, 1e-7, 10e7, 0, 0.01]):
        super().__init__(name, unit='S')
        self._alazar_ctrl = alazar_ctrl
        self.initial_fit_params = initial_fit_params
        self.error_limit = error_limit

    def get_raw(self):
        t2_trace = self._alazar_ctrl.acquisition
        mag_array = t2_trace.get_latest()[1][0]
        time = t2_trace.setpoints[0][0]
        try:
            popt, pcov = curve_fit(exp_decay_sin, time, mag_array,
                                   p0=self.initial_fit_params)
            t2_err = np.sqrt(pcov[1, 1])
            t2 = popt[1]
            if t2_err < self.error_limit * t2:
                return t2   
            else:
                return 0
        except Exception:
            return 0
