from qcodes import Instrument
from qcodes.instrument.parameter import MultiParameter, StandardParameter
from qcodes.instrument.parameter import ManualParameter
from qcodes.utils.validators import Enum, Bool

class Current_preamplifier(Instrument):
    """
    This is the qcodes driver for a general Current-preamplifier.

    This is a virtual driver only and will not talk to your instrument.
    """
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        self.add_parameter('gain',
                           parameter_class=ManualParameter,
                           initial_value=1e-8,
                           label='Sensitivity',
                           unit='A/V',
                           vals=Enum(1e-11, 1e-10, 1e-09, 1e-08, 1e-07,
                                     1e-06, 1e-05, 1e-4, 1e-3))

        self.add_parameter('invert',
                           parameter_class=ManualParameter,
                           initial_value=True,
                           label='Inverted output',
                           vals=Bool())


    def get_idn(self):
        vendor = 'General Current Preamplifier'
        model = None
        serial = None
        firmware = None
        return {'vendor': vendor, 'model': model,
                'serial': serial, 'firmware': firmware}
