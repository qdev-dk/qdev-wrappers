from collections import OrderedDict
import numpy as np


class LeastSquaresModel(object):
    def __init__(self, model_parameters, model_function):
        self.modelparam_names = [key for key in model_parameters]
        self.model_parameters = model_parameters
        self.func_str = model_function['str']
        self.func_np = model_function['np']

        arg_list = ", ".join(self.modelparam_names)
        self.func = eval(f"lambda {arg_list}: {self.func_np}")

    def func(self, *args):

        """The mathematical function to fit to"""

        raise NotImplementedError('This is not implemented in the base class.')



class DecayT1(LeastSquaresModel):

    def __init__(self):
        model_parameters = OrderedDict({'a': {'label': '$a$', 'unit': '' },
                                        'T': {'label': '$T$', 'unit': 's'},
                                        'c': {'label': '$c$', 'unit': '' } })

        model_function = {'str': r'$f(x) = a \exp(-x/T) + c$',
                          'np': 'a*np.exp(-x/T)+c'}

        super().__init__(model_parameters, model_function)

    def func(self, x, a, T, c):
        return eval(self.func_np)


class DecayingRabis(LeastSquaresModel):

    def __init__(self):
        model_parameters = OrderedDict({'a': {'label': '$a$',       'unit': ''  },
                                        'T': {'label': '$T$',       'unit': 's' },
                                        'w': {'label': r'$\omega$', 'unit': 'Hz'},
                                        'p': {'label': r'$\phi$',   'unit': ''  },
                                        'c': {'label': '$c$',       'unit': ''  } })

        model_function = {'str': r'$f(x) = a \exp(-x/T) \sin(\omega x +\phi) + c$',
                          'np': 'a*np.exp(-x/T)*np.sin(w*x+p)+c'}

        super().__init__(model_parameters, model_function)

    def func(self, x, a, T, w, p, c):
        return eval(self.func_np)


class Benchmarking(LeastSquaresModel):

    def __init__(self):
        model_parameters = OrderedDict({'a': {'label': '$a$', 'unit': 'V'},
                                        'p': {'label': '$p$', 'unit': '' },
                                        'b': {'label': '$b$', 'unit': 'V'} })
        model_function = {'str': r'$f(x) = A p^x + B$',
                          'np': 'a * p**x + b'}

        super().__init__(model_parameters, model_function)

    def func(self, x, a, p, b):
        return eval(self.func_np)


class RabiT1(LeastSquaresModel):

    def __init__(self):
        model_parameters = OrderedDict({'T': {'label': '$T_2$',      'unit': 's'  },
                                        'w': {'label': '$w_{rabi}$', 'unit': 'Hz' } })
        model_function = {'str': r'$f(x) = e^(-x/T_2) \cos^2(\omega x / 2)$',
                          'np': 'np.exp(-x/T) * np.cos(w * x / 2) ** 2'}

        super().__init__(model_parameters, model_function)

    def func(self, x, T, w):
        return eval(self.func_np)


