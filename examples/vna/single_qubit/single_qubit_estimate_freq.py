#%% Set estimated coupling (if necessary)
g = 80e6
set_calibration_val('g_value', g)

#%% #%% get estimated qubit frequencies from couplings and resonator push
g = get_calibration_val('g_value')

bare_res_freq = get_calibration_val('bare_res_freq')
pushed_res_freq = get_calibration_val('pushed_res_freq')

expected_qubit_freq = qubit_from_push(g, bare_res_freq, pushed_res_freq)
print('expect qubit at {}'.format(expected_qubit_freq))

#%% Set calibration value
set_calibration_val('expected_qubit_freq', expected_qubit_freq)