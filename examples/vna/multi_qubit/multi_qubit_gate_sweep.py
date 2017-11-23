gate_sweeps = []

for freq in get_calibration_array('pushed_res_freq'):
    startf = freq - 15e6
    stopf = freq + 15e6
    stepf = 0.1e6
    dat, pl = sweep2d_vna(v1, startf, stopf, 0.1e6, gate.voltage,  0, -0.2, 0.01)
    gate_sweeps.append(dat)