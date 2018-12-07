from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateParameter
from qdev_wrappers.customised_instruments.spectrum_analyser_calibration.base import SpectrumAnalyserCalibrator


class Pump_Calibrator(SpectrumAnalyserCalibrator):
    def __init__(self, name, spectrum_analyser_interface,
                 pump_source_interface, signal_source_interface):
        super().__init__(name, spectrum_analyser_interface)
        self.signal_frequency._source = signal_source_interface.frequency
        self.add_parameter(name='signal_power',
                           label='Signal Power',
                           unit='dBm',
                           source=signal_source_interface.power,
                           parameter_class=DelegateParameter)
        self.add_parameter(name='pump_power',
                           label='Pump Power',
                           unit='dBm',
                           source=pump_source_interface.power,
                           parameter_class=DelegateParameter)
        self.add_parameter(name='pump_frequency',
                           label='Pump Frequency',
                           unit='Hz',
                           source=pump_source_interface.frequency,
                           parameter_class=DelegateParameter)
        self.add_parameter(name='pump_status',
                           label='Pump Status',
                           source=pump_source_interface.frequency,
                           parameter_class=DelegateParameter)
        self.add_parameter(name='measure_gain',
                           label='Gain',
                           unit='dB',
                           get_cmd=self._measure_gain)
        self.add_parameter(name='measure_off_SNR',
                           label='SNR with Pump off',
                           unit='dB',
                           get_cmd=self._measure_off_SNR)
        self.add_parameter(name='measure_on_SNR',
                           label='SNR with Pump on',
                           unit='dB',
                           get_cmd=self._measure_on_SNR)
        self.add_parameter(name='measure_SNR_improvement',
                           label='SNR improvement',
                           unit='dB',
                           get_cmd=self._measure_SNR_improvement)

    def _measure_gain(self):
        self.pump_status(0)
        off_signal = self.measure_at_frequency(self.signal_frequency())
        self.pump_status(1)
        on_signal = self.measure_at_frequency(self.signal_frequency())
        return on_signal - off_signal

    def _measure_off_SNR(self):
        self.pump_status(0)
        return self.measure_SNR()

    def _measure_on_SNR(self):
        self.pump_status(1)
        return self.measure_SNR()

    def _measure_SNR_improvement(self):
        on_SNR = self.measure_on_SNR()
        off_SNR = self.measure_off_SNR()
        return on_SNR - off_SNR
