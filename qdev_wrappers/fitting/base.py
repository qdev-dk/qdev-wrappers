import numpy as np
import warnings
from typing import List, Dict
from scipy.optimize import curve_fit
from qcodes.instrument.base import Instrument
from qcodes.instrument.channel import InstrumentChannel
from qcodes import validators as vals
from qcodes.instrument.parameter import Parameter

# TODO: docstrings
# TODO: remove r2 limit or make it a saveable parameter


class FitParameter(Parameter):
    def __str__(self):
        return self.name


class Fitter(Instrument):
    def __init__(self, name,
                 fit_parameters: Dict,
                 method=None,
                 function=None):
        super().__init__(name)
        fit_parameters_ch = InstrumentChannel(self, 'fit_parameters')
        self.add_submodule('fit_parameters', fit_parameters_ch)
        for paramname, paraminfo in fit_parameters.items():
            self.fit_parameters.add_parameter(name=paramname,
                                              set_cmd=False,
                                              parameter_class=FitParameter,
                                              **paraminfo)
        self.add_parameter(name='success',
                           set_cmd=False,
                           parameter_class=FitParameter,
                           vals=vals.Enum(0, 1))
        self.success._save_val(0)
        self.metadata = {'method': method,
                         'name': name,
                         'function': function,
                         'fit_parameters': list(self.fit_parameters.parameters.keys())}

    def fit(self, *args, **kwargs):
        raise NotImplementedError

    @property
    def all_parameters(self):
        params = []
        params += [p for n, p in self.parameters.items() if n != 'IDN']
        for s in self.submodules.values():
            params += list(s.parameters.values())
        return params

    def _check_fit(self, *args):
        for a in args[1:]:
            if a.shape != args[0].shape:
                raise RuntimeError(
                    f"experiment_parameter data does not have the same shape "
                    "as measured data.\nMeasured data shape: {args[0].shape},"
                    "experiment_parameter data shape: {a.shape}")


class LeastSquaresFitter(Fitter):
    def __init__(self, name, fit_parameters, function_metadata):
        super().__init__(name, fit_parameters, method='LeastSquares',
                         function=function_metadata)
        variance_parameters_ch = InstrumentChannel(
            self, 'variance_parameters')
        self.add_submodule('variance_parameters', variance_parameters_ch)
        for paramname, paraminfo in fit_parameters.items():
            self.variance_parameters.add_parameter(
                name=paramname + '_variance',
                label=paraminfo.get('label', paramname) + ' Variance',
                unit=paraminfo['unit'] + '^2' if 'unit' in paraminfo else None,
                set_cmd=False,
                parameter_class=FitParameter)
        initial_value_parameters_ch = InstrumentChannel(
            self, 'initial_value_parameters')
        self.add_submodule('initial_value_parameters',
                           initial_value_parameters_ch)
        for paramname, paraminfo in fit_parameters.items():
            self.initial_value_parameters.add_parameter(
                name=paramname + '_initial_value',
                label=paraminfo.get('label', paramname) + ' Initial Value',
                unit=paraminfo.get('unit', None),
                set_cmd=False,
                parameter_class=FitParameter)
        self.metadata.update(
            {'variance_parameters': list(self.variance_parameters.parameters.keys()),
             'initial_value_parameters': list(self.initial_value_parameters.parameters.keys())})

    def guess(self, *args):
        raise NotImplementedError('Optionally implemented in children')

    def evaluate(self, experiment_values, *fit_values):
        """
        Takes array,and the values of the fit_parameters for these values.
        Requires one parameter per experiment_parameters and one per
        fit_parameter and that they are entered experiment_values followed by
        fit_parameter values.
        """
        fit_params = list(self.fit_parameters.parameters.keys())
        if len(fit_values) == 0:
            fit_values = [v() for v in self.fit_parameters.parameters.values()]
        kwargs = {'x': experiment_values,
                  'np': np,
                  **dict(zip(fit_params, fit_values))}
        return eval(self.metadata['function']['np'], kwargs)

    def _get_r2(self, estimate, measured_values):
        """
        Finds residual and total sum of squares, calculates the R^2 value
        """
        meas = np.array(measured_values).flatten()
        est = np.array(estimate).flatten()
        ss_res = np.sum((meas - est) ** 2)
        ss_tot = np.sum((meas - np.mean(meas)) ** 2)
        r2 = 1 - (ss_res / ss_tot)
        return r2

    def fit(self, measured_values, experiment_values,
            initial_values=None, r2_limit=None, variance_limited=False):
        """
        Performs a fit based on the function_metadata.
        Returns a dictionary containing the model_values,
        the covariance matrix and the initial_values.
        """
        self._check_fit(measured_values, experiment_values)
        if initial_values is None:
            try:
                initial_values = self.guess(measured_values, experiment_values)
            except NotImplementedError:
                initial_values = [1. for _ in self.initial_value_parameters.parameters]
        for i, initial_param in enumerate(self.initial_value_parameters.parameters.values()):
                initial_param._save_val(initial_values[i])
        try:
            popt, pcov = curve_fit(
                self.evaluate, experiment_values, measured_values,
                p0=initial_values)
            variance = np.diag(pcov)
            estimate = self.evaluate(experiment_values, *popt)
            r2 = self._get_r2(estimate, measured_values)
            if r2_limit is not None and r2 < r2_limit:
                success = 0
                message = 'r2 {:.2} exceeds limit {:.2}'.format(r2, r2_limit)
            elif variance_limited and any(variance == np.inf):
                success = 0
                message = 'infinite variance'
            else:
                success = 1
        except (RuntimeError, ValueError) as e:
            success = 0
            message = str(e)
        self.success._save_val(success)
        fit_params = list(self.fit_parameters.parameters.values())
        variance_params = list(
            self.variance_parameters.parameters.values())
        initial_params = list(
            self.initial_value_parameters.parameters.values())
        if success:
            for i, val in enumerate(popt):
                fit_params[i]._save_val(val)
                if variance[i] == np.inf:
                    variance_params[i]._save_val(float('nan'))
                else:
                    variance_params[i]._save_val(variance[i])
        else:
            for i, param in enumerate(fit_params):
                param._save_val(float('nan'))
                variance_params[i]._save_val(float('nan'))
            warnings.warn('Fit failed due to: ' + message)

