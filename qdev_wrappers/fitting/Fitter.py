import qcodes as qc
import numpy as np
from scipy.optimize import curve_fit
from itertools import product
from least_squares_fit import LeastSquaresFit


class Fitter:
    """
    Class which performs fit for data based on data, fitclass and names of

    Args:
        data (dict)
        fitclass (currently limited to LeastSquaresFit)
        indept_var (str): name of parameter in data dict to be used as
            independent variable in fit procedure. eg 'pulse_readout_delay'
        dept_var (str): name of parameter in data dict which represents
            dependent variable for fitting. eg 'cavity_magnitude_result'
    """

    def __ init__(self, data: dict, fitclass: LeastSquaresFit,
                  indept_var: str, dept_var: str):
        self.fitclass = fitclass
        self.experiment_info = {'exp_id': data['exp_id'],
                                'run_id': data['run_id'],
                                'sample_name': data['sample_name']}
        self.indept_var = data[indept_var]
        self.dept_var = data[dept_var]
        self.setpoints = {k: data[k] for k in data.keys() if
                          k not in [indept_var, dept_var]}
        self.fit_parameters = {
            fitclass.param_names[i]:
            {'name': fitclass.param_names[i],
             'label': fitclass.param_labels[i],
             'unit': fitclass.param_units[i]} for
            i in len(fitclass.param_names)}
        self.estimator = {'method': 'LSF',
                          'type': fitclass.name,
                          'fit_function_str': fitclass.fun_str}  # TODO: add dill here
        self.fit_results = self._do_fitting_procedure()

    def _do_fitting_procedure(self):
        """
        Populates fit_results list with one dictionary per combination
        of setpoints.

        eg
        for self.setpoints = {'frequency':
                                {'label': '',
                                 'unit': 'Hz',
                                 'data': [1e9, 2e9, 3e9]},
                              'power':
                                {'label': '',
                                 'unit': 'dBm',
                                 'data': [-10, -30]}}

        will make 6 dictionaries of the form
        {
            'setpoint_names': ['frequency', 'power'],
            'setpoint_labels': {'frequency': '' , 'power': ''},
            'setpoint_units': {'frequency': 'Hz' , 'power': 'dBm'},
            'setpoint_values': {'frequency': 1e9 , 'power': -10},
            'param_names': ['a', 'b'],
            'param_labels': {'a': 'T1', 'b': 'b'},
            'param_units': {'a': 's', 'b': ''},
            'param_start_values': {'a': 3, 'b': 10},
            'param_values': {'a': 2.5, 'b': 11},
            'param_variance': {'a': 0.1, 'b': 2},
            'indept_var_name': 'pulse_readout_delay',
            'indept_var_label': 'Pulse Readout Delay',
            'indept_var_unit': 's',
            'indept_var_values': [0.1, 0.2, 0.3, 0.4],
            'dept_var_name': 'cavity_magnitude_response',
            'dept_var_label': 'Cavity Response',
            'dept_var_unit': '',
            'dept_var_values': [1.15, 1.26, 1.34, 1.23],
            'estimate_values' [1.1, 1.2, 1.3, 1.4]
        }
        """
        fit_results = []
        # if setpoints then perform fit for all
        if len(self.setpoints) > 0:
            setpoint_combinations = product(
                *[v['data'] for v in self.setpoints.values()])
            setpoint_names = list(self.setpoints.keys())
            setpoint_labels = [v['label'] for v in self.setpoints.values()]
            setpoint_units = [v['unit'] for v in self.setpoints.values()]
            for setpoint_combination in setpoint_combinations:
                # find indices where where setpoing combination is satisfied
                setpoint_0_indices = list(np.argwhere(
                    data[setpoint_names[0]['data']] == setpoint_combination[0]))
                for i in range(1, len(setpoint_names)):
                    new_setpoint_indices = list(np.argwhere(
                        data[setpoint_names[i]['data']] == setpoint_combination[i]))
                    union_setpoint_indices = []
                    for index in indices:
                        for new_index in new_indices:
                            if np.array_equal(index, new_index):
                                union_setpoint_indices.append(index)
                index = union_setpoint_indices[0]
                try:
                    input_data_array = data[self.indept_var['name']
                                            ]['data'][index]
                    output_data_array = data[self.dept_var['name']
                                             ]['data'][index]
                    result = self._perform_fit(input_data_array,
                                               output_data_array)
                    result.update(
                        {'setpoint_names': setpoint_names,
                         'setpoint_labels': dict(zip(setpoint_names,
                                                     setpoint_labels)),
                         'setpoint_units': dict(zip(setpoint_names,
                                                    setpoint_units)),
                         'setpoint_values': dict(zip(setpoint_names,
                                                     setpoint_combination)),
                         'indept_var_values': input_data_array,
                         'dept_var_values': output_data_array,
                         'indept_var_name': self.indept_var['name'],
                         'dept_var_name': self.dept_var['name'],
                         'indept_var_label': self.indept_var['label'],
                         'dept_var_label': data[self.dept_var]['label'],
                         'indept_var_unit': data[self.indept_var]['unit'],
                         'dept_var_unit': data[self.dept_var]['unit'],
                         'estimate_values':
                            self.find_estimate(input_data_array,
                                               param_dict['param_values'])})
                    fit_results.append(result)
                except Exception:  # TODO: what kind of exception
                    print('no data for setpoint combination ', dict(
                        zip(self.setpoints.keys(), setpoint_combination)))
        else:
            input_data_array = data[self.indept_var]['data'][index]
            output_data_array = data[self.dept_var]['data'][index]
            result = self._perform_fit(input_data_array,
                                       output_data_array)
            result.update(
                {'setpoint_names': [],
                 'indept_var_values': input_data_array,
                 'dept_var_values': output_data_array,
                 'indept_var_name': self.indept_var['name'],
                 'dept_var_name': self.dept_var['name'],
                 'indept_var_label': data[self.indept_var]['label'],
                 'dept_var_label': data[self.dept_var]['label'],
                 'indept_var_unit': data[self.indept_var]['unit'],
                 'dept_var_unit': data[self.dept_var]['unit'],
                 'estimate_values':
                    self.find_estimate(input_data_array,
                                       param_dict['param_values'])})
            fit_results.append(result)
            except Exception:  # TODO: what kind of exception
                print('no data for setpoint combination ', dict(
                    zip(self.setpoints.keys(), setpoint_combination)))
        return fit_results

    def get_result(**setpoint_values):
        """
        Args:
            kwargs for each setpoints
                eg 'frequency=1e9, power=-10'
        Returns:
            dict for fit where these conditions are satisfiedxw
        """
        if len(setpoint_values) != len(self.setpoints):
            raise RuntimeError('Must specify a value for each setpoint')
        elif len(self.setpoints) == 0:
            return self.fit_results[0]
        else:
            return next(res for res in self.fit_results if
                        all(res[setpoint] == value for
                            setpoint, value in setpoint_values.items()))

    def _perform_fit(self, input_data_array, output_data_array):

        # make fit params dictionary
        params_dict = {'param_names': [], 'param_labels': {},
                       'param_units': {}, 'param_start_values': {},
                       'param_variance': {}, 'param_values': {}}
        for i, param_name in enumerate(fitcass.params_names):
            params_dict['param_names'].append(param_name)
            params_dict['param_labels'][param_name] = fitclass.param_labels[i]
            params_dict['param_units'][param_name] = fitclass.param_units[i]

        # find start parameters, run curve_fit function to perform fit
        p_guess = self.fitclass.guess(input_data_array, output_data_array)
        popt, pcov = curve_fit(fitclass.fun,
                               input_data_array,
                               output_data_array,
                               p0=p_guess)

        # add guess and fit results to dict
        for i, param_name in enumerate(self.fitclass.param_names):
            params_dict['param_start_values'][param_name] = p_guess[i]
            params_dict['param_values'][param_name] = popt[i]
            params_dict['param_variance'][param_name] = pcov[i, i]

        return params_dict

    def _find_estimate(self, input_data_array, params_values_dict):
        return fitlass.fun(input_data_array, **params_values_dict)

    def plot(self, **setpoint_config):
        raise NotImplementedError
