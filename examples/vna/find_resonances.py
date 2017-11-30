#%% Take wide freq data (all resonances)

vna.channels.S21.power(-5)
vna.channels.S21.center(7.2e9)
vna.channels.S21.span(400e6)
vna.channels.S21.avg(5)
vna.channels.S21.bandwidth(1000)
vna.channels.S21.npts(2001)
vna.rf_on()

data, plots = measure(vna.channels.S21.trace)

#%% Find resonances by smoothing and fitting
# sampling frequency used for smoothing  (ie span * npts)
fs = vna.channels.S21.npts.get_latest() / (vna.channels.S21.stop.get_latest() - vna.channels.S21.start.get_latest())
# fs = 2001 / (7.35e9 - 7.05e9)
indices, resonances_array, res_attempt_plot = find_peaks(data, fs, y_key="trace",
                                                         cutoff=5e-7, order=3, widths=np.linspace(40, 150))

#%% Save fit attempt
save_fig(res_attempt_plot, name='find_resosonances')

#%% Correct resonances array if necessary 
correct_resonance_indices = [1, 2, 3, 4, 5] # TODO
additional_resonances = [7.132e9] # TODO

correct_resonances_array = np.array(list(resonances_array[i] for i in correct_resonance_indices))
correct_indices = np.array(list(indices[i] for i in correct_resonance_indices))

#%%
for res in additional_resonances:
    correct_resonances_array = np.append(correct_resonances_array, res)
    correct_indices = np.append(correct_indices, (np.abs(data.arrays['S21 frequency_set'].ndarray - res).argmin()))

correct_resonances_array.sort()
correct_indices.sort()

correct_res_plot = plot_with_markers(data, correct_indices, y_key="trace", title="correct peaks")
print('resonances_array set to: {}'.format(correct_resonances_array))

#%% Save corrected fit and set calibration values
save_fig(correct_res_plot, name='corrected_resonances')
set_calibration_array('bare_res_freq', correct_resonances_array)

    