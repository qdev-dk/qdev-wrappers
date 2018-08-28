import numpy as np
import scipy.fftpack as fftpack
from typing import List


class LeastSquaresFit:
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
                 fun_output, param_names, param_labels, param_units,
                 guess: List[float]=None):
        self.name = name
        self.fun_str = fun_str
        self.fun_np = fun_np
        self.param_names = param_names
        self.param_labels = param_labels
        self.param_units = param_units
        self.guess = guess

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
        if guess is not None:
            return guess
        else:
            return self.perform_guess(*args)

    def perform_guess(self, *args):
        """
        Function for determining an initial guess for the fit parameters
        """
        raise NotImplementedError('This is not implemented in the base class.')


class ExpDecay(LeastSquaresFit):
    def __init__(self, name='ExpDecayFit', guess=None):
        super().__init__(
            name=name,
            fun_str=r'$f(x) = a \exp(-x/T) + c$',
            fun_np='a*np.exp(-x/T)+c',
            param_labels=['$a$', '$T$', '$c$'],
            param_names=['a', 'T', 'c'],
            param_units=['', 's', ''],
            guess=guess)

    def fun(self, x, a, T, c):
        return eval(self.fun_np)

    def perform_guess(self, x, y):
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
    def __init__(self, name='ExpDecaySinFit', guess=None):
        super().__init__(
            name=name,
            fun_str=r'$f(x) = a \sin(\omega x +\phi)\exp(-x/T) + c$',
            fun_np='a*np.exp(-x/T)*np.sin(w*x+p)+c',
            param_labels=['$a$', '$T$', '$\omega$', '$\phi$', '$c$'],
            param_names=['a', 'T', 'w', 'p', 'c'],
            param_units=['', 's', 'Hz', '', ''],
            guess=guess)

    def fun(self, x, a, T, w, p, c):
        return eval(self.fun_np)

    def perform_guess(self, x, y):
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
