from qcodes.instrument_drivers.USB_SA124B import SignalHound_USB_SA124B
from functools import partial

class SpectrumAnalyser_ext(SignalHound_USB_SA124B):
    def __init__(self, name, dll_path=None):
        super().__init__(name, dll_path=dll_path)
        self.add_parameter('carrier_frequency',
                            set_cmd=None,
                            unit='Hz',
                            label='Carrier Frequency')
        self.add_parameter('sideband_frequency',
                            set_cmd=self._set_sideband_frequency,
                            label='Sideband Frequency')
        self.add_parameter('upper_sideband_frequency',
                            unit='Hz',
                            label='Upper Sideband Frequency')
        self.add_parameter('lower_sideband_frequency',
                            unit='Hz',
                            label='Lower Sideband Frequency')
        self.add_parameter('upper_sideband_power',
                            unit='dBm',
                            label='Upper Sideband Power',
                            get_cmd=partial(self._get_power_at_frequency, self.upper_sideband_frequency))
        self.add_parameter('lower_sideband_power',
                            unit='dBm',
                            label='Lower Sideband Power',
                            get_cmd=partial(self._get_power_at_frequency, self.lower_sideband_frequency))
        self.add_parameter('carrier_power',
                            unit='dBm',
                            label='Carrier Power',
                            get_cmd=partial(self._get_power_at_frequency, self.carrier_frequency))
        self.add_parameter('upper_lower_sideband_difference',
                            unit='dBm',
                            label='Upper Lower Sideband Difference',
                            get_cmd=partial(self._get_power_difference, self.upper_sideband_frequency, self.lower_sideband_frequency))
        self.add_parameter('upper_sideband_carrier_difference',
                            unit='dBm',
                            label='Upper Sideband Carrier Difference',
                            get_cmd=partial(self._get_power_difference, self.upper_sideband_frequency, self.carrier_frequency))
        self.add_parameter('lower_sideband_carrier_difference',
                            unit='dBm',
                            label='Lower Sideband Carrier Difference',
                            get_cmd=partial(self._get_power_difference, self.lower_sideband_frequency, self.carrier_frequency))            

    def _set_sideband_frequency(self, sideband):
        self.upper_sideband_frequency._save_val(self.carrier_frequency() + sideband)
        self.lower_sideband_frequency._save_val(self.carrier_frequency() - sideband)

    def _get_power_at_frequency(self, frequency_param):
        self.frequency(frequency_param())
        return self.power()

    def _get_power_difference(self, frequency_param1, frequency_param2):
        power1 = self._get_power_at_frequency(frequency_param1)
        power2 = self._get_power_at_frequency(frequency_param2)
        return power1 - power2