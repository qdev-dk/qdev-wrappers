#%% Set estimated couplings (if necessary)
estimated_g = 75e6
g_array = np.zeros(get_qubit_count()) + estimated_g
set_calibration_array('g_value', g_array)

#%% get estimated qubit frequencies from couplings and resonator push
expected_qubit_freqs = np.empty(get_qubit_count())
bare_res_array = get_calibration_array('bare_res_freq')
pushed_res_array = get_calibration_array('pushed_res_freq')
g_array = get_calibration_array('g_value')

for i in range(get_qubit_count()):
    bare = bare_res_array[i]
    pushed = pushed_res_array[i]
    g = g_array[i]
    expected_qubit_freqs[i] = qubit_from_push(g, bare, pushed)

print('expect qubits at {}'.format(expected_qubit_freqs))

#%% Set calibration values
set_calibration_array('expected_qubit_freq', expected_qubit_freqs)