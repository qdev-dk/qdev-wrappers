import time
# import datetime
from qcodes import Instrument


class TimeInstrument(Instrument):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        self.add_parameter('time',
                           unit='s',
                           get_cmd=time.time,
                           get_parser=float,
                           docstring='Timestamp based on number of seconds since epoch.')


    def get_idn(self):
        vendor = 'Time'
        model = '1.0'
        serial = None
        firmware = None
        return {'vendor': vendor, 'model': model,
                'serial': serial, 'firmware': firmware}
