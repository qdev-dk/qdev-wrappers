
# Example how to use a Rhode & Schwarz VNA, here called v1
## See also https://github.com/QCoDeS/Qcodes/blob/master/docs/examples/driver_examples/Qcodes%20example%20with%20Rohde%20Schwarz%20ZNB.ipynb



## Set power on all channels
#vna.channels.power(-5)

#%%
## Set power of specific channel:
vna.channels.S21.power(-5)

#%% Turn rf on
vna.rf_on()



#%% Do a measurement 
### Define parameters for traces:
vna.channels.S21.npts(201)
vna.channels.S21.bandwidth(100)
vna.channels.S21.avg(1)
vna.channels.S21.power(-35)
vna.channels.S21.start(5.388e9)
vna.channels.S21.stop(5.418e9)
#vna.channels.S21.center(5.4035e9)
#vna.channels.S21.span(2e6)



#%%

do2d(deca.jj, -2.500, -5.500, 301, 0.01, deca.lplg, 0.000, 0.003, 301, 0.01, vna.single_S21_mag, vna.single_S21_phase)
do1d(deca.rplg, 0.000, 0.400, 101, 0.01, vna.single_S21_mag)
do2d(deca.jj, -5.500, -2.500, 301, 0.01, deca.lplg, 0.000, 0.003, 301, 0.01, vna.single_S21_mag, vna.single_S21_phase)
do1d(deca.rplg, 0.400, -0.400, 201, 0.01, vna.single_S21_mag)
do2d(deca.jj, -2.500, -5.500, 301, 0.01, deca.lplg, 0.000, 0.003, 301, 0.01, vna.single_S21_mag, vna.single_S21_phase)

## sweep left cutter and take traces
 #%%
 
vna.channels[0].status(0)
vna.channels[1].status(1)


do1d(dummy_time, 0, 60, 2, 1, vna.channels.S21.trace_mag_phase)


#%%
#v1.channels.S21.start(5e9)
#v1.channels.S21.stop(7e9)



#do1d(deca.lplg, 0, -1, 501, 1, v1.channels.S21.trace)

### define a frequency span
#v1.channels.S11.span(200e3)
#v1.channels.S11.center(1e6)
#v1.channels.S11.npts(100)

#do1d(deca.rplg, 0, -1, 101, 1,v1.channels.S21.trace)

#%% #%% spectroscopy

vna.add_spectroscopy_channel('192.168.15.106')

#%% Do a measurement 
### Define parameters for traces:
vna.channels.B2G1SAM.npts(401)
vna.channels.B2G1SAM.bandwidth(100)
vna.channels.B2G1SAM.start(6e9)
vna.channels.B2G1SAM.stop(8e9)
vna.channels.B2G1SAM.avg(4)
vna.channels.B2G1SAM.power(-35)

vna.readout_freq(5.409e9)
vna.readout_power(-40)

#%%
vna.channels[0].status(0)
vna.channels[1].status(1)

vna.channels.S21.status(1)
vna.channels.B2G1SAM.status(1)
#vna.channels.B2G1SAM.trace_mag_phase() 
do1d(dummy_time, 0, 60, 3, 1, vna.channels.B2G1SAM.trace_mag_phase)
 

do1d(vna.readout_freq, 5.401e9, 5.403e9, 21, 1, vna.channels.B2G1SAM.trace)

do1d(vna.channels.B2G1SAM.power, -50,-20,11, 1, vna.channels.B2G1SAM.trace)

do1d(deca.Q1cut, -0.9 ,-0.8 ,21, 1, vna.channels.B2G1SAM.trace_mag_phase)
do1d(deca.Q1cut, -1.90 ,-1.94 ,21, 1, vna.channels.B2G1SAM.trace)

do1d(deca.Q1lplg, -0.025 ,-0.031 ,101, 1, vna.channels.B2G1SAM.trace)


#%%
do1d(deca.jj, -1.45, -1.85, 201,0.01, vna.channels.B2G1SAM.trace_mag_phase)


## over QDev all
do1d(deca.lcut, -3.5, 0, 351, 0.0001,vna.single_S21_mag, lockin_2.g)
do1d(deca.rcut, -0, -3, 301, 0.0001,vna.single_S21_mag, lockin_2.g)
do1d(deca.jj, -0, -2.5, 251, 0.0001,vna.single_S21_mag, lockin_2.g)
do1d(deca.jj, -2.5, -0, 251, 0.0001,vna.single_S21_mag, lockin_2.g)
do1d(deca.lcut, -0, -3.5, 351, 0.0001,vna.single_S21_mag, lockin_2.g)
do1d(deca.jj, -0, -2.5, 251, 0.0001,vna.single_S21_mag, lockin_2.g)
do1d(deca.jj, -2.5, -0, 251, 0.0001,vna.single_S21_mag, lockin_2.g)
do1d(deca.rcut, -3, -0, 301, 0.0001,vna.single_S21_mag, lockin_2.g)


vna.channels.S21.npts(51)
vna.channels.S21.bandwidth(20)
vna.channels.S21.avg(1)
#vna.channels.S21.center(5.1814e9)
vna.channels.S21.power(-45)
vna.channels.S21.start(5.18e9)
vna.channels.S21.stop(5.183e9)
# Thu, 21 Sep 2017 11:53:35
do1d(deca.jj,0,-2.5,501,0.001, vna.channels.S21.trace_mag_phase)
do1d(deca.jj,-2.5,0,501,0.001, vna.channels.S21.trace_mag_phase)

vna.channels.S21.npts(1)
vna.channels.S21.bandwidth(10)
vna.channels.S21.avg(1)
vna.channels.S21.center(5.1806e9)
vna.channels.S21.power(-45)
do1d(deca.lplg, 0.05, 0.04,201,0.0001,vna.single_S21_mag)
do1d(deca.rcut, -3, -0, 301, 0.0001,vna.single_S21_mag)

vna.channels.S21.npts(201)
vna.channels.S21.bandwidth(100)
vna.channels.S21.avg(1)
#vna.channels.S21.center(5.1814e9)
vna.channels.S21.power(-45)
vna.channels.S21.start(5.5e9)
vna.channels.S21.stop(5.7e9)
# Thu, 21 Sep 2017 11:53:
do1d(dummy_time,0,2,3,1,vna.channels.S21.trace_mag_phase)
do1d(deca.jj,0,-2.5,501,0.001, vna.channels.S21.trace_mag_phase)
do1d(deca.jj,-2.5,0,501,0.001, vna.channels.S21.trace_mag_phase)

vna.channels.S21.npts(101)
vna.channels.S21.bandwidth(100)
vna.channels.S21.avg(1)
#vna.channels.S21.center(5.1814e9)
vna.channels.S21.power(-45)
vna.channels.S21.start(5.176e9)
vna.channels.S21.stop(5.186e9)
# Thu, 21 Sep 2017 11:53:35
do1d(deca.jj,-0,-2,201,0.001, vna.channels.S21.trace_mag_phase)

vna.channels.S21.npts(1)
vna.channels.S21.bandwidth(100)
vna.channels.S21.avg(1)
vna.channels.S21.center(5.181e9)
vna.channels.S21.power(-45)

do1d(vna.channels.S21.center, 5.175e9, 5.186e9, 101, 0.01, vna.single_S21_mag)