#%% RUN INIT.PY

# TODO
# Initialise a new experiment by running the init_script.py in 'init_scripts'
# where you can set the qubit number and sample name. this sets up the file
# structure for data saving, pngs and a calibration dictionary (optional)

#%% IMPORT INSTRUMENTS

# TODO
# Run the cells from instr_import_script.py in  'init_scripts' corresponding to
# the instruments you want to use. You can set visa connections here

#%% START THE MONITOR (optional)

# TODO
# Start the monitor
# Run monitor_metadata_alazar_script.py or monitor_metadata_vna_script.py to set up
# the monitor and the metadata (all metadata is saved enen if you don't do this
# but this just sets which metadata gets printed when you load a plot back etc).
# You can choose which parameters are 'important' and should go in the monitor here.

#%% SET VALUES OF PARAMETERS

# NB you have to have imported the instrument already... ;P
vna.power21(-10)
gate.voltage(-5)


#%% GET VALUES OF PARAMETERS

#gate.voltage()
ave_ctrl.acquisition()

#%% TAKE A MEASUREMENT

# This is different from getting the value of a parameter as it will create
# and save a dataset and make a plot, there are no limits on dimensions of
# acquired data (ie you could get a gate voltage or a vna trace, all ok)

data, plot = measure(samp_ctrl.acquisition, key="mag")

#%% DO A SWEEP

# syntax is:
#
#    sweep1d(meas_param, sweep_param, start, stop, step, 
#            delay=0.01, live_plot=True, key=None, save=True)
#
#    sweep2d(meas_param, sweep_param1, start1, stop1, step1,
#            sweep_param2, start2, stop2, step2, delay=0.01,
#            live_plot=True, key=None, save=True)

data, plots = sweep1d(gate.voltage, startf, stopf, stepf, gate.voltage, 0, -0.2, 0.01)

data, plots = sweep2d(ave_ctrl.acquisition, qubit.frequency, gate.voltage,
                      4e9, 5e9, 1e6, 0, -1, 0.1)

#%% LOAD BACK DATA/PLOTS

# syntax is:
#    load(counter, plot=True, metadata=True, matplot=False, key=None)

data1 = load(15, plot=False)
data2, plot = load(24, metadata=False, matplot=True, key="mag")

#%% USE THE CALIBRATION DICTIONARY (optional)

# check out what you can keep in it
get_allowed_keys()

# use it
set_current_qubit(4)
set_calibration_val('qubit_freq', 5e9)
bare_resonator = get_calibration_val('bare_res_freq')