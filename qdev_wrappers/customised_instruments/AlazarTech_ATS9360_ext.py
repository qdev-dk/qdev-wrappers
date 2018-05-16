from qcodes.instrument_drivers.AlazarTech.ATS9360 import AlazarTech_ATS9360
from qcodes.utils import validators as vals


class AlazarTech_ATS9360_ext(AlazarTech_ATS9360):
    def __init__(self, name, seq_mode='off'):
        if seq_mode == 'on':
            io_mode = 'AUX_IN_TRIGGER_ENABLE'
            io_param = 'TRIG_SLOPE_POSITIVE'
        elif seq_mode == 'off':
            io_mode = 'AUX_IN_AUXILIARY'
            io_param = 'NONE'
        else:
            raise ValueError('must set seq mode to "on" or '
                             '"off", received {}'.format(seq_mode))
        super().__init__(name=name)
        self.add_parameter(name='seq_mode',
                           get_cmd=self._get_seq_mod,
                           set_cmd=self._set_seq_mode,
                           vals=vals.Enum('on', 'off')
                           )

    def _get_seq_mod(self):
        if (self.aux_io_mode() == 'AUX_IN_TRIGGER_ENABLE' and
                self.aux_io_param() == 'TRIG_SLOPE_POSITIVE'):
            return 'on'
        elif (self.aux_io_mode() == 'AUX_IN_AUXILIARY' and
              self.aux_io_param() == 'NONE'):
            return 'off'
        else:
            raise ValueError('aux_io_mode: {}, aux_io_param: {} '
                             'do not correspond to seq_mode on or off')

    def _set_seq_mode(self, mode):
        if mode == 'on':
            self.aux_io_mode('AUX_IN_TRIGGER_ENABLE')
            self.aux_io_param('TRIG_SLOPE_POSITIVE')
        elif mode == 'off':
            self.aux_io_mode('AUX_IN_AUXILIARY')
            self.aux_io_param('NONE')
        else:
            raise ValueError('must set seq mode to "on" or "off"')
        self.sync_settings_to_card()