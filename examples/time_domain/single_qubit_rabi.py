#%% AWG upload
rabi_seq = pb.make_rabi_sequence(0, 100e-9, 1e-9, gaussian=True)
set_up_sequence(awg, alazar, [rec_ctrl], rabi_seq, seq_mode='on')

#%% Plot it
fig = rabi_seq.plot(channels=[1, 4], elemnum=5)
save_fig(fig, name="rabi_seq", pulse=True)

#%% Instr settings
qubit_pow = -5.5 #get_calibration_val('pi_pulse_pow')
qubit_freq = get_calibration_val('qubit_freq')
qubit.power(qubit_pow)
qubit.frequency(qubit_freq)
cavity.status('on')
localos.status('on')
qubit.status('on')
twpa.status('on')
alazar.seq_mode('on')
alazar.seq_mode('on')

#%% Rabi 1d
data, pl = measure(rec_ctrl.acquisition, key="mag")

#%% Rabi freq sweep

qubit_freq_start = get_calibration_val('qubit_freq') - 10e6
qubit_freq_stop = get_calibration_val('qubit_freq') + 10e6
qubit_freq_step = 2e6

data, plot = sweep1d(rec_ctrl.acquisition, qubit.frequency, qubit_freq_start, qubit_freq_stop, qubit_freq_step, 
                      live_plot=True, key="mag", save=True)

#%% Rabi power sweep

qubit_pow_start = -40
qubit_pow_stop = -10
qubit_pow_step = 1

data, plots = sweep1d(rec_ctrl.acquisition, qubit.power, qubit_pow_start, qubit_pow_stop, qubit_pow_step, 
                      live_plot=True, key="mag", save=True)


#%% Set calibration values (pulse seq)
set_calibration_val('pi_pulse_amp', 1)
set_calibration_val('pi_pulse_sigma', 10e-9)
set_calibration_val('sigma_cutoff', 4)
#set_calibration_val('pi_pulse_dur', 40e-9)



#%% Set calibration values (instr)
set_calibration_val('qubit_freq', 5.091e9)
set_calibration_val('pi_pulse_pow', -5.5)

#%% Recalculate coupling
g = recalculate_g(calib_update=True)