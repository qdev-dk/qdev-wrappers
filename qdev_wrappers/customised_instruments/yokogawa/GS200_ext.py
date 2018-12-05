from qcodes.instrument_drivers.yokogawa.GS200 import GS200
from qcodes.utils import validators as vals


class GS200_ext(GS200):
    def __init__(self, name, address, config=None, **kwargs):
        super().__init__(name, address, **kwargs)

        # Set voltage and ramp limits from config
        self.config = config
        if config is not None:
            try:
                ramp_stepdelay = config.get(
                    'Yokogawa Ramp Settings', 'voltage').split(" ")
                ranges_minmax = config.get(
                    'Yokogawa Limits', 'voltage').split(" ")
            except KeyError as e:
                raise KeyError('Settings not found in config file. Check they '
                               'are specified correctly. {}'.format(e))
            self.voltage.set_step(int(ramp_stepdelay[0]))
            self.voltage.set_delay(int(ramp_stepdelay[1]))
            self.voltage.vals = vals.Numbers(
                int(ranges_minmax[0]), int(ranges_minmax[1]))
