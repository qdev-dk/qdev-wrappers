import numpy as np
import scipy.fftpack as fftpack
from typing import List
from qcodes import Instrument
from scipy.optimize import curve_fit
from collections import OrderedDict


class LeastSquaresFit(Instrument):
    """
    Base class for fit functions to be used with curve_fit. Specifies
    a function for fitting, function for guessing initial parameters for fit
    and attributes specifying inputs and output of fit function as
    well as and names, labels and units of fit parameters.

    Only one input and one output is currently allowed.

    Order of parameters in model_parameters ordered dictionary must match function guess
    output and order of appearance in func
    """
    model_parameters = OrderedDict({})
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        for param_name, param_kwargs in self.model_parameters.items():
            self.add_parameter(param_name, set_cmd=False, **kwargs)
        del self.parameters['IDN']

    def func(self, *args):
        """
        The mathematical function to fit to
        """
        raise NotImplementedError('This is not implemented in the base class.')

    def guess(self, *args):
        """
        Function for determining an initial guess for the fit parameters from
        given values or based on perform guess function
        """
        raise NotImplementedError

    def perform_fit(self, input_data_array, output_data_array):

        # find start parameters, run curve_fit function to perform fit
        p_guess = self.guess(input_data_array, output_data_array)
        popt, pcov = curve_fit(self.func,
                               input_data_array,
                               output_data_array,
                               p0=p_guess)

        # update guess and fit results in fit parameters
        for i, param in enumerate(self.model_parameters):
            self.parameters[param]._save_val(popt[i])
            self.parameters[param].start_value = p_guess[i]
            self.parameters[param].variance = pcov[i, i]


class ExpDecay(LeastSquaresFit):

    model_parameters = OrderedDict({'a': {'label':'$a$', 'unit':''},
                                    'T': {'label':'$T$', 'unit':'s'},
                                    'c': {'label':'$c$', 'unit':''}   })
    def __init__(self, name, guess=None):
        super().__init__(name)
        self.guess_params = guess
        self.fun_str=r'$f(x) = a \exp(-x/T) + c$'
        self.fun_np='a*np.exp(-x/T)+c'

    def func(self, x, a, T, c):
        return eval(self.fun_np)

    def guess(self, x, y):
        if self.guess_params is not None:
            return self.guess_params
        length = len(y)
        val_init = y[0:round(length / 20)].mean()
        val_fin = y[-round(length / 20):].mean()
        a = val_init - val_fin
        c = val_fin
        # guess T1 as point where data has fallen to 1/e of init value
        idx = (np.abs(y - a / np.e - c)).argmin()
        T = x[idx]
        return [a, T, c]


class ExpDecaySin(LeastSquaresFit):

    model_parameters = OrderedDict({'a': {'label': '$a$', 'unit': ''},
                                    'T': {'label': '$T$', 'unit': 's'},
                                    'w': {'label': r'$\omega$', 'unit': 'Hz'},
                                    'p': {'label': r'$\phi$', 'unit': ''},
                                    'c': {'label': '$c$', 'unit': ''}})
    def __init__(self, name, guess=None):
        super().__init__(name)
        self.guess_params = guess
        self.fun_str = r'$f(x) = a \sin(\omega x +\phi)\exp(-x/T) + c$'
        self.fun_np = 'a*np.exp(-x/T)*np.sin(w*x+p)+c'

    def func(self, x, a, T, w, p, c):
        return eval(self.fun_np)

    def guess(self, x, y):
        if self.guess_params is not None:
            return self.guess_params
        a = y.max() - y.min()
        c = y.mean()
        # guess T2 as point half way point in data
        T = x[round(len(x) / 2)]
        # Get initial guess for frequency from a fourier transform
        yhat = fftpack.rfft(y - y.mean())
        idx = (yhat**2).argmax()
        freqs = fftpack.rfftfreq(len(x), d=(x[1] - x[0]) / (2 * np.pi))
        w = freqs[idx]
        p = 0
        return [a, T, w, p, c]


class PowerDecay(LeastSquaresFit):

    model_parameters = OrderedDict({'a': {'label': '$a$', 'unit': 'V'},
                                    'p': {'label': '$p$', 'unit': ''},
                                    'b': {'label': '$c$', 'unit': 'V'}})
    def __init__(self, name, guess=None):
        super().__init__(name)
        self.guess_params = guess
        self.fun_str = r'$f(x) = A p^x + B$'
        self.fun_np = 'a * p**x + b'

    def func(self, x, a, p, b):
        return eval(self.fun_np)

    def guess(self, x, y):
        if self.guess_params is not None:
            return self.guess_params
        
        length = len(y)
        val_init = y[0:round(length / 20)].mean()
        val_fin = y[-round(length / 20):].mean()
        a = val_init - val_fin
        b = val_fin

        # guess T as point where data has fallen to 1/e of init value
        idx = (np.abs(y - a / np.e - b)).argmin()
        T = x[idx]
        #guess p as e^(-1/T):
        p = np.e**(-1/T)

        return [a, p, b]