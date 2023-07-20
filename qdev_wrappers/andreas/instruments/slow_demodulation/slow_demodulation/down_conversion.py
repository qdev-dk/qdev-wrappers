"""
This module provides the all the math required for the `DownConverter` module.
"""

import numpy as np


def downconvert(
    time_trace: np.ndarray,
    sample_rate: float,
    frequency: float
):
    """Down-convert input signal.

    Multiplies the input with sines and cosines of given frequency,
    averages result and returns complex number whose real part is
    the average result of the cosine demodulation and whose imaginary
    part is the result of the sine demodulation.

    Args:
        time_trace: input_signal to be down-converted
        sample_rate: sample rate of `time_trace`
        frequency: single frequency at which to be demodulated

    Returns:
        complex number representing the magnitude and phase for the
        given frequency component in the input signal.

    """
    assert len(time_trace.shape) == 1
    n_samples = len(time_trace)
    duration = n_samples / sample_rate
    t = np.linspace(0, duration, n_samples, endpoint=False)
    sine = 1 * np.sin(frequency * t, dtype=np.dtype('float32'))
    cosine = 1 * np.cos(frequency * t, dtype=np.dtype('float32'))
    imag = 2 * np.average(np.multiply(time_trace, sine))
    real = 2 * np.average(np.multiply(time_trace, cosine))
    return real + 1j * imag
