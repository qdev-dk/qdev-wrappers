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
gate_dict = pb.make_pulse_dict(qubit_indices=[0, 1, 2, 3],
                                SSBfreqs=[1e6, 1e6, 1e6, 1e6], gaussian=True,
                                drag=False, z_gates=False, SR=1e9)

#%%
set_current_qubit(1)
set_calibration_val('pi_pulse_sigma', 30e-9)
get_calibration_array('pi_pulse_sigma')

#%%
c = pb.make_sequence_from_gate_lists([['X', 'Y/2'], ['Y']],
                                    SSBfreq=50e6,
                                    channels=[1, 2, 3, 4])
c.print_segment_lists()
p = c.plot(elemnum=0)


#%%
allxy = pb.make_allxy_sequence(gaussian=False, drag=False,
                               SSBfreq=None, spacing=None)
allxy.print_segment_lists()
p = allxy.plot(elemnum=12)

#%%
bench = pb.make_benchmarking_sequence(2, 1)
bench.print_segment_lists()
p = bench.plot()
