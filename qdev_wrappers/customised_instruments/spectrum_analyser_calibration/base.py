from qcodes.instrument.base import Instrument
from qdev_wrappers.customised_instruments.interfaces.parameters import InterfaceParameter
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateParameter
from qdev_wrappers.customised_instruments.interfaces.spectrum_analyser_interface import DelegateTraceParameter, DelegatePowerParameter


class SpectrumAnalyserCalibrator(Instrument):
    def __init__(self, name, spectrum_analyser_interface):
        self._spectrum_analyser_interface = spectrum_analyser_interface
        super().__init__(name)
        self.add_parameter(name='signal_frequency',
                           label='Signal Frequency',
                           unit='Hz',
                           parameter_class=InterfaceParameter)
        self.add_parameter(name='measurement_span',
                           label='Measurement Span',
                           unit='Hz',
                           source=spectrum_analyser_interface.span,
                           parameter_class=DelegateParameter)
        self.add_parameter(name='measurement_bandwidth',
                           label='Measurement Bandwidth',
                           unit='Hz',
                           source=spectrum_analyser_interface.bandwidth,
                           parameter_class=DelegateParameter)
        self.add_parameter(name='measurement_frequency',
                           label='Measurement Frequency',
                           unit='Hz',
                           source=spectrum_analyser_interface.frequency,
                           parameter_class=DelegateParameter)
        self.add_parameter(name='measurement_avg',
                           label='Number of Averages',
                           source=spectrum_analyser_interface.avg,
                           parameter_class=DelegateParameter)
        self.add_parameter(name='noise_detuning',
                           label='Detuning for noise measurement',
                           units='Hz',
                           intial_value=5e6)
        self.add_parameter(name='measure_trace',
                           label='Magnitude',
                           unit='dBm',
                           source=spectrum_analyser_interface.trace,
                           parameter_class=DelegateTraceParameter)
        self.add_parameter(name='measure_single',
                           label='Magnitude',
                           unit='dBm',
                           source=spectrum_analyser_interface.single,
                           parameter_class=DelegatePowerParameter)
        self.add_parameter(name='measure_signal',
                           label='Signal at Sidebanded Frequency',
                           unit='dBm',
                           get_cmd=self._measure_signal)
        self.add_parameter(name='measure_noise',
                           label='Signal detuned from Sidebanded Frequency',
                           unit='dBm',
                           get_cmd=self._measure_noise)
        self.add_parameter(name='measure_SNR',
                           label='Signal to Noise Ratio',
                           unit='dB',
                           get_cmd=self._measure_snr)

    def _measure_signal(self):
        return self.measure_at_frequency(self.signal_frequency())

    def _measure_noise(self):
        return self.measure_at_frequency(
            self.signal_frequency() + self.noise_detuning())

    def _measure_snr(self):
        signal = self._measure_signal()
        noise = self._measure_noise()
        return signal - noise

    def measure_at_frequency(self, frequency):
        self.measurement_frequency(frequency)
        return self.measure_single()

    def _update_for_trace(self, **kwargs):
        self._spectrum_analyser._update_for_trace(**kwargs)


