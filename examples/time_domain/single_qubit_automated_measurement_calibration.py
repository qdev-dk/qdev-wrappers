#%% AWG upload
ssb_seq = make_spectroscopy_SSB_sequence(0, 0, 1e6)
set_up_sequence(awg, alazar, [ave_ctrl, samp_ctrl, rec_ctrl], ssb_seq, seq_mode='off')

#%% Instr settings
qubit.status('off')
twpa.status('on')

#%% Calibration
calibrate_cavity(cavity, localos, ave_ctrl, alazar,
                 centre_freq=None, demod_freq=None, calib_update=True,
                 cavity_pow=None, localos_pow=None, detuning=3e5, live_plot=True)