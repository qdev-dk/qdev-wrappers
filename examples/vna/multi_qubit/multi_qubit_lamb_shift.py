#%% sweep power around resonators
pow_sweeps = []

for freq in get_calibration_array('bare_res_freq'):
    startf = freq - 15e6
    stopf = freq + 15e6
    stepf = 0.1e6
    dat, pl = sweep2d_vna(vna, startf, stopf, 0.1e6, vna.channels.S21.power, -10, -50, 1)
    pow_sweeps.append(dat)

#%% make plot of resonance with power and get pushed resonant frequency
pushed_res_array = np.empty(get_qubit_count())
bare_res_array = np.empty(get_qubit_count())

for i, dat in enumerate(pow_sweeps):
    pushed_res, bare_res,  dif_fig = get_resonator_push(dat, z_key="trace")
    pushed_res_array[i] = pushed_res
    bare_res_array[i] = bare_res
    save_fig(dif_fig)

print('pushed resonators set to: {}'.format(pushed_res_array))

#%% correct pushes and set calibration values for pushed resonances
low_pow_indices_to_correct = [3]
low_pow_vals = [9e9]
high_pow_indices_to_correct = []
high_pow_vals = []

for i, res_index in enumerate(low_pow_indices_to_correct):
    pushed_res_array[res_index] = low_pow_vals[i]
for i, res_index in enumerate(high_pow_indices_to_correct):
    bare_res_array[res_index] = high_pow_vals[i]

set_calibration_array('pushed_res_freq', pushed_res_array)
set_calibration_array('bare_res_freq', bare_res_array)
print('bare resonators are now {}'.format(get_calibration_array('bare_res_freq')))
print('pushed resonators are now {}'.format(pushed_res_array))
print('pushes are now {}'.format(pushed_res_array - get_calibration_array('bare_res_freq')))