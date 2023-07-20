"""Tests for the `down_converter` module.

Test that the `DownConverter` instrument can be create, returns the expected
results, and can be used in a real measurement scenario.
"""

import numpy as np
import pytest

from qcodes.instrument.parameter import Parameter
from qcodes.tests.dataset.temporary_databases import empty_temp_db  # noqa
from qcodes import new_experiment
from qcodes.dataset.measurements import Measurement

from slow_demodulation.down_converter import DownConverter


class DummyArray(Parameter):
    def get_raw(self):
        npoints = 1000
        return np.random.rand(npoints)


@pytest.fixture
def dummy_demodulator():
    source = DummyArray('source')
    d = DownConverter(
        'test_demodulator',
        source_parameter=source,
        sample_rate=1000)
    try:
        yield d
    finally:
        d.close()


def test_creation(dummy_demodulator):
    pass


def test_settting_demod_freqs(dummy_demodulator):
    d = dummy_demodulator
    d.set_demodulation_frequencies(np.array([1, 2, 3]))
    assert np.allclose(d.demodulation_frequencies(), np.array([1, 2, 3]))


def test_getting_demod_signal(dummy_demodulator):
    d = dummy_demodulator
    d.set_demodulation_frequencies(np.array([1, 2, 3]))
    dcsig = d.down_converted_signal()
    assert dcsig.shape == (3,)


def test_correct_demod_signal():
    lo = 2 * np.pi * 111.0
    sample_rate = 100011

    class SineSourceParameter(Parameter):
        def get_raw(self):
            t = np.linspace(0, 1, sample_rate, endpoint=False)
            return np.sin(lo * t)

    d = DownConverter(
        'test_demodulator',
        source_parameter=SineSourceParameter('source'),
        sample_rate=sample_rate)
    try:
        d.set_demodulation_frequencies(np.array([lo, 2 * lo, 3 * lo]))

        dcsig = d.down_converted_signal()
        assert np.isclose(np.imag(dcsig[0]), 1, atol=1e-2)
        assert np.isclose(np.real(dcsig[0]), 0, atol=1e-2)
        assert np.isclose(np.imag(dcsig[1]), 0, atol=1e-2)
        assert np.isclose(np.real(dcsig[1]), 0, atol=1e-2)
        assert np.isclose(np.imag(dcsig[2]), 0, atol=1e-2)
        assert np.isclose(np.real(dcsig[2]), 0, atol=1e-2)
    finally:
        d.close()


@pytest.mark.usefixtures("empty_temp_db")
def test_in_measurement(dummy_demodulator):
    new_experiment(
        name='slow demodulation test',
        sample_name="test script sample")
    d = dummy_demodulator
    d.set_demodulation_frequencies(np.array([1, 2, 3]))
    meas = Measurement()
    meas.register_parameter(d.down_converted_signal)

    with meas.run() as datasaver:
        datasaver.add_result(
            (d.demodulation_frequencies, d.demodulation_frequencies()),
            (d.down_converted_signal, d.down_converted_signal())
        )
