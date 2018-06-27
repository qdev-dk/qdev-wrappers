from qcodes.instrument_drivers.stanford_research.SR860 import SR860

class SR860_ext(SR860):
    """
    The SR860 instrument is almost equal to the SR865, except for the max frequency
    """
    def __init__(self, name: str, address: str, **kwargs: str) ->None:
        super().__init__(name, address, **kwargs)

       	self.add_parameter(name='iv_gain',
                           label='I/V Gain',
                           unit='',
                           set_cmd=lambda x: x,
                           get_parser=float)

       	self.add_parameter(name='conductance',
                           label='Conductance',
                           unit='2e^2/h',
                           get_cmd=self._get_conductance,
                           get_parser=float)

       	self.add_parameter(name='resistance',
                           label='Resistance',
                           unit='Ω',
                           get_cmd=self._get_resistance,
                           get_parser=float)

    def _get_conductance(self):
        V = self.amplitude.get_latest()
        I = self.X()/self.iv_gain.get_latest()
        conductance_quantum = 7.7480917310e-5
        return (I/V)/conductance_quantum

    def _get_resistance(self):
        V = self.amplitude.get_latest()
        I = self.X()/self.iv_gain.get_latest()
        return (V/I)


"""
Voltage division on input to fridge is added as scale factor to self.amplitude.
Use negative I/V gain to account for sign change on voltage input on Basel current amplifier.

Example yaml file:
    lockin:
        driver: qdev_wrappers.customised_instruments.SR860_ext
        type: SR860_ext
        address: 'your address'
        parameters:
            amplitude: {scale: 100000, monitor: True}
            iv_gain: {initial_value: -0.000000001}
"""