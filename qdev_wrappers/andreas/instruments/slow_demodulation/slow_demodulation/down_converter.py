"""
This module provides the `DownConverter` QCoDeS-instrument.

It enables the down conversion of a time trace parameter at given frequencies.
"""

from typing import Optional

import numpy as np

from qcodes.instrument.base import Instrument
from qcodes.instrument.parameter import (
    ParameterWithSetpoints, Parameter, _BaseParameter)
import qcodes.utils.validators as validators

from .down_conversion import downconvert


class DownConversionParameter(ParameterWithSetpoints):
    """ Downconvert Signal."""

    def __init__(
        self, name, *,
        demodulation_frequencies: _BaseParameter,
        vals=None,
        snapshot_get=False,
        snapshot_value=False,
        source: ParameterWithSetpoints,
        **kwargs
    ):
        self.source = source
        assert isinstance(demodulation_frequencies.vals, validators.Arrays)
        super().__init__(
            name,
            vals=validators.Arrays(
                shape=demodulation_frequencies.vals.shape_unevaluated,
                valid_types=(np.complexfloating,)
            ),
            setpoints=(demodulation_frequencies,),
            snapshot_get=snapshot_get,
            snapshot_value=snapshot_value,
            **kwargs)

    def get_raw(self) -> np.ndarray:
        freqs = self.setpoints[0].get_latest()
        time_trace = self.source.get()
        result = [
            downconvert(time_trace, self.instrument.sample_rate(), f)
            for f in list(freqs)
        ]
        return np.array(result)


class DownConverter(Instrument):
    """QCoDeS Instrument for downconversion at given freuencies.

    This instrument exposes the parameter `down_converted_signal`,
    which returns a numpy array of complex numbers, resulting from
    demodulating the input signal `source_parameter` at the given
    frequencies `demodulation_frequencies` and subsequent averaging,
    so that there is a complex coefficient for each demodulation
    frequency.
    """
    
    def __init__(
        self, name: str,
        source_parameter: ParameterWithSetpoints,
        sample_rate: float,
        metadata: Optional[dict] = None,
    ):
        """Create a `DownConverter` Instrument.

        Use `set_demodulation_frequencies` instead of parameter!

        Args:
            name: QCoDeS name of the instrument
            source_parameter: QCoDeS parameter that returns a 1d numpy array,
                which gets down converted.
            sample_rate: the sample rate corresponding to the signal delivered
                by `source_parameter`
            metadata: additional metadata, see `Instrument`

        """
        super().__init__(name, metadata)

        self.add_parameter(
            name='sample_rate',
            parameter_class=Parameter,
            vals=validators.Numbers(min_value=0),
            initial_value=sample_rate,
            set_cmd=None,
            get_cmd=None)

        self.add_parameter(
            name='_n_freqs',
            parameter_class=Parameter,
            vals=validators.Ints(min_value=0),
            initial_value=0,
            set_cmd=None,
            get_cmd=None)

        self.add_parameter(
            name='demodulation_frequencies',
            parameter_class=Parameter,
            vals=validators.Arrays(
                shape=(lambda: self._n_freqs(),)
            ),
            initial_value=np.zeros(0),
            set_cmd=None,
            get_cmd=None)

        self.add_parameter(
            name='down_converted_signal',
            parameter_class=DownConversionParameter,
            source=source_parameter,
            demodulation_frequencies=self.demodulation_frequencies)

    def set_demodulation_frequencies(self, val: np.ndarray) -> None:
        """Use this method instead of the parameter to set demodulation freqs."""
        self._n_freqs(len(val))
        self.demodulation_frequencies(val)



