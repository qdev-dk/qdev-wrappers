from qcodes.instrument_drivers.stanford_research.SR830 import SR830
from qcodes.instrument_drivers.devices import VoltageDivider
from qcodes.instrument_drivers.stanford_research.SR830 import ChannelBuffer

# A conductance buffer, needed for the faster 2D conductance measurements
# (Dave Wecker style)


class ConductanceBuffer(ChannelBuffer):
    """
    A full-buffered version of the conductance based on an
    array of X measurements

    We basically just slightly tweak the get method
    """

    def __init__(self, name: str, instrument: 'SR830_T10', **kwargs):
        super().__init__(name, instrument, channel=1)
        self.unit = ('e^2/h')

    def get(self):
        # If X is not being measured, complain
        if self._instrument.ch1_display() != 'X':
            raise ValueError('Can not return conductance since X is not '
                             'being measured on channel 1.')

        resistance_quantum = 25.818e3  # (Ohm)
        xarray = super().get()
        iv_conv = self._instrument.ivgain
        ac_excitation = self._instrument.amplitude_true()

        gs = xarray / iv_conv / ac_excitation * resistance_quantum

        return gs


# Subclass the SR830

class SR830_cQED(SR830):
    """
    An SR830 with the following super powers:
        - a Voltage divider
        - An I/V converter
        - A conductance buffer
    """

    def __init__(self, name, address, config, **kwargs):
        super().__init__(name, address, **kwargs)

        # using the vocabulary of the config file
        self.ivgain = float(config.get('Gain Settings',
                                       'iv gain'))
        self.__acf = float(config.get('Gain Settings',
                                      'ac factor'))

        self.add_parameter('amplitude_true',
                           label='ac bias',
                           parameter_class=VoltageDivider,
                           v1=self.amplitude,
                           division_value=self.acfactor)

        self.acbias = self.amplitude_true

        self.add_parameter('g',
                           label='{} conductance'.format(self.name),
                           # use lambda for late binding
                           get_cmd=self._get_conductance,
                           unit='e^2/h',
                           get_parser=float)

        self.add_parameter('conductance',
                           label='{} conductance'.format(self.name),
                           parameter_class=ConductanceBuffer)

        self.add_parameter('resistance',
                           label='{} Resistance'.format(self.name),
                           get_cmd=self._get_resistance,
                           unit='Ohm',
                           get_parser=float)

    def _get_conductance(self):
        """
        get_cmd for conductance parameter
        """
        resistance_quantum = 25.8125e3  # (Ohm)
        i = self.R() / self.ivgain
        # ac excitation voltage at the sample
        v_sample = self.amplitude_true()

        return (i / v_sample) * resistance_quantum

    def _get_resistance(self):
        """
        get_cmd for resistance parameter
        """
        i = self.R() / self.ivgain
        # ac excitation voltage at the sample
        v_sample = self.amplitude_true()

        return (v_sample / i)

    @property
    def acfactor(self):
        return self.__acf

    @acfactor.setter
    def acfactor(self, acfactor):
        self.__acf = acfactor
        self.amplitude_true.division_value = acfactor

    def snapshot_base(self, update=False, params_to_skip_update=None):
        if params_to_skip_update is None:
            params_to_skip_update = (
                'conductance', 'ch1_databuffer', 'ch2_databuffer')
        snap = super().snapshot_base(
            update=update, params_to_skip_update=params_to_skip_update)
        return snap
