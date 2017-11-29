#%% AWG upload
ssb_seq = make_spectroscopy_SSB_sequence(0, 200e6, 1e6)
set_up_sequence(awg, alazar, [ave_ctrl, samp_ctrl, rec_ctrl], ssb_seq, seq_mode='on')

#%% Plot it
fig = ssb_seq.plot(channels=[1, 2, 4], elemnum=5)
save_fig(fig, name="ssb_seq", pulse=True)

#%% Instr settings
qubit_pow = get_calibration_val('spec_pow')
qubit.power(qubit_pow)
cavity.status('on')
localos.status('on')
qubit.status('on')
twpa.status('on')
alazar.seq_mode('on')
alazar.seq_mode('on')

#%% Take data1d
ssb_centre = get_calibration_val('qubit_freq')
data, pl = measure_ssb(qubit, rec_ctrl, ssb_centre, key="mag")

res, mag =  find_extreme(data, x_key="ssb_qubit", extr="min")
print('max at {}GHz, mag of {}'.format(res / 1e9, mag))

#%% Take data2d
data, pl = sweep1d(rec_ctrl.acquisition, qubit.frequency, 4e9, 5e9, 200e6, delay=0.1, key="mag")

#%% Power sweep
ssb_centre = get_calibration_val('qubit_freq') #- 20e6
data, plots = sweep2d_ssb(qubit, rec_ctrl, ssb_centre, qubit.power, -5, -30, 5,
                           key="mag")

#%% Time sweep
ssb_centre = get_calibration_val('qubit_freq')
time_between_points = 2
num_of_points = 10
data, plots = sweep_2d_ssb(qubit, rec_ctrl, ssb_centre, time_param, 0, num_of_points, 1,
                           delay=time_between_points2, key="mag")

#%% Gate sweep
#raise Exception('are you sure you want to do a gate sweep? comment me out')
ssb_centre = get_calibration_val('qubit_freq')
data, plots = sweep2d_ssb(qubit, rec_ctrl, ssb_centre, gate.voltage,
                           -0.005, 0, 0.001, delay=0.01,
                           live_plot=True, key="mag", save=True)

#%% Set calibration values
set_calibration_val('qubit_freq', 5.09e9)
set_calibration_val('spec_pow', -20)

#%% Recalculate coupling
g = recalculate_g(calib_update=True)