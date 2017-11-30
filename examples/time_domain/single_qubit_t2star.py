#%% AWG upload
ramsey_seq = pb.make_ramsey_sequence(0, 0.5e-6, 1e-9, gaussian=True)
set_up_sequence(awg, alazar, [rec_ctrl], ramsey_seq, seq_mode='on')

#%% Plot it
fig = rabi_seq.plot(channels=[1, 4], elemnum=5)
save_fig(fig, name="rabi_seq", pulse=True)

#%% Instr settings
qubit_pow = get_calibration_val('pi_pulse_pow')
qubit_freq = get_calibration_val('qubit_freq')
qubit.power(qubit_pow)
qubit.frequency(qubit_freq)
cavity.status('on')
localos.status('on')
qubit.status('on')
twpa.status('on')
alazar.seq_mode('on')
alazar.seq_mode('on')
rec_ctrl.num_avg(1000)

#%% Ramsey freq sweep

qubit_freq_start = get_calibration_val('qubit_freq') - 10e6
qubit_freq_stop = get_calibration_val('qubit_freq') + 10e6
qubit_freq_step = 1e6

data, plot = sweep1d(rec_ctrl.acquisition, qubit.frequency, qubit_freq_start, qubit_freq_stop, qubit_freq_step, 
                      live_plot=True, key="mag", save=True)


#%% T2* 1d
T2_meas_freq = 5.083e9
qubit.frequency(T2_meas_freq)

data, pl = measure(rec_ctrl.acquisition, key="mag")


#%% Set calibration values (pulse seq)
plot, fit_params, param_errors = get_t2(data, x_name='pi_half_pulse_pi_half_pulse_delay_set', y_name='rec_ctrl_demod_freq_0_mag',
                                       plot=True, subplot=None)

#%% Set calibration values (instr)
set_calibration_val('qubit_freq', 5.09e9)

#%% Recalculate coupling
g = recalculate_g(calib_update=True)