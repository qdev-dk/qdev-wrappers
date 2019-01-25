from qcodes.instrument_drivers.stanford_research.SR830 import SR830, ChannelBuffer

# A conductance buffer, needed for the faster 2D conductance measurements
# (Dave Wecker style)

class ConductanceBuffer(ChannelBuffer):
    """
    A full-buffered version of the conductance based on an
    array of X measurements

    We basically just slightly tweak the get method
    """

    def __init__(self, name: str, instrument: 'SR830', **kwargs):
        super().__init__(name, instrument, channel=1)
        self.unit = ('e$^2$/h')

    def get(self):
        # If X is not being measured, complain
        if self._instrument.ch1_display() != 'X':
            raise ValueError('Can not return conductance since X is not '
                                'being measured on channel 1.')

        resistance_quantum = 25.818e3  # (Ohm)
        xarray = super().get()
        iv_conv = self._instrument.iv_gain()
        ac_excitation = self._instrument.amplitude.get_latest()

        gs = xarray / iv_conv / ac_excitation * resistance_quantum

        return gs

class ResistanceBuffer(ChannelBuffer):
    """
    A full-buffered version of the current biased resistance based on an
    array of X measurements

    We basically just slightly tweak the get method
    """

    def __init__(self, name: str, instrument: 'SR830', **kwargs):
        super().__init__(name, instrument, channel=1)
        self.unit = ('Ohm')

    def get(self):
        # If X is not being measured, complain
        if self._instrument.ch1_display() != 'X':
            raise ValueError('Can not return conductance since X is not '
                                'being measured on channel 1.')

        xarray = super().get()
        v_conv = self._instrument.v_gain()
        ac_excitation = self._instrument.amplitude.get_latest()

        rs = xarray / v_conv / ac_excitation

        return rs


# Subclass the SR830

class SR830_ext(SR830):
    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, **kwargs)

        self.add_parameter(name='iv_gain',
                            label='I/V Gain',
                            unit='',
                            set_cmd=lambda x: x,
                            get_parser=float,
                            docstring='Gain of transimpedance preamplifier')

        self.add_parameter(name='v_gain',
                            label='V Gain',
                            unit='',
                            set_cmd=lambda x: x,
                            get_parser=float,
                            docstring='Gain of voltage preamplifer')        

        self.add_parameter(name='g',
                            label='Conductance',
                            unit='e$^2$/h',
                            get_cmd=self._get_conductance,
                            get_parser=float)

        self.add_parameter(name='resistance',
                            label='Resistance',
                            unit='Ohm',
                            get_cmd=self._get_resistance,
                            get_parser=float)
        
        self.add_parameter(name='g_X',
                            label='Conductance X',
                            unit='e$^2$/h',
                            get_cmd=self._get_conductance_X,
                            get_parser=float)

        self.add_parameter(name='resistance_X',
                            label='Resistance X',
                            unit='Ohm',
                            get_cmd=self._get_resistance_X,
                            get_parser=float)

        self.add_parameter(name='resistance_i_bias',
                            label='Resistance_I_bias',
                            unit='Ohm',
                            get_cmd=self._get_resistance_i_bias,
                            get_parser=float,
                            docstring='Resistance assuming current bias with AC'
                                ' current sourced from the lockin')

        self.add_parameter(name='g_buff',
                            label='Conductance',
                            parameter_class = ConductanceBuffer)

        self.add_parameter(name='r_buff',
                            label='Resistance',
                            parameter_class = ResistanceBuffer)

    def _get_conductance(self):
        V = self.amplitude.get_latest()
        I = abs(self.R()/self.iv_gain.get_latest())
        conductance_quantum = 7.7480917310e-5
        return (I/V)/(conductance_quantum/2)

    def _get_resistance(self):
        V = self.amplitude.get_latest()
        I = abs(self.R()/self.iv_gain.get_latest())
        return (V/I)

    def _get_conductance_X(self):
        V = self.amplitude.get_latest()
        I = self.X()/self.iv_gain.get_latest()
        conductance_quantum = 7.7480917310e-5
        return (I/V)/(conductance_quantum/2)

    def _get_resistance_X(self):
        V = self.amplitude.get_latest()
        I = self.X()/self.iv_gain.get_latest()
        return (V/I)

    def _get_resistance_i_bias(self):
        I = self.amplitude.get_latest()
        V = self.X()/self.v_gain.get_latest()
        return (V/I)


"""
Voltage division on input to fridge is added as scale factor to self.amplitude.
Use negative I/V gain to account for sign change on voltage input on Basel current amplifier.
To take the new scale into account we also need to change the limits on the amplitude.

Example yaml file:
    lockin:
        driver: qdev_wrappers.customised_instruments.SR830_ext
        type: SR830_ext
        address: 'your address'
        parameters:
            amplitude: {scale: 100000, limits: '4e-8,5e-5', monitor: true}
            iv_gain: {initial_value: -10000000}
"""