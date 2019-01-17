import numpy as np
from qcodes.utils import validators as vals
from qcodes.instrument.base import Instrument
from functools import partial
import qcodes.utils.validators as vals
import os
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import (DelegateParameter,
DelegateArrayParameter)



class _SpectrumAnalyserInterface(Instrument):
    """
    Interface base class for the spectrum analyser which by default
    has only manual parameters and no parameter for measurment.
    """
    def __init__(self, name):
        super().__init__(name)
        self.add_parameter('frequency',
                           label='Frequency',
                           unit='Hz',
                           parameter_class=DelegateParameter)
        self.add_parameter(name='span',
                           label='Span',
                           unit='Hz',
                           parameter_class=DelegateParameter)
        self.add_parameter(name='bandwidth',
                           label='Bandwidth',
                           unit='Hz',
                           parameter_class=DelegateParameter)
        self.add_parameter(name='avg',
                           label='Number of Averages',
                           vals=vals.Ints(),
                           get_parser=int,
                           parameter_class=DelegateParameter)
        self.add_parameter(name='npts',
                           label='Number of Averages',
                           vals=vals.Ints(),
                           get_parser=int,
                           parameter_class=DelegateParameter)
        self.add_parameter(name='mode',
                           label='Mode',
                           vals=vals.Enum('trace', 'single'),
                           parameter_class=DelegateParameter)
        self.add_parameter(name='single',
                           label='Magnitude',
                           unit='dBm',
                           set_allowed=False,
                           parameter_class=DelegateParameter)
        self.add_parameter(name='trace',
                           label='Magnitude',
                           unit='dBm',
                           parameter_class=DelegateArrayParameter)
        self.mode._save_val('trace')

    def _update_for_trace(self, **kwargs):
        """
        To be implemented in base class. Called when measurement
        parameters are gotten.
        """
        raise NotImplementedError


class USB_SA124BSpectrumAnalyserInterface(_SpectrumAnalyserInterface):
    """
    'Real' instrument implementation of the spectrum analyser interface.
    Main advantage over the instrument itself is that it updates the trace
    and configures when the measurement parameters 'trace' or 'single'
    are called so it doesn't need to be done by hand. Also switches the mode
    so that the span and bandwidth parameters are only implemented when
    the mode is 'trace' or if the 'trace' parameters are called. Otherwise
    these are both set to the minimum as required to get the 'single'
    parameter.
    """
    def __init__(self, name, spectrum_analyser):
        self._spectrum_analyser = spectrum_analyser
        super().__init__(name)
        self.frequency.source = spectrum_analyser.frequency
        self.avg.source = spectrum_analyser.avg
        self.avg()
        self.span.set_fn = partial(
            self._set_mode_dependent_param, 'span')
        self.span._save_val(spectrum_analyser.span())
        self.bandwidth.set_fn = partial(
            self._set_mode_dependent_param, 'rbw')
        self.bandwidth._save_val(spectrum_analyser.rbw())
        self.npts.set_fn = False
        self.npts.get_fn = self._get_npts
        self.npts()
        self.mode.set_fn = self._set_mode
        self.mode.get_fn = self._get_mode
        mode_docstring = ("If set to 'trace' sets the bandwidth and "
                          "span of the instrument to match the parameter "
                          "values. If set to 'single' set them to their "
                          "minimum values for a single point measurement.")
        self.mode.__doc__ = os.linesep.join(
            (mode_docstring, '', self.mode.__doc__))
        self.trace.source = spectrum_analyser.trace
        self.trace.get_fn = self.instrument._update_for_trace
        self.single.source = self._spectrum_analyser.power
        self.add_parameter('sleep_time',
                           source=spectrum_analyser.sleep_time,
                           parameter_class=DelegateParameter)

    def _get_npts(self):
        return self._spectrum_analyser.QuerySweep()[0]

    def _set_mode(self, val):
        if val == 'single':
            # TODO make model dependent/configurable
            self._spectrum_analyser.span(0.25e6)
            self._spectrum_analyser.rbw(1e3)
        else:
            self._spectrum_analyser.span(self.span())
            self._spectrum_analyser.rbw(self.bandwidth())

    def _get_mode(self):
        if (self._spectrum_analyser.span() == 0.25e6 and
                self._spectrum_analyser.rbw() == 1e3):
            return 'single'
        else:
            return 'trace'

    def _set_mode_dependent_param(self, param, val):
        if self.mode() == 'trace':
            self._spectrum_analyser.parameters[param].set(val)

    def _update_for_trace(self, name=False, **kwargs):
        if self.mode() != name:
            self._set_mode(name)
        if (not self._spectrum_analyser._parameters_synced or
                not self._spectrum_analyser._trace_updated):
            self._spectrum_analyser.configure()


class SimulatedSpectrumAnalyserInterface(_SpectrumAnalyserInterface):
    """
    Simulated instrument implementation of the spectrum analyser interface.
    The 'trace' and 'single' parameters return a random trace or point.
    """
    def __init__(self, name):
        super().__init__(name)
        self.npts.set_fn = self._set_npts
        self.bandwidth.set_fn = self._set_bandwidth
        self.span.set_fn = self._set_span
        self.trace.setpoint_units = ('Hz',)
        self.trace.setpoint_labels = ('Frequency',)
        self.trace.setpoint_names = ('frequency',)
        self.trace.get_fn = self._get_simulated_trace
        self.single.get_fn = self._get_simulated_single
        self.npts._latest['raw_value'] = 100
        self.avg._latest['raw_value'] = 1
        self.span._latest['raw_value'] = 10e6
        self.bandwidth._latest['raw_value'] = 100e3
        self.frequency._latest['raw_value'] = 5e9

    def _set_npts(self, val):
        self.bandwidth._latest['raw_value'] = self.span() / val

    def _set_span(self, val):
        self.bandwidth._latest['raw_value'] = val / self.npts()

    def _set_bandwidth(self, val):
        self.npts._latest['raw_value'] = self.span() / val

    def _get_simulated_single(self):
        self.mode('single')
        return np.random.random()

    def _get_simulated_trace(self):
        self.mode('trace')
        start_freq = self.frequency() - self.span() / 2
        stop_freq = self.frequency() + self.span() / 2
        npts = self.npts()
        freq_points = tuple(np.linspace(start_freq, stop_freq, npts))
        self.trace.shape = (npts, )
        self.trace.setpoints = (freq_points,)
        return np.random.random(int(npts))

