from qcodes.instrument_drivers.tektronix.AWG5014 import Tektronix_AWG5014
from qcodes import ManualParameter
from qcodes.utils import validators as vals


class AWG5014_ext(Tektronix_AWG5014):
    def __init__(self, name, visa_address, **kwargs):
        super().__init__(name, visa_address, **kwargs)
        self.add_parameter(name='current_seq',
                           parameter_class=ManualParameter,
                           initial_value=None,
                           label='Uploaded sequence index',
                           vals=vals.Ints())
        self.ref_source('EXT')
        self.clear_message_queue()
