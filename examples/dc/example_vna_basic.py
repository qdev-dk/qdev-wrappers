
# Example how to use a Rhode & Schwarz VNA, here called v1
## See also https://github.com/QCoDeS/Qcodes/blob/master/docs/examples/driver_examples/Qcodes%20example%20with%20Rohde%20Schwarz%20ZNB.ipynb


## Set power on all channels
vna.channels.power(-5)

#%%
## Set power of specific channel:
vna.channels.S21.power(-5)

#%% Turn rf on
vna.rf_on()

#%% Do a measurement 
### Define parameters for traces:

vna.channels.S21.start(5.2e9)
vna.channels.S21.stop(5.4e9)

#%%
#v1.channels.S21.start(5e9)
#v1.channels.S21.stop(7e9)

npts = 1001
vna.channels.S21.npts(npts)

## sweep left cutter and take traces

do1d(dummy_time, 0, 60, 2, 1, vna.channels.S21.trace)

#do1d(deca.lplg, 0, -1, 501, 1, v1.channels.S21.trace)

### define a frequency span
#v1.channels.S11.span(200e3)
#v1.channels.S11.center(1e6)
#v1.channels.S11.npts(100)

#do1d(deca.rplg, 0, -1, 101, 1,v1.channels.S21.trace)

#%% 

vna.add_spectroscopy_channel('192.168.15.104')

#%%
vna.readout_freq(5e9)
vna.readout_power(-50)
vna.channels.B2G1SAM.trace_mag_phase()

#%%
do1d(dummy_time, 0, 60, 2, 1, vna.channels.B2G1SAM.trace_mag_phase)