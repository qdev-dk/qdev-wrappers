#%% Choose qubit (leave as none to use 'current qubit' in calib dict)
index = 3

#%% sweep power around resonator
freq = get_calibration_val('bare_res_freq')#, qubit_index=index)
startf = freq - 15e6
stopf = freq + 15e6
stepf = 0.5e6
dat, pl = sweep2d_vna(vna, startf, stopf, stepf, gate.voltage, 1, 0.8, 0.02)