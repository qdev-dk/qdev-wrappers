import qcodes as qc
import numpy as np
from itertools import product
import warnings
# warnings.simplefilter("always")
from qdev_wrappers.fitting.analysis import Analysis


class Fitter:
    """
    Args:
        'model'
        'guess' : Optional, and unnecessary if the model contains a suitable default guess.
        'r2_limit' : Optional, used to reject very bad fits. Useful but questionable.
    """

    def __init__(self, model, guess=None, r2_limit=None):
        self.model = model
        if guess is not None:
            self.model.guess = guess

        self.r2_limit = r2_limit

    def fit_by_id(self, run_id, dept_var: str, save_fit=True, **other_function_variables):

        analysis = Analysis(run_id, dept_var, self.model, **other_function_variables)
        analysis.metadata = self.model.summary
        if self.r2_limit is not None:
            analysis.metadata['r2_limit'] = self.r2_limit

        fit = self._do_fitting_procedure(analysis)
        if save_fit:
            fit.save()

        return fit

    def _do_fitting_procedure(self, analysis):
        """
        Populates fit_results list with one dictionary per combination
        of setpoints.

        eg setpoints = {'frequency':
                                {'label': '',
                                 'unit': 'Hz',
                                 'data': [1e9, 2e9, 3e9]},
                        'power':
                                {'label': '',
                                 'unit': 'dBm',
                                 'data': [-10, -30]}}

        will make 6 dictionaries of the form
        {
            'setpoint_values': {'frequency': 1e9 , 'power': -10},
            'start_values': {'a': 3, 'b': 10},
            'param_values': {'a': 2.5, 'b': 11},
            'variance': {'a': 0.1, 'b': 2},
        }
        """
        fit_results = []
        setpoints = analysis.setpoints
        full_function_variable_arrays = {var: data_dict['data'] for var, data_dict in analysis.function_vars.items()}
        full_output_data_array = analysis.dept_var['data']

        # input_data_array = indept_var['data']

        # if setpoints then perform fit for all
        if len(setpoints) > 0:
            # find all possible combinations of setpoint values
            setpoint_combinations = product(
                *[set(v['data']) for v in setpoints.values()])
            setpoint_names = list(setpoints.keys())
            for setpoint_combination in setpoint_combinations:
                # find indices where where setpoint combination is satisfied
                indices = set(np.argwhere(
                    setpoints[setpoint_names[0]]['data'] == setpoint_combination[0]).flatten())
                for i in range(1, len(setpoint_names)):
                    new_indices = np.argwhere(
                            setpoints[setpoint_names[0]]['data'] == setpoint_combination[0]).flatten()
                    indices = indices.intesection(new_indices)
                indices = list(indices)
                output_data_array = full_output_data_array[indices]
                function_variable_arrays = {}
                for var, data in full_function_variable_arrays.items():
                    function_variable_arrays[var] = data[indices]
                param_values, param_dict = self.fit(output_data_array, **function_variable_arrays)
                result = param_dict.copy()
                result.update({'setpoints': dict(zip(setpoint_names, setpoint_combination))})
                fit_results.append(result)
#                except Exception:  # TODO: what kind of exception
#                    print('no data for setpoint combination ', dict(
#                        zip(self.setpoints.keys(), setpoint_combination)))
        else:
            function_variable_arrays = full_function_variable_arrays
            output_data_array = full_output_data_array
            param_values, param_dict = self.fit(output_data_array, **function_variable_arrays)
            fit_results.append(param_dict)

        analysis.fit_results = fit_results
        return analysis

    def fit(self, output_data_array, **function_variable_arrays):

        param_values = {parameter: None for parameter in self.model.parameters.keys()}
        fit_info = None

        try:
            # Do fit, using fit_procedure from model
            popt, fit_info = self.model.fit_procedure(output_data_array, **function_variable_arrays)
            # Store parameter values
            for i, param_name in enumerate(self.model.parameters.keys()):
                param_values[param_name] = popt[i]
        except RuntimeError:
            warnings.warn('Unsuccessful fit - did not find optimal parameters')
            param_values = None

        params_dict = {'param_values': param_values,
                       'fit_info': fit_info}

        # r2 test to approve fit
        if self.r2_limit is not None and param_values is not None:
            est_data = self._find_estimate(params_dict['param_values'], **function_variable_arrays)
            r2 = self._get_r2(est_data, output_data_array)
            if r2 < self.r2_limit:
                params_dict['param_values'] = None
                params_dict['fit_info'] = None
                param_values = None
                warnings.warn(f'Unsuccessful fit - r2 for fit is below limit {self.r2_limit}')

        # Organize fit info (fx. variance, inital guess, etc). Organization is defined in the model
        params_dict = self.model.organize_fit_info(params_dict)

        return param_values, params_dict

    def _find_estimate(self, param_values_dict, **function_variable_arrays):
        variable_args = [value for value in function_variable_arrays.values()]
        param_args = [value for value in param_values_dict.values()]
        return self.model.evaluate(*variable_args, *param_args)

    def _get_r2(self, estimate, data):
        """
        Finds residual and total sum of squares, calculates the R^2 value
        """
        ss_res = np.sum((data - estimate) ** 2)
        ss_tot = np.sum((data - np.mean(data)) ** 2)
        r2 = 1 - (ss_res / ss_tot)
        return r2
