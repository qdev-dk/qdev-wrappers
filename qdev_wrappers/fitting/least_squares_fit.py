import numpy as np
import scipy.fftpack as fftpack
from typing import List
from qcodes import Instrument
from scipy.optimize import curve_fit


class LeastSquaresFit(Instrument):
    """
    Base class for fit functions to be used with curve_fit. Specifies
    a function for fitting, function for guessing initial parameters for fit
    and attributes specifying inputs and output of fit function as
    well as and names, labels and units of fit parameters.

    Only one input and one output is currently allowed.

    Order of param_names, param_labels, param_units must match function guess
    output and order of appearance in fun
    """

    def __init__(self, name, fun_str, fun_np,
                 param_names, param_labels, param_units):
        super().__init__(name)
        self.fun_str = fun_str
        self.fun_np = fun_np
        self.param_names = param_names

        for idx, parameter in enumerate(self.param_names):
            self.add_parameter(name=parameter,
                               unit=param_units[idx],
                               label=param_labels[idx],
                               set_cmd=False)
        del self.parameters['IDN']

    def perform_fit(self, input_data_array, output_data_array):

        # find start parameters, run curve_fit function to perform fit
        p_guess = self.guess(input_data_array, output_data_array)
        popt, pcov = curve_fit(self.fun,
                               input_data_array,
                               output_data_array,
                               p0=p_guess)

        # update guess and fit results in fit parameters
        for i, param in enumerate(self.param_names):
            self.parameters[param]._save_val(popt[i])
            self.parameters[param].start_value = p_guess[i]
            self.parameters[param].variance = pcov[i, i]

    def fun(self, *args):
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


class ExpDecay(LeastSquaresFit):
    def __init__(self, name='ExpDecayFit', guess: List=None):
        super().__init__(
            name=name,
            fun_str=r'$f(x) = a \exp(-x/T) + c$',
            fun_np='a*np.exp(-x/T)+c',
            param_labels=['$a$', '$T$', '$c$'],
            param_names=['a', 'T', 'c'],
            param_units=['', 's', ''])
        self.guess_params = guess

    def fun(self, x, a, T, c):
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
    def __init__(self, name='ExpDecaySinFit', guess: List=None):
        super().__init__(
            name=name,
            fun_str=r'$f(x) = a \sin(\omega x +\phi)\exp(-x/T) + c$',
            fun_np='a*np.exp(-x/T)*np.sin(w*x+p)+c',
            param_labels=['$a$', '$T$', r'$\omega$', r'$\phi$', '$c$'],
            param_names=['a', 'T', 'w', 'p', 'c'],
            param_units=['', 's', 'Hz', '', ''])
        self.guess_params = guess

    def fun(self, x, a, T, w, p, c):
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
    def __init__(self, name='PowerFit', guess: List=None):
        super().__init__(
            name=name,
            fun_str=r'$f(x) = A p^x + B$',
            fun_np='a * p**x + b',
            param_labels=['$A$', '$p$', '$B$'],
            param_names=['a', 'p', 'b'],
            param_units=['V', '', 'V'])
        self.guess_params = guess

    def fun(self, x, a, p, b):
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


class FirstOrderBM(LeastSquaresFit):
    def __init__(self, name='1st order benchmarking', guess: List=None):
        super().__init__(
            name=name,
            fun_str=r'$f(x) = A p^x + C(x-1)p^{x-2} + B$',
            fun_np='a * p**x + c*(x-1)*p**(x-2) + b',
            param_labels=['$A$', '$p$', '$B$'],
            param_names=['a', 'p', 'b'],
            param_units=['V', '', 'V'])
        self.guess_params = guess

    def fun(self, x, a, p, b):
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
        # guess p as e^(-1/T)
        b = val_fin

        # guess T as point where data has fallen to 1/e of init value
        idx = (np.abs(y - a / np.e - b)).argmin()
        T = x[idx]
        #guess p as e^(-1/T):
        p = np.e**(-1/T)

        return [a, p, b]
