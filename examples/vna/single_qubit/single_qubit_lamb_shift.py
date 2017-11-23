#%% Choose qubit (leave as none to use 'current qubit' in calib dict)
index = None

#%% sweep power around resonator
freq = get_calibration_val('bare_res_freq', qubit_index=index)
startf = freq - 15e6
stopf = freq + 15e6
stepf = 0.5e6
dat, pl = sweep2d_vna(vna, startf, stopf, stepf, vna.channels.S21.power, -10, -50, 1)

#%% make plot of resonance with power and get pushed resonant frequency
pushed_res, dif_fig = get_resonator_push(dat, z_key="trace")
# save_fig(dif_fig, name="lamb_shift_q{}".format(index))
print('pushed resonator set to: {}'.format(pushed_res))

#%% set calibration value for pushed resonance
set_calibration_val('pushed_res_freq', pushed_res, qubit_index=index)