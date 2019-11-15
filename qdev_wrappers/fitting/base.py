import numpy as np
import warnings
from scipy.optimize import curve_fit
from qcodes.instrument.base import Instrument
from qcodes.instrument.channel import InstrumentChannel
from qcodes import validators as vals
from qcodes.instrument.parameter import Parameter

# TODO: remove r2 limit or make it a saveable parameter (nataliejpg)
# TODO: add fitter for >1 independent and dependent variable (nataliejpg)


class FitParameter(Parameter):
    """
    Parameter to be used in the fitter which is represented by its name rather
    than its full name as this facilitates it being used both before and after
    saving in the same way (especially useful when evaluating functions stored
    as strings as in the LeastSquaredFitter where the parameter names are
    important)
    """

    def __str__(self):
        return self.name


class Fitter(Instrument):
    """
    Instrument which can perform fits on data and has parameters to store the
    fit parameter values. Can be used with the fit_by_id and saved datasets
    generated can be plotted using plot_fit_by_id helpers.

    Args:
        name (str)
        fit_parameters (dict): dictionary describing the parameters generated
            in the fitting procedure. Keys are used as parameter names and
            values are a dict with at keys 'unit' and/or 'label'
        method_description (str) (optional): identifier for fitting method
        function_description (dict) (optional): dictionary with more detail
            about the function. Keys should include 'str'
    """

    def __init__(self, name,
                 fit_parameters,
                 method_description=None,
                 function_description=None):
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
        self.metadata = {
            'method': method_description,
            'name': name,
            'function': function_description,
            'fit_parameters': list(self.fit_parameters.parameters.keys())}

    @property
    def all_parameters(self):
        """
        Gathers all parameters on instrument and on it's submodules
        and returns them in a list.
        """
        params = []
        params += [p for n, p in self.parameters.items() if n != 'IDN']
        for s in self.submodules.values():
            params += list(s.parameters.values())
        return params

    def fit(self, *args, **kwargs):
        """
        Function which is expected to take data and any other information,
        perform the fit and (minimally) update the fit_parameters and success
        parameter
        """
        raise NotImplementedError(
            'Fit function must be implemented in Children')

    def _check_fit(self, *args):
        """
        Checks shape of arguments provided to check for consistancy.
        """
        for a in args[1:]:
            if a.shape != args[0].shape:
                raise RuntimeError(
                    f"experiment_parameter data does not have the same shape "
                    f"as measured data.\nMeasured data shape: {args[0].shape},"
                    f"experiment_parameter data shape: {a.shape}")


class LeastSquaresFitter(Fitter):
    """
    An extension of the Fitter which uses the least squares method to fit
    an array of data to a function and learn the most likely parameters of
    this function and the variance on this knowledge. Also stored the initial
    guesses used.

    Args:
        name (str)
        fit_parameters (dict): dictionary describing the parameters in the
            function which is being fit to, keys are taken as parameter names
            as they appear in the function, values are dictionary with keys
            'unit' and 'label' to be used in plotting.
        function_metadata (dict): description of the function to be fit to
            including the exact code to be evaluated (key 'np') and the
            label to be printed (key 'str')
    """

    def __init__(self, name, fit_parameters, function_metadata):
        super().__init__(name, fit_parameters,
                         method_description='LeastSquares',
                         function_description=function_metadata)
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
            {'variance_parameters': list(
                self.variance_parameters.parameters.keys()),
             'initial_value_parameters': list(
                self.initial_value_parameters.parameters.keys())})

    def guess(self, measured_values, experiment_values):
        """
        Function to generate initial values of the parameters for fitting,
        if not implemented in children then values must be provided
        at time of fitting.
        """
        raise NotImplementedError('Optionally implemented in children')

    def evaluate(self, experiment_values, *fit_values):
        """
        Evaluates the function to be fit to (stored in the metadata) for
        the values of the independent variable (experiment value) and the
        fit parameters provided.
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
        Performs a fit based on a measurement and using the evaluate function.
        Updates the instrument parameters to record the success and results
        of the fit.
        """
        self._check_fit(measured_values, experiment_values)
        if initial_values is None:
            try:
                initial_values = self.guess(measured_values, experiment_values)
            except NotImplementedError:
                initial_values = [
                    1. for _ in self.initial_value_parameters.parameters]
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
