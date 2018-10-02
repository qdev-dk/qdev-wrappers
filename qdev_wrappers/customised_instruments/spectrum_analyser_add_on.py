from qcodes import Instrument
from functools import partial

class SpectrumAnalyserSidebandingHelper(Instrument):
    def __init__(self, spectrum_analyser, carrier_frequency, sideband_frequency):
        self.spectrum_analyser = spectrum_analyser
        super().__init__('spectrum_analyser_helper')
        self.add_parameter('carrier_frequency',
                            set_cmd=None,
                            unit='Hz',
                            label='Carrier Frequency',
                            initial_value=carrier_frequency)
        self.add_parameter('sideband_frequency',
                            set_cmd=None,
                            unit='Hz',
                            label='Sideband Frequency',
                            initial_value=sideband_frequency)
        self.add_parameter('upper_sideband_frequency',
                            unit='Hz',
                            label='Upper Sideband Frequency',
                            get_cmd=partial(self._get_sideband_frequency, 'upper'))
        self.add_parameter('lower_sideband_frequency',
                            unit='Hz',
                            label='Lower Sideband Frequency',
                            get_cmd=partial(self._get_sideband_frequency, 'lower'))
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

    def _get_sideband_frequency(self, sideband):
        if sideband == 'upper':
            return self.carrier_frequency() + self.sideband_frequency()
        elif sideband == 'lower':
            return self.carrier_frequency() - self.sideband_frequency()

    def _get_power_at_frequency(self, frequency_param):
        self.spectrum_analyser.frequency(frequency_param())
        return self.spectrum_analyser.power()

    def _get_power_difference(self, frequency_param1, frequency_param2):
        power1 = self._get_power_at_frequency(frequency_param1)
        power2 = self._get_power_at_frequency(frequency_param2)
        return power1 - power2