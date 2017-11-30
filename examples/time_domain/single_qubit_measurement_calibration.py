#%% AWG upload
readout_seq = pb.make_readout_single_sequence(channels=[4])
set_up_sequence(awg, alazar, [ave_ctrl], readout_seq, seq_mode='off')

#%% Cavity settings

cavity.power(-40)
localos.power(15)
cavity.frequency(get_calibration_val('pushed_res_freq'))
demod_freq = get_calibration_val('demod_freq')

cavity.status('on')
localos.status('on')
qubit.status('off')
twpa.status('on')
alazar.seq_mode('off')
alazar.seq_mode('off')

set_single_demod_freq(cavity, localos, [ave_ctrl], demod_freq)

#%% Take data
centre_freq = get_calibration_val('pushed_res_freq')

data, plot = do_cavity_freq_sweep(cavity, localos, centre_freq, ave_ctrl,
                                   cavity_pm=5e6, freq_step=0.1e6,
                                   live_plot=True, key="mag", save=True)

res, mag =  find_extreme(data, x_key='frequency_set', y_key="mag", extr="min")
print('min at {}GHz, mag of {}'.format(res / 1e9, mag))

#%% Set calibration values (and on instruments)

good_cav_freq = 7.0941e9#res + 2e5
good_cav_power = cavity.power()
good_demod_freq = get_demod_freq(cavity, localos, ave_ctrl)

set_calibration_val('cavity_freq', good_cav_freq)
set_calibration_val('cavity_pow', good_cav_power)
set_calibration_val('demod_freq', good_demod_freq)
cavity.power(good_cav_power)
set_single_demod_freq(cavity, localos, [samp_ctrl, ave_ctrl, rec_ctrl],
                      good_demod_freq, cavity_freq=good_cav_freq)
