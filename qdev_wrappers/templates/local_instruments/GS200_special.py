from qcodes.instrument_drivers.yokogawa.GS200 import GS200


class GS200_special(GS200):
    def __init__(self, name, address, initial_voltage=12.3, **kwargs):
        super().__init__(name, address, **kwargs)
        self.voltage(initial_voltage)
