from qcodes.instrument_drivers.stanford_research.SR86x import SR86x

class SR86x_ext(SR86x):
    def __init__(self, name, address, max_frequency, reset=False, **kwargs) ->None:
        super().__init__(name, address, max_frequency, reset, **kwargs)

       	self.add_parameter(name='iv_gain',
                           label='I/V Gain',
                           unit='',
                           set_cmd=lambda x: x,
                           get_parser=float)

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


class SR860_ext(SR86x_ext):
    """
    The SR860 instrument is almost equal to the SR865, except for the max frequency
    """
    def __init__(self, name: str, address: str, reset: bool=False, **kwargs: str) ->None:
        super().__init__(name, address, max_frequency=500E3, reset=reset, **kwargs)


"""
Voltage division on input to fridge is added as scale factor to self.amplitude.
Use negative I/V gain to account for sign change on voltage input on Basel current amplifier.
To take the new scale into account we also need to change the limits on the amplitude.

Example yaml file:
    lockin:
        driver: qdev_wrappers.customised_instruments.SR86x_ext
        type: SR860_ext
        address: 'your address'
        parameters:
            amplitude: {scale: 1e5, limits: '0,2e-5',monitor: true}
            iv_gain: {initial_value: -1e7}
"""