from qcodes.instrument_drivers.AlazarTech.ATS9360 import AlazarTech_ATS9360
from qdev_wrappers.alazar_controllers.ATS9360Controller import ATS9360Controller
from qcodes.utils import validators as vals


class ATS9360Controller_ext(ATS9360Controller):
    def __init__(self, name, alazar, ctrl_type='ave'):
        if ctrl_type == 'samp':
            integrate_samples = False
            average_records = True
        elif ctrl_type == 'ave':
            integrate_samples = True
            average_records = True
        elif ctrl_type == 'rec':
            integrate_samples = True
            average_records = False
        else:
            raise Exception('acquisition controller type must be in {}, '
                            'received: {}'.format(['samp', 'ave', 'rec'],
                                                  ctrl_type))
        super().__init__(name=name, alazar_name=alazar.name,
                         integrate_samples=integrate_samples,
                         average_records=average_records)


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
        self.config(clock_source='EXTERNAL_CLOCK_10MHz_REF',
                    #sample_rate=500_000_000,
                    external_sample_rate=500_000_000,
                    clock_edge='CLOCK_EDGE_RISING',
                    decimation=1,
                    coupling=['DC', 'DC'],
                    channel_range=[.4, .4],
                    impedance=[50, 50],
                    trigger_operation='TRIG_ENGINE_OP_J',
                    trigger_engine1='TRIG_ENGINE_J',
                    trigger_source1='EXTERNAL',
                    trigger_slope1='TRIG_SLOPE_POSITIVE',
                    trigger_level1=140,
                    trigger_engine2='TRIG_ENGINE_K',
                    trigger_source2='DISABLE',
                    trigger_slope2='TRIG_SLOPE_POSITIVE',
                    trigger_level2=128,
                    external_trigger_coupling='DC',
                    external_trigger_range='ETR_2V5',
                    trigger_delay=0,
                    timeout_ticks=0,
                    aux_io_mode=io_mode,
                    aux_io_param=io_param
                    )
        self.add_parameter(name='seq_mode',
                           get_cmd=self._get_seq_mod,
                           set_cmd=self._set_seq_mode,
                           vals=vals.Anything()
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
            self.config(sample_rate=self.sample_rate(),
                        clock_edge=self.clock_edge(),
                        clock_source=self.clock_source(),
                        aux_io_mode='AUX_IN_TRIGGER_ENABLE',
                        aux_io_param='TRIG_SLOPE_POSITIVE')
        elif mode == 'off':
            self.config(sample_rate=self.sample_rate(),
                        clock_edge=self.clock_edge(),
                        clock_source=self.clock_source(),
                        aux_io_mode='AUX_IN_AUXILIARY',
                        aux_io_param='NONE')
        else:
            raise ValueError('must set seq mode to "on" or "off"')
