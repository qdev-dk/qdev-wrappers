"""
This example illustrates how to use the StationConfigurator
When running it, make sure that your working directory is set to the path of
this file, or that you put the exampleConfig.yaml and the yaml file for the
simulated instrument (Agilent_34400A.yaml) into your current path.
If you don't like to have them there you can change the path in the init
function of the StationConfigurator, as well as the path in the yaml file(
everything befor the @-sign).
You also need to have the otpion 'enable_forced_reconnect' in your
qcodesrc.json, as it is the case for the example config file in this path.

A handy feature is that you can simply reëxecute the all the code, and should
stay in a consisten state. It will only fail for those instruments that you
have specified to not be simply reinstantiated (depending on the setting in
your qcdoesrc.json file and the  auto reconnect option in the yaml file)

You can try starting the qcodes monitor and see how the parameters get added.
Currently a bug is that the parameters do not get removed once an instrument
is closed. So there will appear multiple copies of them.

"""
from qdev_wrappers.station_configurator import StationConfigurator
import qcodes as qc

# scfg = StationConfigurator('exampleConfig.yaml')
scfg = StationConfigurator('testSetupConfig.yaml')

# Configure all settings in the Alazar card

alazar = scfg.load_instrument('Alazar')
alazar.sync_settings_to_card()
#alazar.config(clock_source='INTERNAL_CLOCK',
#              sample_rate=1_000_000_000,
#              clock_edge='CLOCK_EDGE_RISING',
#              decimation=1,
#              coupling=['DC','DC'],
#              channel_range=[.4,.4],
#              impedance=[50,50],
#              trigger_operation='TRIG_ENGINE_OP_J',
#              trigger_engine1='TRIG_ENGINE_J',
#              trigger_source1='EXTERNAL',
#              trigger_slope1='TRIG_SLOPE_POSITIVE',
#              trigger_level1=160,
#              trigger_engine2='TRIG_ENGINE_K',
#              trigger_source2='DISABLE',
#              trigger_slope2='TRIG_SLOPE_POSITIVE',
#              trigger_level2=128,
#              external_trigger_coupling='DC',
#              external_trigger_range='ETR_2V5',
#              trigger_delay=0,
#              timeout_ticks=0,
#              aux_io_mode='AUX_IN_AUXILIARY', # AUX_IN_TRIGGER_ENABLE for seq mode on
#              aux_io_param='NONE' # TRIG_SLOPE_POSITIVE for seq mode on
#             )
alazar_ctrl = scfg.load_instrument('AlazarController')

alazar_sample_chan = scfg.load_instrument('AlazarSampleChannel', parent=alazar_ctrl)

alazar_records_chan = scfg.load_instrument('AlazarRecordChannel', parent=alazar_ctrl)

alazar_buffer_chan =  scfg.load_instrument('AlazarBufferChannel', parent=alazar_ctrl)

alazar_sample_record_chan = scfg.load_instrument('AlazarSampleRecordChannel', parent=alazar_ctrl)

alazar_sample_buffer_chan = scfg.load_instrument('AlazarSampleBufferChannel', parent=alazar_ctrl)

alazar_record_buffer_chan = scfg.load_instrument('AlazarRecordBufferChannel', parent=alazar_ctrl)