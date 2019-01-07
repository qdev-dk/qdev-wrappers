import numpy as np
from qcodes.utils import validators as vals
from qcodes.instrument.base import Instrument
from functools import partial
import os
from qdev_wrappers.customised_instruments.interfaces.interface_parameter import InterfaceParameter
from qcodes.instrument.parameter import ArrayParameter
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateParameter, DelegateArrayParameter


class DelegateTraceParameter(DelegateArrayParameter):
    def get_raw(self):
        self.instrument._update_for_trace()
        return self.parent.get_raw()


class DelegatePowerParameter(DelegateParameter):
    def get_raw(self):
        self.instrument._update_for_trace(name=self.name)
        return self.parent.get_raw()


class SimulatedTraceParameter(ArrayParameter):
    def get_raw(self):
        start_freq = self.instrument.frequency() - self.instrument.span() / 2
        stop_freq = self.instrument.frequency() + self.instrument.span() / 2
        npts = self.instrument.npts()
        freq_points = tuple(np.linspace(start_freq, stop_freq, npts))
        self.shape = (npts, )
        self.setpoints = (freq_points,)
        self.instrument._trace_updated = True
        return np.random.random(npts)


class _SpectrumAnalyserInterface(Instrument):
    """
    Interface base class for the spectrum analyser which by default
    has only manual parameters and no parameter for measurment.
    """
    def _init__(self, name):
        super().__init__(name)
        self.add_parameter('frequency',
                           label='Frequency',
                           unit='Hz',
                           parameter_class=InterfaceParameter)
        self.add_parameter(name='span',
                           label='Span',
                           unit='Hz',
                           parameter_class=InterfaceParameter)
        self.add_parameter(name='bandwidth',
                           label='Bandwidth',
                           unit='Hz',
                           parameter_class=InterfaceParameter)
        self.add_parameter(name='avg',
                           label='Number of Averages',
                           parameter_class=InterfaceParameter)
        self.add_parameter(name='npts',
                           label='Number of Averages',
                           parameter_class=InterfaceParameter)
        self.add_parameter(name='mode',
                           label='Mode',
                           vals=vals.Enum('trace', 'single'),
                           parameter_class=InterfaceParameter)
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
        self.frequency._source = spectrum_analyser.frequency
        self.span._set_fn = partial(
            self._set_spectrum_analyser_param, 'span')
        self.span._save_val(spectrum_analyser.span())
        self.bandwidth._set_fn = partial(
            self._set_spectrum_analyser_param, 'rbw')
        self.bandwidth._save_val(spectrum_analyser.rbw())
        self.avg._source = spectrum_analyser.avg
        self.npts._set_fn = False
        self.npts._get_fn = self._get_npts
        self.mode._set_fn = self._set_mode
        self.mode._get_fn = self._get_mode
        mode_docstring = ("If set to 'trace' sets the bandwidth and "
                          "span of the instrument to match the parameter "
                          "values. If set to 'single' set them to their "
                          "minimum values for a single point measurement.")
        self.mode.__doc__ = os.linesep.join(
            (mode_docstring, '', self.mode.__doc__))
        self.add_parameter('sleep_time',
                           source=spectrum_analyser.sleep_time,
                           parameter_class=InterfaceParameter)
        self.add_parameter(
            name='trace',
            label='Magnitude',
            unit='dBm',
            source=spectrum_analyser.trace,
            parameter_class=DelegateTraceParameter)
        self.add_parameter(
            name='single',
            instrument=self,
            label='Magnitude',
            unit='dBm',
            source=self._spectrum_analyser.power,
            parameter_class=DelegateTraceParameter)

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

    def _set_spectrum_analyser_param(self, param, val):
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
        self.npts._set_fn = self._set_npts
        self.add_parameter(
            name='trace',
            unit='dBm',
            label='Magnitude',
            setpoint_units=('Hz',),
            setpoint_labels=('Frequency',),
            setpoint_names=('frequency',),
            parameter_class=SimulatedTraceParameter)
        self.add_parameter(
            name='single',
            unit='dBm',
            label='Magnitude',
            get_cmd=lambda: np.random.random())

    def _set_npts(self, val):
        self.bandwidth._save_val(self.span() / val)

    def _set_span(self, val):
        self.bandwidth._save_val(val / self.npts())

    def _set_bandwidth(self, val):
        self.npts._save_val(self.span() / val)
