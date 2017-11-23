#%% Find qubit
qubit_freq = find_qubit(awg, alazar, rec_ctrl, qubit, start_freq=4e9, stop_freq=5.5e9,
                        qubit_power=None, calib_update=True, channels=[1, 2, 3, 4],
                        pulse_mod=False)

#%% Recalibrating time loop
repeat_number = 25 # recalibration and delay will occur this many times
repeat_delay = 1

inner_loop_time = 60
inner_loop_delay = 1

do_tracking_ssb_time_sweep(qubit, cavity, time_param, localos,
                           rec_acq_ctrl, ave_acq_ctrl, alazar, awg,
                           outer_loop_number, outer_loop_delay,
                           inner_loop_time, inner_loop_delay_step,
                           initial_cavity_freq=None)

#%% Recalibrating gate loop
gate_start = -3.3
gate_stop = -3
gate_step = 0.01
sleep_time = 0

gate_array = np.linspace(gate_start, gate_stop, num=round((gate_stop-gate_start) / gate_step+1))

for i, g in enumerate(gate_array):
    qubit.status('off')
    final_g = g + gate_step
    calibrate_cavity(cavity, localos, ave_ctrl, alazar, calib_update=True)
    print('scan {} started at {}, gate set to {}'.format(i, time.time(), g))
    qubit_freq, mag = find_qubit(awg1, alazar, rec_ctrl, qubit2, calib_update=True)
    do_rabis(awg, alazar, rec_ctrl, qubit, qubit_power=-40)
    do_rabis(awg, alazar, rec_ctrl, qubit, qubit_power=-35)
    do_rabis(awg, alazar, rec_ctrl, qubit, qubit_power=-30)
    sweep2d_ssb(qubit, rec_ctrl, qubit_freq, gate.voltage, g, g+gate_step, 0.001, delay=2,
                live_plot=True, key="mag", save=True)
    time.sleep(sleep_time)
