import numpy as np
import scipy.fftpack as fftpack


class LeastSquaresFit:
    """
    Base class for fit functions to be used with curve_fit. Specifies
    a particular mathematical function and information that can be used to
    perform a least squares fit to the data.

    Each class holds the mathematical function itself ('fun'), a function
    for determining an initial guess for the fit parameters ('guess'), and
    a list of attributes that set the function inputs and outputs, the fit
    parameter labels and names, and the relationship between the units on the
    input and output variables and the units on the parameters.
    """

    def __init__(self, name, fun_str, fun_np, fun_vars,
                 fun_output, p_names, p_labels, p_units):
        self.name = name
        self.fun_str = fun_str
        self.fun_np = fun_np
        self.fun_output = fun_output
        self.p_names = p_names
        self.p_units = p_labels
        self.p_units = p_units

    def fun(self, x, a, T, c):
        raise NotImplementedError('This is not implemented in the base class.')

    def guess(self, x, y):
        raise NotImplementedError('This is not implemented in the base class.')


class ExpDecay(LeastSquaresFit):
    def __init__(self, name='ExpDecayFit'):
        super().__init__(
            name=name,
            fun_str=r'$f(x) = a \exp(-x/T) + c$',
            fun_np='a*np.exp(-x/T)+c',
            fun_vars=['x'],
            fun_output=['y'],
            p_names=['$a$', '$T$', '$c$'],
            p_labels=['a', 'T', 'c'],
            p_units=['y', 'x', 'y'])

    def fun(self, x, a, T, c):
        return eval(self.fun_np)

    def guess(self, x, y):
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
    def __init__(self, name='ExpDecaySinFit'):
        super().__init__(
            name=name,
            fun_str=r'$f(x) = a \sin(\omega x +\phi)\exp(-x/T) + c$',
            fun_np='a*np.exp(-x/T)*np.sin(w*x+p)+c',
            fun_vars=['x'],
            fun_output=['y'],
            p_names=['$a$', '$T$', '$\omega$', '$\phi$', '$c$'],
            p_labels=['a', 'T', 'w', 'p', 'c'],
            p_units=['y', 'x', '1/x', '', 'y'])

    def fun(self, x, a, T, w, p, c):
        return eval(self.fun_np)

    def guess(self, x, y):
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
