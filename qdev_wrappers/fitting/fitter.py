import numpy as np
from typing import List, Dict
from qdev_wrappers.fitting import guess
from scipy.optimize import curve_fit
from qcodes.instrument.base import Instrument
from qcodes.instrument.channel import InstrumentChannel
from qcodes import validators as vals

# TODO: docstrings


class Fitter(Instrument):
    def __init__(self, name,
                 experiment_parameters: List,
                 fit_parameters: Dict,
                 metadata: Dict=None):
        super().__init__(name)
        fit_parameters_ch = InstrumentChannel(self, 'fit_parameters')
        self.add_submodule('fit_parameters', fit_parameters_ch)
        for paramname, paraminfo in fit_parameters.items():
            self.fit_parameters.add_parameter(name=paramname,
                                              set_cmd=False,
                                              **paraminfo)
        self.add_parameter(name='success',
                           set_cmd=False,
                           vals=vals.Enum(0, 1))
        self.success._save_val(0)
        self.experiment_parameters = experiment_parameters
        self.metadata = {'method': None,
                         'name': name,
                         'function': None,
                         'fit_parameters': list(self.fit_parameters.parameters.keys())}
        if metadata is not None:
            self.metadata.update(metadata)

    def fit(self, *args, **kwargs):
        raise NotImplementedError

    def _check_fit(self, *args):
        if len(args) - 1 != len(self.experiment_parameters):
            raise RuntimeError(
                f"Unexpected number of experiment parameters provided.\n"
                 "Expected: {len(self.experiment_parameters.parameters)},"
                 " Received  {len(args)}")
        for a in args[1:]:
            if a.shape != args[0].shape:
                raise RuntimeError(
                    f"experiment_parameter data does not have the same shape "
                    "as measured data.\nMeasured data shape: {args[0].shape},"
                    "experiment_parameter data shape: {a.shape}")


class SimpleMinimumFitter(Fitter):
    def __init__(self):
        experiment_parameters = ['x']
        fit_parameters = {'location': {'label': 'location of minimum'},
                          'value': {'label': 'minimum value'}}
        metadata = {'method': 'simple_minimum',
                    'function': {'str': 'find minimum (simple)'}}
        super().__init__(experiment_parameters, fit_parameters, metadata)

    def fit(self, measured_values, experiment_values):
        self._check_fit(measured_values, experiment_values)
        min_index = np.argmin(measured_values)
        self.location._save_val(experiment_values[min_index])
        self.value._save_val(measured_values[min_index])


class LeastSquaresFitter(Fitter):
    def __init__(self, name, fit_parameters, function_metadata):
        experiment_parameters = ['x']
        super().__init__(name, experiment_parameters, fit_parameters)
        variance_parameters_ch = InstrumentChannel(
            self, 'variance_parameters')
        self.add_submodule('variance_parameters', variance_parameters_ch)
        for paramname, paraminfo in fit_parameters.items():
            self.variance_parameters.add_parameter(
                name=paramname + '_variance',
                label=paraminfo.get('label', paramname) + ' Variance',
                unit=paraminfo['unit'] + '^2' if 'unit' in paraminfo else None,
                set_cmd=False)
        initial_value_parameters_ch = InstrumentChannel(
            self, 'initial_value_parameters')
        self.add_submodule('initial_value_parameters',
                           initial_value_parameters_ch)
        for paramname, paraminfo in fit_parameters.items():
            self.initial_value_parameters.add_parameter(
                name=paramname + '_initial_value',
                label=paraminfo.get('label', paramname) + ' Initial Value',
                unit=paraminfo.get('unit', None),
                set_cmd=False)
        self.metadata.update(
            {'method': 'LeastSquares',
             'function': function_metadata,
             'variance_parameters': list(self.variance_parameters.parameters.keys()),
             'initial_value_parameters': list(self.initial_value_parameters.parameters.keys())})

    def guess(self, *args):
        raise NotImplementedError(
            'Implemented in children or initial_values specified.')

    def evaluate(self, experiment_values, *fit_values):
        """
        Takes array,and the values of the fit_parameters for these values.
        Requires one parameter per experiment_parameters and one per
        fit_parameter and that they are entered experiment_values followed by
        fit_parameter values.
        """
        fit_params = list(self.fit_parameters.parameters.keys())
        if len(fit_values) == 0:
            fit_values = [v() for v in self.fit_parameters.values()]
        kwargs = {self.experiment_parameters[0]: experiment_values,
                  **dict(zip(fit_params, fit_values))}
        return eval(self.metadata['function']['np'], kwargs)

    def _get_r2(self, estimate, measured_values):
        """
        Finds residual and total sum of squares, calculates the R^2 value
        """
        ss_res = np.sum((data - estimate) ** 2)
        ss_tot = np.sum((data - np.mean(data)) ** 2)
        r2 = 1 - (ss_res / ss_tot)
        return r2

    def fit(self, measured_values, experiment_values,
            initial_values=None, r2_limit=None):
        """
        Performs a fit based on the function_metadata.
        Returns a dictionary containing the model_values,
        the covariance matrix and the initial_values.
        """
        self._check_fit(measured_values, experiment_values)
        if initial_values is None:
            initial_values = self.guess(measured_values, experiment_values)
        for i, param in enumerate(self.initial_value_parameters.values()):
            param._save_val(initial_values[i])
        try:
            popt, pcov = curve_fit(
                self.evaluate, measured_values, experiment_values,
                p0=initial_values)
            variance = np.diag(pcov)
            estimate = self.evaluate(experiment_values, *popt)
            r2 = self._get_r2(estimate, measured_values)
            if r2_limit is not None and r2 > r2_limit:
                success = 0
                message = 'r2 {:.2} exceeds limit {:.2}'.format(r2, r2_limit)
            else:
                success = 1
        except (RuntimeError, ValueError) as e:
            success = 0
            message = e
        self.success._save_val(success)
        if success:
            fit_params = list(self.fit_parameters.parameters.values())
            variance_params = list(
                self.variance_parameters.parameters.values())
            initial_params = list(
                self.initial_value_parameters.parameters.values())
            for i, val in enumerate(popt):
                fit_params[i]._save_val(val)
                variance_params[i]._save_val(variance[i])
                initial_params[i]._save_val(initial_values[i])
        else:
            warning.warn('Fit failed due to: ', message)


class T1Fitter(LeastSquaresFitter):
    def __init__(self):
        fit_parameters = {'a': {'label': '$a$'},
                          'T': {'label': '$T$', 'unit': 's'},
                          'c': {'label': '$c$'}}
        function_metadata = {'str': r'$f(x) = a \exp(-x/T) + c$',
                             'np': 'a*np.exp(-x/T)+c'}
        super().__init__('T1Fitter', fit_parameters, function_metadata)
        self.guess = guess.exp_decay


class BenchmarkingFitter(LeastSquaresFitter):
    def __init__(self):
        fit_parameters = {'a': {'label': '$a$', 'unit': 'V'},
                          'p': {'label': '$p$'},
                          'b': {'label': '$b$', 'unit': 'V'}}
        function_metadata = {'str': r'$f(x) = A p^x + B$',
                             'np': 'a * p**x + b'}
        super().__init__('BenchmarkingFitter', fit_parameters, function_metadata)
        self.guess = guess.power_decay


class CosineFitter(LeastSquaresFitter):
    def __init__(self):
        fit_parameters = {'a': {'label': '$a$'},
                          'w': {'label': r'$\omega$', 'unit': 'Hz'},
                          'p': {'label': r'$\phi$'},
                          'b': {'label': '$c$', 'unit': ''}}
        function_metadata = {'str': r'$f(x) = a\cos(\omega x + \phi)+b$',
                             'np': 'a * np.cos(w * x + p) + b'}
        super().__init__('CosineFitter', fit_parameters, function_metadata)
        self.guess = guess.cosine


class DecayingRabisFitter(LeastSquaresFitter):
    def __init__(self):
        fit_parameters = {'a': {'label': '$a$', 'unit': ''},
                          'T': {'label': '$T$', 'unit': 's'},
                          'w': {'label': r'$\omega$', 'unit': 'Hz'},
                          'p': {'label': r'$\phi$'},
                          'c': {'label': '$c$'}}
        function_metadata = {
            'str': r'$f(x) = a \exp(-x / T) \sin(\omega x + \phi) + c$',
            'np': 'a * np.exp(-x / T)*np.sin(w * x + p) + c'}
        super().__init__('DecayingRabisFitter', fit_parameters, function_metadata)
        self.guess = guess.exp_decay_sin
