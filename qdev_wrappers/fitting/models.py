import numpy as np
from scipy.optimize import curve_fit


class Model(object):
    def __init__(self, model_parameters, model_vars, model_function, guess):
        self.parameters = model_parameters
        self.variables = model_vars
        self.func_str = model_function['str']
        self.func_np = model_function['np']
        self.default_guess = guess  # defined by model, should not be changed
        self.guess = guess         # to be updated if a different guess than the default is given

        self.summary = {'method': '',
                        'function': [self.func_str, self.func_np]}  # TODO: add dill here

        """Any results the model returns for the parameters beyond the parameter values themselves 
        should be included in "data_saving_info". See least_squares_models for example"""
        self.data_saving_info = {}

    def evaluate(self, *args):
        """Used for plotting and for producing estimates from data. Takes values
        for function variables followed by parameter values. Returns a function
        output from evaluating the model function at the provided values."""
        raise NotImplementedError('This is not implemented in the base class.')

    def get_initial_guess(self, output_array, **function_variable_arrays):
        """ Takes an output array - i.e. data array - as the first argument. Also takes
        keyword arguments for the variables in the function to be fitted. Returns a list of
        initial values for the parameters in the model.
        If a user-defined list for initial parameter guesses was given to the fitter, it
        returns that list. Otherwise, it returns a guess, as defined by the model's 'guess',
        based on the arrays given."""
        if self.guess != self.default_guess:
            initial_guess = self.guess
        else:
            initial_guess = self.guess.make_guess(output_array, **function_variable_arrays)
        return initial_guess

    def fit_procedure(self, output_data_array, **function_variable_arrays):
        """ Performs the fit, returns parameter values and any additional information
        the fitting function returned, in the format:

            [list of parameter values], [fit info]

        where fit info is any additional information returned by the model (fx. variance).
        If there is no additional information beyond the returned parameters, the list
        should be left empty. """
        raise NotImplementedError('This is not implemented in the base class.')

    def organize_fit_info(self, parameter_dict):
        """Organize the additional information the model provides and incorporate in
        into the parameter dictionary. Default: ignore all fit information beyond
        parameter values"""
        del parameter_dict['fit_info']
        return parameter_dict


class SimpleMinimum(Model):
    def __init__(self):
        guess = None
        model_parameters = {'location': {'label': 'location of minimum', 'unit': ''},
                            'value': {'label': 'minimum value', 'unit': ''}}
        model_vars = ['x']
        model_function = {'str': 'find minimum (simple)',
                          'np': None}

        super().__init__(model_parameters, model_vars, model_function, guess)
        self.summary = {'method': 'using np.argmin to find minimum',
                        'function': [self.func_str, self.func_np]}

    def evaluate(self, *args):
        raise NotImplementedError("This model only returns the minimum, not "
                                  "parameters that fit a function.")

    def fit_procedure(self, output_array, **function_variable_arrays):
        """No additional info beyond parameter values, so the returned fit_info
        list is empty"""
        if len(function_variable_arrays) > 1:
            raise RuntimeError("Simple minimum can only find the minimum with respect to one variable. "
                               "You seem to have provided multiple variables.")
        input_array = [data_array for data_array in function_variable_arrays.values()][0]

        min_index = np.argmin(output_array)

        min_point = input_array[min_index]
        min_val = output_array[min_index]

        popt = np.array([min_point, min_val])

        return popt, []

    def update_unit(self, parameter, unit):
        self.parameters[parameter]['unit'] = unit
        print('{} unit updated to {}'.format(parameter, unit))


class LauritsMobility(Model):

    def __init__(self):
        guess = None
        model_parameters = {'vt': {'label': '$V_th$', 'unit': 'V'},
                            'a': {'label': r'$\alpha$', 'unit': ''},
                            'r': {'label': '$R_s$', 'unit': ''},
                            'vt1': {'label': '$V_th$', 'unit': 'V'},
                            'a2': {'label': r'$\alpha$', 'unit': ''},
                            'r2': {'label': '$R_s$', 'unit': ''}}
        model_vars = ['vg']
        model_function = {'str': r'$f(V_g) = 1/ (R + (\alpha /(V_g - V_th))$', 'np': '1/(r + a/(vg-vt))'}

        super().__init__(model_parameters, model_vars, model_function, guess)

    def evaluate(self, *args):
        """Takes an array, x, and a list of parameter values, in the order they are given
        in model parameters. Evaluates the output of the model function at each point in x,
        and returns an array of the output"""
        arg_list = self.variables + [key for key in self.parameters.keys()]
        arg_string = ", ".join(arg_list)
        func = eval(f"lambda {arg_string}: {self.func_np}")
        return func(*args)

    def fit_procedure(self, output_data_array, **function_variable_arrays):
        """Performs a fit based on the model. Returns :
            an array of parameter values, ordered like the model_parameters dictionary AND
            a fit_info list with the covariance matrix and the initial parameter guesses
            """

        p_guess = self.get_initial_guess(output_data_array, **function_variable_arrays)
        vt_guess = p_guess[0]

        gate_voltages = [array for array in function_variable_arrays.values()][0]
        single_scan_length = int(len(gate_voltages) / 2)

        # get arrays for curve 1
        gate_sweep_1 = gate_voltages[:single_scan_length]
        conductance_1 = output_data_array[:single_scan_length]
        above_vt = np.where(gate_sweep_1 > vt_guess)
        Vg_1 = gate_sweep_1[above_vt]
        G_1 = conductance_1[above_vt]

        # get arrays for curve 2
        gate_sweep_2 = gate_voltages[single_scan_length:]
        conductance_2 = output_data_array[single_scan_length:]
        above_vt = np.where(gate_sweep_1 > vt_guess)
        Vg_2 = gate_sweep_2[above_vt]
        G_2 = conductance_2[above_vt]

        # find diff
        diff = np.abs(G_2 - G_1)

        # fit to both curves
        func = eval(f"lambda vg, vt, a, r: {self.func_np}")
        popt1, pcov1 = curve_fit(func, Vg_1, G_1, p0=p_guess)
        popt2, pcov2 = curve_fit(func, Vg_2, G_2, p0=p_guess)

        # combine fit info
        popt = np.concatenate([popt1, popt2])

        pcov = [pcov1, pcov2]

        return popt, [pcov, p_guess, diff]


def organize_fit_info(self, params_dict):
    """Takes the params_dict as produced by the fit procedure:

            {'param_values': {'a' : 1, 'b', 2} , 'param_info': fit_info }

        In the case of Least Mean Squares fit models, fit_info is
        [pcov, p_guess] (the covariance matrix and initial guess). Organizes
        the additional fit info, and returns an updated params_dict."""

    if params_dict['fit_info'] is not None:
        params_dict['variance'] = {}
        params_dict['start_values'] = {}

        pcov = params_dict['fit_info'][0]
        p_guess = params_dict['fit_info'][1]
        diff = params_dict['fit_info'][2]

        for i, param_name in enumerate(self.parameters.keys()):
            params_dict['variance'][param_name] = pcov[i, i]
            params_dict['start_values'][param_name] = p_guess[i]

        params_dict['difference'] = diff

    del params_dict['fit_info']
    return params_dict

