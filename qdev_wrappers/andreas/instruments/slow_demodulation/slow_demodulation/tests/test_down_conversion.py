"""Tests for the `down_conversion` module.

Simple tests to verify that the actual calculation returns the expected
results.
"""


import numpy as np

from slow_demodulation.down_conversion import downconvert


def test_downconversion_of_sine():
    f = 2 * np.pi * 111.0
    sr = 100011.0
    t = np.linspace(0, 1, sr, endpoint=False)
    ret = downconvert(np.sin(f * t), sample_rate=sr, frequency=f)
    assert np.isclose(np.imag(ret), 1, atol=1e-2)
    assert np.isclose(np.real(ret), 0, atol=1e-2)


def test_downconversion_of_cosine():
    f = 2 * np.pi * 111.0
    sr = 100011
    t = np.linspace(0, 1, sr, endpoint=False)
    ret = downconvert(np.cos(f * t), sample_rate=sr, frequency=f)
    assert np.isclose(np.imag(ret), 0, atol=1e-2)
    assert np.isclose(np.real(ret), 1, atol=1e-2)


def test_downconversion_of_two_freqs():
    f = 2 * np.pi * 111.0
    sr = 100011
    t = np.linspace(0, 1, sr)
    ret = downconvert(
        np.cos(f * t) + np.sin(5 * f * t),
        sample_rate=sr, frequency=f)
    assert np.isclose(np.imag(ret), 0, atol=1e-2)
    assert np.isclose(np.real(ret), 1, atol=1e-2)
