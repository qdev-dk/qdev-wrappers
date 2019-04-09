import numpy as np
import scipy.fftpack as fftpack


def exp_decay(y, x):
    """Guess for f(x) = a * e^(-x/b)  +  c"""
    length = len(y)
    val_init = y[0:round(length / 20)].mean()
    val_fin = y[-round(length / 20):].mean()

    a = val_init - val_fin

    c = val_fin

    # guess b as point where data has fallen to 1/e of init value
    idx = (np.abs(y - a / np.e - c)).argmin()
    b = x[idx]

    return [a, b, c]


def exp_decay_sin(y, x):
    """Guess for f(x) = a * e^(-x/b) sin(wx+p)  + c"""
    a = y.max() - y.min()

    c = y.mean()

    # guess b as point half way point in data
    b = x[round(len(x) / 2)]

    # Get initial guess for frequency from a fourier transform
    yhat = fftpack.rfft(y - y.mean())
    idx = (yhat**2).argmax()
    freqs = fftpack.rfftfreq(len(x), d=(x[1] - x[0]) / (2 * np.pi))
    w = freqs[idx]

    p = 0

    return [a, b, w, p, c]


def power_decay(y, x):
    """Guess for f(x) = a * b^x + c"""
    length = len(y)
    val_init = y[0:round(length / 20)].mean()
    val_fin = y[-round(length / 20):].mean()

    a = val_init - val_fin

    c = val_fin

    # find index where data has fallen to 1/e of init value
    idx = (np.abs(y - a / np.e - c)).argmin()
    # guess b as e^(-1/x[idx]):
    b = np.e ** (-1 / x[idx])

    return [a, b, c]


def rabi_t1(y, x):
    """Guess for f(x) = e^(-x/b) cos^2(wx/2 + p)"""
    # guess b as point half way point in data
    b = x[round(len(x) / 2)]

    # Get initial guess for frequency from a fourier transform
    yhat = fftpack.rfft(y - y.mean())
    idx = (yhat ** 2).argmax()
    freqs = fftpack.rfftfreq(len(x), d=(x[1] - x[0]) / (2 * np.pi))
    w = freqs[idx] * 2

    return [b, w]


def cosine(y, x):
    """Guess for f(x) = a * cos(wx + p) + c"""
    c = y.mean()

    a = (y.max() - y.min()) / 2

    # Get initial guess for frequency from a fourier transform
    yhat = fftpack.rfft(y - y.mean())
    idx = (yhat ** 2).argmax()
    freqs = fftpack.rfftfreq(len(x), d=(x[1] - x[0]) / (2 * np.pi))
    w = freqs[idx]

    if (y[0] - c) / a > 1:
        p = 0
    elif (y[0] - c) / a < -1:
        p = np.pi
    else:
        p = np.arccos((y[0] - c) / a)

    return [a, w, p, c]
