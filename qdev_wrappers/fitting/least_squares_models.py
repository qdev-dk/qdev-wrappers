import numpy as np
from qdev_wrappers.fitting.models import Model
import qdev_wrappers.fitting.guess as g
from scipy.optimize import curve_fit


class LeastSquaresModel(Model):
    def __init__(self, model_parameters, model_vars, model_function, guess):
        super().__init__(model_parameters, model_vars, model_function, guess)
        self.summary = {'method': 'Least squares',
                        'function': {'func_str': self.func_str, 'func_np': self.func_np},
                        'parameters': self.parameters.copy()}  # TODO: add dill here?

        """"data_saving_info" contains information for saving the additional information returned
         by the model, beyond the parameter values. In the case of least squares fitting, this is 
         variance and initial guess values. If these results don't share a unit with their parameter, 
         the dictionary should also include 'units'."""
        self.data_saving_info = {'variance': {'type': 'numeric', 'label': ' variance'},
                                 'start_values': {'type': 'numeric', 'label': ' initial value'}}

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

        if len(function_variable_arrays) > 1:
            raise NotImplementedError("Least squares model guess and fit procedure are not set up for 2D fits yet")
        else:
            input_data_array = [array for array in function_variable_arrays.values()][0]
            p_guess = self.get_initial_guess(output_data_array, **function_variable_arrays)
            popt, pcov = curve_fit(self.evaluate, input_data_array, output_data_array, p0=p_guess)

            return popt, [pcov, p_guess]

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

            for i, param_name in enumerate(self.parameters.keys()):
                params_dict['variance'][param_name] = pcov[i, i]
                params_dict['start_values'][param_name] = p_guess[i]

        del params_dict['fit_info']
        return params_dict


class Benchmarking(LeastSquaresModel):

    def __init__(self):
        guess = g.PowerDecayGuess()
        model_parameters = {'a': {'label': '$a$', 'unit': 'V'},
                            'p': {'label': '$p$', 'unit': ''},
                            'b': {'label': '$b$', 'unit': 'V'}}
        model_vars = ['x']
        model_function = {'str': r'$f(x) = A p^x + B$',
                          'np': 'a * p**x + b'}

        super().__init__(model_parameters, model_vars, model_function, guess)


class CosineModel(LeastSquaresModel):

    def __init__(self):
        guess = g.CosineGuess()
        model_parameters = {'a': {'label': '$a$',       'unit': ''},
                            'w': {'label': r'$\omega$', 'unit': 'Hz'},
                            'p': {'label': r'$\phi$', 'unit': ''},
                            'b': {'label': '$c$',       'unit': ''}}
        model_vars = ['x']
        model_function = {'str': r'$f(x) = a\cos(\omega x + \phi)+b$',
                          'np': 'a * np.cos(w * x + p) + b'}

        super().__init__(model_parameters, model_vars, model_function, guess)


class CosineModelSwapped(LeastSquaresModel):

    def __init__(self):
        guess = g.CosineGuess()
        model_parameters = {'a': {'label': '$a$',       'unit': ''},
                            'p': {'label': r'$\phi$', 'unit': ''},
                            'w': {'label': r'$\omega$', 'unit': 'Hz'},
                            'b': {'label': '$c$',       'unit': ''}}
        model_vars = ['x']
        model_function = {'str': r'$f(x) = a\cos(\omega x + \phi)+b$',
                          'np': 'a * np.cos(w * x + p) + b'}

        super().__init__(model_parameters, model_vars, model_function, guess)


class DecayT1(LeastSquaresModel):

    def __init__(self):
        guess = g.ExpDecayGuess()
        model_parameters = {'a': {'label': '$a$', 'unit': ''},
                            'T': {'label': '$T$', 'unit': 's'},
                            'c': {'label': '$c$', 'unit': ''}}
        model_vars = ['x']
        model_function = {'str': r'$f(x) = a \exp(-x/T) + c$',
                          'np': 'a*np.exp(-x/T)+c'}

        super().__init__(model_parameters, model_vars, model_function, guess)


class DecayingRabis(LeastSquaresModel):

    def __init__(self):
        guess = g.ExpDecaySinGuess()
        model_parameters = {'a': {'label': '$a$',       'unit': ''},
                            'T': {'label': '$T$',       'unit': 's'},
                            'w': {'label': r'$\omega$', 'unit': 'Hz'},
                            'p': {'label': r'$\phi$',   'unit': ''},
                            'c': {'label': '$c$',       'unit': ''}}
        model_vars = ['x']
        model_function = {'str': r'$f(x) = a \exp(-x/T) \sin(\omega x +\phi) + c$',
                          'np': 'a*np.exp(-x/T)*np.sin(w*x+p)+c'}

        super().__init__(model_parameters, model_vars, model_function, guess)



