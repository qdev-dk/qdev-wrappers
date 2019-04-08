import numpy as np
from broadbean.atoms import atom


@atom
def sine_multi(time, frequencies=None, amplitudes=1, phases=0):
    if time.size == 1:
        return 0
    if frequencies is None:
        frequencies = [0]
    if type(amplitudes) in [int, float]:
        amplitudes = np.ones(len(frequencies)) * amplitudes
    if type(phases) in [int, float]:
        phases = np.ones(len(frequencies)) * phases
    if not (len(frequencies) == len(amplitudes) and
            len(frequencies) == len(phases)):
        raise Exception(
            '{} frequencies, {} amplitudes and {} phases provided'.format(
                len(frequencies), len(amplitudes), len(phases)))
    output = np.zeros(time.shape)
    for i, frequency in enumerate(frequencies):
        output += amplitudes[i] * \
            np.sin(frequency * 2 * np.pi * time + phases[i])
    return output / len(frequencies)


@atom
def gaussianDRAG(time, sigma_cutoff=4, amplitude=1, DRAG=False):
    sigma = time[-1] / (2 * sigma_cutoff)
    t = time - time[-1] / 2
    if DRAG:
        return amplitude * t / sigma * np.exp(-(t / (2. * sigma))**2)
    else:
        return amplitude * np.exp(-(t / (2. * sigma))**2)
