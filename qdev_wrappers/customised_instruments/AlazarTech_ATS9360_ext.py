from qcodes.instrument_drivers.AlazarTech.ATS9360 import AlazarTech_ATS9360
from qcodes.utils import validators as vals


class AlazarTech_ATS9360_ext(AlazarTech_ATS9360):
    def __init__(self, name, **kwargs):
        super().__init__(name=name, **kwargs)
        self.add_parameter(name='seq_mode',
                           get_cmd=self._get_seq_mod,
                           set_cmd=self._set_seq_mode,
                           vals=vals.Enum('on', 'off', True, False, 1, 0))

    def _get_seq_mod(self):
        if (self.aux_io_mode() == 'AUX_IN_TRIGGER_ENABLE' and
                self.aux_io_param() == 'TRIG_SLOPE_POSITIVE'):
            return True
        elif (self.aux_io_mode() == 'AUX_IN_AUXILIARY' and
              self.aux_io_param() == 'NONE'):
            return False
        else:
            raise ValueError('aux_io_mode: {}, aux_io_param: {} '
                             'do not correspond to seq_mode on or off')

    def _set_seq_mode(self, mode):
        if str(mode).upper() in ['1', 'ON', 'TRUE']:
            self.aux_io_mode('AUX_IN_TRIGGER_ENABLE')
            self.aux_io_param('TRIG_SLOPE_POSITIVE')
        elif str(mode).upper() in ['0', 'OFF', 'FALSE']:
            self.aux_io_mode('AUX_IN_AUXILIARY')
            self.aux_io_param('NONE')
        else:
            raise ValueError(
                'Unable to set seq_mode to {} '
                'expected "ON"/1/True or "OFF"/0/False.'.format(mode))
        self.sync_settings_to_card()
