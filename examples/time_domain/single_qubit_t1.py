#%% AWG upload
t1_seq = make_t1_sequence(0, 5e-6, 50e-9, gaussian=True)
set_up_sequence(awg, alazar, [rec_ctrl], t1_seq, seq_mode='on')

#%% Plot it
fig = t1_seq.plot(channels=[1, 4], elemnum=100)
save_fig(fig, name="t1_seq", pulse=True)

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

#%% T1_meas
data, pl = measure(rec_ctrl.acquisition, key="mag")

#%% T1 fit

plot, fit_params, param_errors = get_t1(data, x_name='pi_pulse_readout_delay_set', y_name='rec_ctrl_demod_freq_0_mag',
                                        plot=True, subplot=None)
