from qcodes.instrument_drivers.tektronix.AWG5014 import Tektronix_AWG5014
from qcodes import ManualParameter
from qcodes.utils import validators as vals


class AWG5014_ext(Tektronix_AWG5014):
    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, **kwargs)
        self.add_parameter(name='current_seq',
                           parameter_class=ManualParameter,
                           initial_value=None,
                           label='Uploaded sequence index',
                           vals=vals.Ints())
        self.add_parameter(name='seq_mode',
                           set_cmd=self._set_seq_mode,
                           get_cmd=self._get_seq_mode)
        self.clear_message_queue()

    def _set_seq_mode(self, status):
        if str(status).upper() in ['TRUE', '1', 'ON']:
            for i in range(self.sequence_length()):
                self.set_sqel_loopcnt(i, 1)
        elif str(status).upper() in ['FALSE', '0', 'OFF']:
            for i in range(self.sequence_length()):
                self.set_sqel_loopcnt_to_inf(i)

    def _get_seq_mode(self):
        if self.sequence_length() > 1:
            return self.get_sqel_loopcnt() != '1'
        else:
            return False

    def send_and_load_awg_file(self, awg_file, filename):
        self.visa_handle.write('MMEMory:CDIRectory ' +
                               '"C:\\Users\\OEM\\Documents"')

        self.send_awg_file(filename, awg_file)
        currentdir = self.visa_handle.query('MMEMory:CDIRectory?')
        currentdir = currentdir.replace('"', '')
        currentdir = currentdir.replace('\n', '\\')
        loadfrom = '{}{}'.format(currentdir, filename)
        self.load_awg_file(loadfrom)
