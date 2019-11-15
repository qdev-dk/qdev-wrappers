from qdev_wrappers.fitting.base import Fitter, LeastSquaresFitter
from qdev_wrappers.fitting import guess
import numpy as np

# TODO: add 2D MinimumFitter (nataliejpg)
# TODO: add fitter for resonators (nataliejpg)


class MinimumFitter(Fitter):
    """
    Fitter instrument which finds the minimum of a 1d array and.
    """
    def __init__(self, name='MinimumFitter'):
        fit_parameters = {'location': {'label': 'location of minimum'},
                          'value': {'label': 'minimum value'}}
        function_metadata = {'str': 'find minimum (simple)'}
        super().__init__(name, fit_parameters,
                         method_description='SimpleMinimum',
                         function_description=function_metadata)

    def fit(self, measured_values, experiment_values):
        """
        Find minimum value and location, update fit_parameters and
        save succcess as yay.
        """
        self._check_fit(measured_values, experiment_values)
        min_index = np.argmin(measured_values)
        self.fit_parameters.location._save_val(experiment_values[min_index])
        self.fit_parameters.value._save_val(measured_values[min_index])
        self.success._save_val(1)


class ExpDecayFitter(LeastSquaresFitter):
    """
    Least Squares Fitter which fits to an exponential decay using the equation
        a * np.exp(-x / T) + c
    given the measured results and the values of x. Useful for T1 fitting.
    """
    def __init__(self, name='ExpDecayFitter'):
        fit_parameters = {'a': {'label': '$a$'},
                          'T': {'label': '$T$', 'unit': 's'},
                          'c': {'label': '$c$'}}
        function_metadata = {'str': r'$f(x) = a \exp(-x/T) + c$',
                             'np': 'a * np.exp(-x / T) + c'}
        super().__init__(name, fit_parameters, function_metadata)
        self.guess = guess.exp_decay


class ExpDecayBaseFitter(LeastSquaresFitter):
    """
    Least Squares Fitter which fits to an exponential using the equation
        a * p**x + b
    and given the measured results and the values of x. Useful for fitting
    benchmarking results.
    """
    def __init__(self, name='ExpDecayBaseFitter'):
        fit_parameters = {'a': {'label': '$a$', 'unit': 'V'},
                          'p': {'label': '$p$'},
                          'b': {'label': '$b$', 'unit': 'V'}}
        function_metadata = {'str': r'$f(x) = A p^x + B$',
                             'np': 'a * p**x + b'}
        super().__init__(name, fit_parameters, function_metadata)
        self.guess = guess.power_decay


class CosFitter(LeastSquaresFitter):
    """
    Least Squares Fitter which fits to a cosine using the equation
        a * np.cos(w * x + p) + c
    and given the measured results and the values of x. Useful for fitting
    Rabi oscillations.
    """
    def __init__(self, name='CosFitter'):
        fit_parameters = {'a': {'label': '$a$'},
                          'w': {'label': r'$\omega$', 'unit': 'Hz'},
                          'p': {'label': r'$\phi$'},
                          'c': {'label': '$c$', 'unit': ''}}
        function_metadata = {'str': r'$f(x) = a\cos(\omega x + \phi)+c$',
                             'np': 'a * np.cos(w * x + p) + c'}
        super().__init__(name, fit_parameters, function_metadata)
        self.guess = guess.cosine


class ExpDecaySinFitter(LeastSquaresFitter):
    """
    Least Squares Fitter which fits to an exponentially decaying sine using the
    equation
        a * np.exp(-x / T) * np.sin(w * x + p) + c
    and given the measured results and the values of x. Useful for fitting
    Ramsey oscillations to find T2*.
    """
    def __init__(self, name='ExpDecaySinFitter'):
        fit_parameters = {'a': {'label': '$a$', 'unit': ''},
                          'T': {'label': '$T$', 'unit': 's'},
                          'w': {'label': r'$\omega$', 'unit': 'Hz'},
                          'p': {'label': r'$\phi$'},
                          'c': {'label': '$c$'}}
        function_metadata = {
            'str': r'$f(x) = a \exp(-x / T) \sin(\omega x + \phi) + c$',
            'np': 'a * np.exp(-x / T) * np.sin(w * x + p) + c'}
        super().__init__(name, fit_parameters, function_metadata)
        self.guess = guess.exp_decay_sin
