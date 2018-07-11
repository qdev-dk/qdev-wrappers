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


# scfg = StationConfigurator('exampleConfig.yaml')
scfg = StationConfigurator()
# dmm1 = scfg.load_instrument('dmm1')
# mock_dac = scfg.load_instrument('mock_dac')
mock_dac = scfg.load_instrument('qdac')

# this works only with the lakeshore PR and when you change the directory in
# yaml file to point to the sim file
# ls = scfg.load_instrument('lakeshore')

# # if you happen to have a qdac you can also change the hardware address in the
# # config file and then do the following:
# # watch out! the current config file will set a voltage on the qdac!
# qdac = scfg.load_instrument('qdac')
# # now you should be able to do
# qdac.Bx(0.04)
# # which should ramp up the voltage of ch02 from 0.02V (initial value) to
# # 0.08V (scaling factor is 0.2)
# # that is fine
# qdac.Bx(0.09)
# # but this will fail because it is outside the specified range
# qdac.Bx(0.11)
