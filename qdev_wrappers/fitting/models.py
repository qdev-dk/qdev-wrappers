import numpy as np


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
