import numpy as np
from lomentum.atoms import atom


@atom
def sidebanding_I(time, phase=0, offset=0, amplitudes=None, frequencies=None):
    if time.size == 1:
        return 0
    if frequencies is None:
        frequencies = [0]
    if amplitudes is None:
        amplitudes = [0]
    if len(frequencies) != len(amplitudes):
        raise RuntimeError(
            'Number of frequencies must match number of amplitudes:'
            ' {} != {}'.format(len(frequencies), len(amplitudes)))
    output = np.zeros(time.shape)
    for i, frequency in enumerate(frequencies):
        output += offset + amplitudes[i] * np.cos(
            frequency * 2 * np.pi * time + phase)
    return output / len(frequencies)


@atom
def sidebanding_Q(time, phase=0, offset=0, amplitudes=None, frequencies=None):
    if time.size == 1:
        return 0
    if frequencies is None:
        frequencies = [0]
    if amplitudes is None:
        amplitudes = [0]
    if len(frequencies) != len(amplitudes):
        raise RuntimeError(
            'Number of frequencies must match number of amplitudes:'
            ' {} != {}'.format(len(frequencies), len(amplitudes)))
    output = np.zeros(time.shape)
    for i, frequency in enumerate(frequencies):
        output += offset + amplitudes[i] * np.sin(
            frequency * 2 * np.pi * time + phase)
    return output / len(frequencies)


@atom
def gaussianDRAG(time, sigma_cutoff=4, amplitude=1, DRAG=False):
    sigma = time[-1] / (2 * sigma_cutoff)
    t = time - time[-1] / 2
    if DRAG:
        return amplitude * t / sigma * np.exp(-(t / (2. * sigma))**2)
    else:
        return amplitude * np.exp(-(t / (2. * sigma))**2)
