import qcodes as qc
import numpy as np

from scipy.optimize import curve_fit
from itertools import product
from qcodes.config.config import DotDict


def fit_data(data, fitclass, fun_inputs, fun_output, **kwargs):
    """
    Fits the data in the data dictionary using the fit class provided and the
    mappings provided to generate a fit dictionary.

    Args:
        data (dict)
        fitclass (currently limited to LeastSquaresFit)
        fun_input (dict): mapping between data name in data dictionary and
            argument of fitclass function eg {'x': 'pulse_readout_delay'}
        fun_output (dict: mapping between data name in data dictionary and
            return of fit class function eg {'y': 'data'}
        **kwargs (optional): passed to find_fit function of fit class

    Returns:
        fit (dict): containing the fitted parameters and an array of
            "estimated" outputs given the fit as well as some metadata about
            the fit.
    """

    check_input_matches_fitclass(fitclass, fun_input, fun_output)

    setpoints = [v for v in data['variables'] if
                 v not in set([*fun_input.values(),
                               *fun_output.values()])]
    return Fitter(data, fitclass, fun_input, fun_output, setpoints)


class Fitter:
    """
    Class which performs fit for data based on data, fitclass, mapping between
    paramter names and fit function arguments/returns and setpoints
    """

    def __ init__(self, data, fitclass, fun_input, fun_output, setpoints):
        """
        Args:
            data (dict)
        """
        self.fitclass = fitclass
        self.fun_input = fun_input
        self.fun_output = fun_output
        self.setpoints = {setpoint: set(data[setpoint].flatten()) for
                          setpoint in setpoints}
        self.estimator = {'method': 'LSF',
                          'type': fitclass.name,
                          'fit_function_str': fitclass.fun_str}
        self.inferred_from = data.run_id
        self.fit_results = []
        self._do_fitting_procedure()

    def _do_fitting_procedure(self):
        """
        Populates fit_results list with one dictionary per combination
        of setpoints. Dictionaries are of the form:

        for self.setpoints = {'temperature': [0.01, 0.02, 0.03]}

        {
            'temperature': 0.02,
            'param_names': ['a', 'b'],
            'param_labels': {'a': 'T1', 'b': 'b'},
            'param_units': {'a': 's', 'b': ''},
            'param_start_values': {'a': 3, 'b': 10},
            'param_values': {'a': 2.5, 'b': 11},
            'param_variance': {'a': 0.1, 'b': 2},
            'input': [0.1, 0.2, 0.3, 0.4],
            'output': [1.15, 1.26, 1.34, 1.23]
            'estimate' [1.1, 1.2, 1.3, 1.4]
        }
        """

        # if setpoints then perform fit for all
        if len(self.setpoints) > 0:
            setpoint_combinations = product(*self.setpoints.values())
            setpoint_names = self.setpints.keys()
            for setpoint_combination in setpoint_combinations:
                # find indices where where setpoing combination is satisfied
                setpoint_0_indices = list(np.argwhere(
                    data[setpoint_names[0]] == setpoint_combination[0]))
                for i in range(1, len(setpoint_names)):
                    new_setpoint_indices = list(np.argwhere(
                        data[setpoint_names[i]] == setpoint_combination[i]))
                    union_setpoint_indices = []
                    for index in indices:
                        for new_index in new_indices:
                            if np.array_equal(index, new_index):
                                union_setpoint_indices.append(index)
                index = union_setpoint_indices[0]
                try:
                    result = {}
                    input_data_array = {k: data[v][index]
                                        for k, v in fun_input.items()}
                    output_data_array = {k: data[v][index]
                                         for k, v in fun_output.items()}
                    param_dict = self._perform_fit(input_data_array,
                                                   output_data_array)
                    result.update(dict(zip(self.setpoints.keys(),
                                           setpoint_combination)))
                    result.update({'input': input_data_array,
                                   'output': output_data_array})
                    result.update(
                        {'estimate':
                            self.find_estimate(input_data_array,
                                               param_dict['param_values'])})
                    result.update(result)
                    self.fit_results.append(result)
                except Exception:  # TODO: what kind of exception
                    print('no data for setpoint combination ', dict(
                        zip(self.setpoints.keys(), setpoint_combination)))
        else:
            input_data_array = {k: data.get_data(v) for
                                k, v in fun_input.items()}
            output_data_array = {k: data.get_data(v) for
                                 k, v in fun_output.items()}
            param_dict = self.perform_fit(input_data_array,
                                          output_data_array)
            result.update({'input': input_data_array,
                           'output': output_data_array})
            result.update(
                {'estimate':
                    self.find_estimate(input_data_array,
                                       param_dict['param_values'])})
            self.fit_dict['fit_results'].append(result)

    def get_result(**setpoint_values):
        if len(setpoint_values) != len(self.setpoints):
            raise RuntimeError('Must specify a value for each setpoint')
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
        for i, param_name in enumerate(self.fitclass.p_names):
            params_dict['param_start_values'][param_name] = p_guess[i]
            params_dict['param_values'][param_name] = popt[i]
            params_dict['param_variance'][param_name] = pcov[i, i]

        return params_dict

    def find_estimate(self, input_data_array, params_values_dict):
        return fitlass.fun(input_data_array, **params_values_dict)


    def check_input_matches_fitclass(self):
        """
        Checks that the given arguments are in the correct format for the
        'fit_data' function to proceed, and that they match the expected inputs for
        the specified fit class.

        Each fit class describes a mathematical function to be fitted to,
        with a set of attributes, including which variables the function has as
        inputs, and what outputs it has. This function makes sure that the correct
        inputs and outputs are specified compared to what inputs and outputs the
        mathematical function has, and that they are specified in the correct
        format.

        Args:
            fitclass (currently only LeastSquaresFit implemented)
            inputs (dict)
            output (dict)
        """

        # check input and output are given, and that input,
        # output and setpoints are in correct format
        if (type(inputs) != dict or type(output) != dict):
            raise RuntimeError(
                'Please specify both input and output variables for the function '
                'you wish to fit in the format fun_inputs = '
                '{"x": "name", "y": "other_name"}, fun_output ='
                ' {"z": "another_name"}')

        # check inputs/outputs specified match inputs/outputs function takes
        if len(inputs) != len(fitclass.fun_vars):
            raise RuntimeError(
                'The function you are fitting to takes {} variables, and you '
                'have specified {}'.format(len(fitclass.fun_vars), len(inputs)))
        for variable in inputs.keys():
            if variable not in fitclass.fun_vars:
                raise RuntimeError(
                    'You have specified a variable {}. The fit function takes'
                    'variables {}'.format(variable, fitclass.fun_vars))
        for variable in output.keys():
            if variable not in fitclass.fun_output:
                raise RuntimeError(
                    'You have specified a variable {}. The fit function returns '
                    'variables {}'.format(variable, fitclass.fun_output))
