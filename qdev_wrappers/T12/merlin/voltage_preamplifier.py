from qcodes import Instrument
from qcodes.instrument.parameter import ManualParameter
from qcodes.instrument.parameter import MultiParameter
from qcodes.utils.validators import Bool, Enum, Numbers



class Voltage_preamplifier(Instrument):
    """
    This is the qcodes driver for a general Voltage-preamplifier.

    This is a virtual driver only and will not talk to your instrument.

    Note:

    - The ``cutoff_lo`` and ``cutoff_hi`` parameters will interact with
      each other on the instrument (hi cannot be <= lo) but this is not
      managed here, you must ensure yourself that both are correct whenever
      you change one of them.

    - ``gain`` has a vernier setting, which does not yield a well-defined
      output. We restrict this driver to only the predefined gain values.

    """
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        mode = ['A-B', 'A GND' 'A Float']


        self.add_parameter('mode',
                           parameter_class=ManualParameter,
                           initial_value='A-B',
                           label='Mode',
                           vals=Enum(*mode))

        self.add_parameter('invert',
                           parameter_class=ManualParameter,
                           initial_value=False,
                           label='Inverted output',
                           vals=Bool())

        self.add_parameter('gain',
                           parameter_class=ManualParameter,
                           initial_value=100,
                           label='Gain',
                           unit=None,
                           vals=Numbers())

    def get_idn(self):
        vendor = 'General Voltage Preamplifier'
        model = None
        serial = None
        firmware = None

        return {'vendor': vendor, 'model': model,
                'serial': serial, 'firmware': firmware}
