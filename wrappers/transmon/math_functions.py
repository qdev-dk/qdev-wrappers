import numpy as np
from math import sqrt, factorial
from scipy import signal


def qubit_from_push(g, bare_res, pushed_res):
    """
    Get estimated qubit location given coupling, push on resonator
    and bare resonator position.

    Args:
        g: coupling in Hz
        bare_res: high power resonator position in Hz
        pushed_res: low power resonator position in Hz

    Returns:
        estimated qubit frequency
    """
    push = pushed_res - bare_res
    delta = g**2 / push
    return bare_res - delta


def g_from_qubit(qubit, bare_res, pushed_res):
    """
    Get estimated coupling strength given qubit frequency, push
    on resonator and bare resonator position.

    Args:
        qubit: qubit frequency
        bare_res: high power resonator position in Hz
        pushed_res: low power resonator position in Hz

    Returns:
        coupling of qubit to resonator
    """
    push = pushed_res - bare_res
    delta = bare_res - qubit
    return sqrt(delta * push)


def resonator_from_qubit(qubit, g, bare_res):
    """
    Get estimated resonator position based on qubit position,
    qubit resonator coupling and bare resonator position

    Args:
        qubit: qubit frequency
        g: coupling in Hz
        bare_res: resonator position in Hz

    Returns:
        estimated resonator frequency
    """
    delta = bare_res - qubit
    push = g**2 / delta
    return bare_res + push


def exp_decay_sin(x, a, b, c, d, e):
    """
    Returns exponential decay modulated sine
    """
    return a * np.exp(-x / b) * np.sin(c * x + d) + e


def exp_decay(x, a, b, c):
    """
    Returns exponential decay
    """
    return a * np.exp(-x / b) + c


def smooth_data_SG(y, window_size, order, deriv=0, rate=1):
    """
    Function which does savitzky_golay data smoothing method

    Args:
        y (numpy array): array for filtering
        window_size (int): size of window in points for smoothing
        order (int): polynomial order to use for smoothing

    Returns:
        filtered array
    """
    try:
        window_size = np.abs(np.int(window_size))
        order = np.abs(np.int(order))
    except ValueError:
        raise ValueError("window_size and order have to be of type int")
    if window_size % 2 != 1 or window_size < 1:
        raise TypeError("window_size size must be a positive odd number")
    if window_size < order + 2:
        raise TypeError("window_size is too small for the polynomials order")
    order_range = range(order + 1)
    half_window = (window_size - 1) // 2

    # precompute coefficients
    b = np.mat([[k**i for i in order_range]
                for k in range(-half_window, half_window + 1)])
    m = np.linalg.pinv(b).A[deriv] * rate**deriv * factorial(deriv)

    # pad the signal at the extremes with values taken from the signal itself
    firstvals = y[0] - np.abs(y[1:half_window + 1][::-1] - y[0])
    lastvals = y[-1] + np.abs(y[-half_window - 1:-1][::-1] - y[-1])
    y = np.concatenate((firstvals, y, lastvals))

    return np.convolve(m[::-1], y, mode='valid')


def butter_lowpass(cutoff, fs, order):
    """
    Function which generates scipy butterworth filter to data

    Args:
        cutoff (float): frequency above which components should be removed
        order (int): filter order

    Returns:
        filter coefs: (numerator and denominator polynomials of IIR filter)
    """
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = signal.butter(order, normal_cutoff, btype='low', analog=False)
    return b, a


def smooth_data_butter(data, fs, cutoff, order):
    """
    Function which applies butterwoth filter to data

    Args:
        data (numpy array)
        cutoff (float): passed to butter_lowpass

    Returns:
        filtered data
    """
    b, a = butter_lowpass(cutoff, fs, order)
    return signal.filtfilt(b, a, data)


def gaussian_array(sigma, sigma_cutoff, amp, SR, positive=True):
    """
    Function which makes a gaussian of length (2*sigma_cutoff)

    Args:
        sampling_rate
        sigma
        sigma_cutoff
        amp (default 1)
    """
    t = np.linspace(-1 * sigma_cutoff * sigma, sigma_cutoff * sigma,
                    num=int(np.round(SR * 2 * sigma_cutoff * sigma)))
    prefactor = amp if positive else -1 * amp
    return prefactor * np.exp(-(t / (2 * sigma))**2)


def cos_gaussian_array(sigma, sigma_cutoff, SSBfreq, amp, SR, positive=True):
    """
    Function which makes the I component of a single sideband with a gaussan
    envelope

    Args:
        sampling_rate
        sigma
        sigma_cutoff
        SSBfreq
        amp (default 1)
    """
    t = np.linspace(-1 * sigma_cutoff * sigma, sigma_cutoff *
                    sigma, num=int(np.round(SR * 2 * sigma_cutoff * sigma)))
    prefactor = amp if positive else -1 * amp
    y = prefactor * np.exp(-(t / (2 * sigma))**2) * \
        np.cos(2 * np.pi * SSBfreq * t)
    return y


def cos_gaussian_multi_array(sigma, sigma_cutoff, SSBfreq_list, amp, SR,
                             positive=True):
    points = int(np.round(SR * 2 * sigma_cutoff * sigma))
    t = np.linspace(-1 * sigma_cutoff * sigma, sigma_cutoff *
                    sigma, num=points)
    prefactor = amp if positive else -1 * amp
    y = np.zeros(points)
    for i, SSBfreq in enumerate(SSBfreq_list):
        y += prefactor * np.exp(-(t / (2 * sigma))**2) * \
            -np.cos(2 * np.pi * SSBfreq * t)
    return y / len(SSBfreq_list)


def sin_gaussian_array(sigma, sigma_cutoff, SSBfreq, amp, SR, positive=True):
    """
    Function which makes the Q component of a single sideband with a gaussan
    envelope

    Args:
        sampling_rate
        sigma
        sigma_cutoff
        SSBfreq
        amp (default 1)
    """
    t = np.linspace(-1 * sigma_cutoff * sigma, sigma_cutoff *
                    sigma, num=int(np.round(SR * 2 * sigma_cutoff * sigma)))
    prefactor = amp if positive else -1 * amp
    y = prefactor * np.exp(-(t / (2 * sigma))**2) * \
        -np.sin(2 * np.pi * SSBfreq * t)
    return y


def sin_gaussian_multi_array(sigma, sigma_cutoff, SSBfreq_list, amp, SR,
                             positive=True):
    points = int(np.round(SR * 2 * sigma_cutoff * sigma))
    t = np.linspace(-1 * sigma_cutoff * sigma, sigma_cutoff *
                    sigma, num=points)
    prefactor = amp if positive else -1 * amp
    y = np.zeros(points)
    for i, SSBfreq in enumerate(SSBfreq_list):
        y += prefactor * np.exp(-(t / (2 * sigma))**2) * \
            -np.sin(2 * np.pi * SSBfreq * t)
    return y / len(SSBfreq_list)


def ramp_array(start, stop, dur, SR):
    points = int(np.round(SR * dur))
    return np.linspace(start, stop, points)


def flat_array(amp, dur, SR):
    points = int(np.round(SR * dur))
    return amp * np.ones(points)


def gaussian_derivative_array(sigma, sigma_cutoff, amp, SR, positive=True):
    points = int(np.round(SR * 2 * sigma_cutoff * sigma))
    t = np.linspace(-1 * sigma_cutoff * sigma, sigma_cutoff * sigma,
                    num=points)
    prefactor = amp if positive else -1 * amp
    return prefactor * t / sigma * np.exp(-(t / (2 * sigma))**2)


def cos_array(freq, amp, dur, SR, positive=True):
    points = int(np.round(SR * dur))
    t = np.linspace(0, dur, num=points)
    angle = t * freq * 2 * np.pi
    prefactor = amp if positive else -1 * amp
    return prefactor * np.cos(angle)


def cos_multi_array(freq_list, amp, dur, SR, positive=True):
    points = int(np.round(SR * dur))
    t = np.linspace(0, dur, num=points)
    y = np.zeros(points)
    prefactor = amp if positive else -1 * amp
    for i, freq in enumerate(freq_list):
        angle = t * freq * 2 * np.pi
        y += prefactor * np.cos(angle)
    return y / len(freq_list)


def sin_array(freq, amp, dur, SR, positive=True):
    points = int(np.round(SR * dur))
    t = np.linspace(0, dur, num=points)
    angle = t * freq * 2 * np.pi
    prefactor = amp if positive else -1 * amp
    return prefactor * np.sin(angle)


def sin_multi_array(freq_list, amp, dur, SR, positive=True):
    points = int(np.round(SR * dur))
    t = np.linspace(0, dur, num=points)
    y = np.zeros(points)
    prefactor = amp if positive else -1 * amp
    for i, freq in enumerate(freq_list):
        angle = t * freq * 2 * np.pi
        y += prefactor * np.sin(angle)
    return y / len(freq_list)
