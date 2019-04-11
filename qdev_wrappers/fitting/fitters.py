from qdev_wrappers.fitting.base import Fitter, LeastSquaresFitter
from qdev_wrappers.fitting import guess
import numpy as np


class SimpleMinimumFitter(Fitter):
    def __init__(self, name='SimpleMinimumFitter'):
        fit_parameters = {'location': {'label': 'location of minimum'},
                          'value': {'label': 'minimum value'}}
        function_metadata = {'str': 'find minimum (simple)'}
        super().__init__(name, fit_parameters, method='SimpleMinimum',
                         function=function_metadata)

    def fit(self, measured_values, experiment_values):
        self._check_fit(measured_values, experiment_values)
        min_index = np.argmin(measured_values)
        self.fit_parameters.location._save_val(experiment_values[min_index])
        self.fit_parameters.value._save_val(measured_values[min_index])
        self.success._save_val(1)


class T1Fitter(LeastSquaresFitter):
    def __init__(self, name='T1Fitter'):
        fit_parameters = {'a': {'label': '$a$'},
                          'T': {'label': '$T$', 'unit': 's'},
                          'c': {'label': '$c$'}}
        function_metadata = {'str': r'$f(x) = a \exp(-x/T) + c$',
                             'np': 'a*np.exp(-x/T)+c'}
        super().__init__(name, fit_parameters, function_metadata)
        self.guess = guess.exp_decay


class BenchmarkingFitter(LeastSquaresFitter):
    def __init__(self, name='BenchmarkingFitter'):
        fit_parameters = {'a': {'label': '$a$', 'unit': 'V'},
                          'p': {'label': '$p$'},
                          'b': {'label': '$b$', 'unit': 'V'}}
        function_metadata = {'str': r'$f(x) = A p^x + B$',
                             'np': 'a * p**x + b'}
        super().__init__(name, fit_parameters, function_metadata)
        self.guess = guess.power_decay


class CosineFitter(LeastSquaresFitter):
    def __init__(self, name='CosineFitter'):
        fit_parameters = {'a': {'label': '$a$'},
                          'w': {'label': r'$\omega$', 'unit': 'Hz'},
                          'p': {'label': r'$\phi$'},
                          'c': {'label': '$c$', 'unit': ''}}
        function_metadata = {'str': r'$f(x) = a\cos(\omega x + \phi)+c$',
                             'np': 'a * np.cos(w * x + p) + c'}
        super().__init__(name, fit_parameters, function_metadata)
        self.guess = guess.cosine


class DecayingRabisFitter(LeastSquaresFitter):
    def __init__(self, name='DecayingRabisFitter'):
        fit_parameters = {'a': {'label': '$a$', 'unit': ''},
                          'T': {'label': '$T$', 'unit': 's'},
                          'w': {'label': r'$\omega$', 'unit': 'Hz'},
                          'p': {'label': r'$\phi$'},
                          'c': {'label': '$c$'}}
        function_metadata = {
            'str': r'$f(x) = a \exp(-x / T) \sin(\omega x + \phi) + c$',
            'np': 'a * np.exp(-x / T)*np.sin(w * x + p) + c'}
        super().__init__(name, fit_parameters, function_metadata)
        self.guess = guess.exp_decay_sin