from qdev_wrappers.file_setup import CURRENT_EXPERIMENT, close_station, my_init
from qdev_wrappers.configreader import Config
import qcodes as qc
from qdev_wrappers import *
from qdev_wrappers.transmon import *

# This is an example script for use of the sequencing and pulse building
# secion of the qdev_wrappers which uses the calibration.config to build
# sequences to be run on the awg based on these 'calibration' values

#%%
station = qc.Station()
my_init('floquet_test3', station, qubit_count=4, calib_config=True)

#%%
set_current_qubit(1)
set_calibration_val('pi_pulse_sigma', 30e-9)

#%%
get_calibration_array('pi_pulse_sigma')

#%%
c_ssb = pb.make_spectroscopy_SSB_sequence(0, 200e6, 1e6, channels=[3, 1, 2, 4],
                                          readout_SSBfreqs=[10e6, 1e6], pulse_mod=True)

#%%
c_ssb.print_segment_lists()
pl = c_ssb.plot(elemnum=3)


#%%
rabi = pb.make_rabi_sequence(0, 100e-9, 5e-9, pulse_mod=True, gaussian=True,
                            SSBfreq=20e6)

#%%
rabi.print_segment_lists()
pl = rabi.plot(elemnum=20)

#%%
t1 = pb.make_t1_sequence(0, 1e-6, 10e-9, pi_dur=100e-9, gaussian=False,
                         pulse_mod=True, SSBfreq=None)

#%%
t1.print_segment_lists()
pl = t1.plot(elemnum=30)

#%%
set_calibration_val('pulse_readout_delay', 1e-7)

#%%
ramsey = pb.make_ramsey_sequence(0, 1e-6, 100e-9, SSBfreq=10e6, pulse_mod=False)

#%%
ramsey.print_segment_lists()
pl = ramsey.plot(elemnum=10)