#%% AWG upload
readout_seq = pb.make_readout_single_sequence(channels=[4])
set_up_sequence(awg, alazar, [samp_ctrl], readout_seq, seq_mode='off')

#%% Alazar samples_acq settings
samp_ctrl.int_delay(0)
samp_ctrl.int_time(5e-6)
samp_ctrl.num_avg(1000)
alazar.seq_mode('off')
set_single_demod_freq(cavity, localos, [samp_ctrl], 15e6, cavity_freq=7e9)

#%% Take data
data, plots = measure(samp_ctrl.acquisition, key="mag")

#%% Set calibration values

good_int_delay = 0.5e-6
good_int_time = 1e-6

set_calibration_val('int_time', good_int_time)
set_calibration_val('int_delay', good_int_delay)
ave_ctrl.int_delay(good_int_delay)
ave_ctrl.int_time(good_int_time)
rec_ctrl.int_delay(good_int_delay)
rec_ctrl.int_time(good_int_time)
rec_ctrl.num_avg(1000)
ave_ctrl.num_avg(1000)

