# import as a first module logging, and start logging
from qcodes.logger import start_all_logging
start_all_logging()

# import modules you might want to use
import qcodes as qc
import time
import atexit
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

# import some dummy instruments to have something to look at
from qcodes.tests.instrument_mocks import DummyInstrument, DummyChannelInstrument


# import necessary wrappers and measurement functions
from qdev_wrappers.file_setup import (
    CURRENT_EXPERIMENT, my_init, close_station, init_python_logger)
from qdev_wrappers.configreader import Config
from qdev_wrappers.show_num import show_num, show_meta
from qdev_wrappers.sweep_functions import do1d, do2d, do0d
from qdev_wrappers.transmon import *

# set matplotlib default settings
mpl.rcParams['figure.subplot.bottom'] = 0.15
mpl.rcParams['font.size'] = 10


if __name__ == '__main__':
    # this line should be the first line, no matter what
    init_python_logger()
    # close any existing instruments connections at restart
    atexit.register(qc.Instrument.close_all)
    # Close existing connections if present
    if qc.Station.default:
        close_station(qc.Station.default)

    # initialise station
    STATION = qc.Station()


    dac = DummyInstrument(name="dac", gates=['ch1', 'ch2'])  # The DAC voltage source
    dmm = DummyInstrument(name="dmm", gates=['voltage'])  # The DMM voltage reader
    dc = DummyChannelInstrument(name='dc')

    import random
    dmm.voltage.get =  lambda: random.randint(0, 100)

    # We add a parameter that loudly prints what it is being set to
    # (It is used below)

    chX = 0
    def myget():
        return chX

    def myset(x):
        global chX
        chX = x
        print('Setting to {}'.format(x))
        return None

    dac.add_parameter('verbose_channel',
                      label='Verbose Channel',
                      unit='V',
                      get_cmd=myget,
                      set_cmd=myset)

#
#
#    # Next, the instruments should be bound to a Station.
#    # Only instruments bound to the Station get recorded in the
#    # measurement metadata, so your metadata is blind to
#    # any instrument not in the Station.
#
#    station = qc.Station(dac, dmm, dc)

#    # Set up folders, settings and logging for the experiment
#    my_init("MT_LEc03_SE_sw", STATION,
#            pdf_folder=True, png_folder=True, analysis_folder=True,
#            waveforms_folder=True, calib_config=True,
#            annotate_image=False, mainfolder=None, display_pdf=False,
#            display_individual_pdf=False, qubit_count=1,
#            plot_x_position=0.66)
#
#    # Load instument config files, attempts to load the experiment specific
#    # file, if none found then the default from the scripts_folder
#    # specified in qc.config is used
#    instr_config = get_config('instr')
#    # make a locel version of the calibration config from the default and
#    # set it up for use.
#    make_local_config_file('calib')
#    calib_config = get_config('calib')
#
#    # Initialise intruments and add them to the station
#    qdac = QDAC_ext('QDAC', 'ASRL4::INSTR')
#    STATION.add_component(qdac)
#    dmm1 = Agilent_34400A(
#        'DMM1', 'GPIB0::11::INSTR')
#    STATION.add_component(dmm1)
#    dmm2 = Agilent_34400A(
#        'DMM2', 'GPIB0::8::INSTR')
#    STATION.add_component(dmm2)
#    deca = Decadac_ext('Decadac', 'ASRL1::INSTR', instr_config,terminator='\n')
#    STATION.add_component(deca)
#    lockin_2 = SR830_ext('lockin_2', 'GPIB0::2::INSTR', instr_config)
#    STATION.add_component(lockin_2)
#    keith = Keithley_2600_ext('Keithley', 'GPIB0::9::INSTR', 'a')
#    STATION.add_component(keith)
#    gs200 = GS200_special('gs200', 'GPIB0::10::INSTR', initial_voltage=14)
#    STATION.add_component(gs200)
#    alazar = AlazarTech_ATS9360_ext('alazar', seq_mode='off')
#    STATION.add_component(alazar)
#    ave_ctrl = ATS9360Controller_ext('ave_ctrl', alazar, ctrl_type='ave')
#    STATION.add_component(ave_ctrl)
#    rec_ctrl = ATS9360Controller_ext('rec_ctrl', alazar, ctrl_type='rec')
#    STATION.add_component(rec_ctrl)
#    samp_ctrl = ATS9360Controller_ext('samp_ctrl', alazar, ctrl_type='samp')
#    STATION.add_component(samp_ctrl)
#    qubit = RohdeSchwarz_SGS100A(
#        'qubit', 'TCPIP0::192.168.15.101::inst0::INSTR')
#    STATION.add_component(qubit)
#    localos = RohdeSchwarz_SGS100A(
#        'localos', 'TCPIP0::192.168.15.105::inst0::INSTR')
#    STATION.add_component(localos)
#    cavity = RohdeSchwarz_SGS100A(
#        'cavity', 'TCPIP0::192.168.15.104::inst0::INSTR')
#    STATION.add_component(cavity)
#    awg = AWG5014_ext(
#        'awg', 'TCPIP0::192.168.15.102::inst0::INSTR', timeout=40)
#    STATION.add_component(awg)
#    mercury = MercuryiPS(name='mercury',
#                         address='192.168.15.200',
#                         port=7020,
#                         axes=['X', 'Y', 'Z'])
#    STATION.add_component(mercury)
#    vna = VNA_ext('VNA', 'TCPIP0::192.168.15.103::inst0::INSTR')
#    STATION.add_component(vna)
#    dummy_time = qc.ManualParameter('dummy_time')
#    mag_sphere = SphereCor('Magnet', mercury.x_fld, keith.By, mercury.z_fld)
#    STATION.add_component(mag_sphere)
#    mag_sphere.radius.label = 'B magnitude'
#    mag_sphere.radius.unit = 'T'
#    mag_sphere.theta.label = 'B theta'
#    mag_sphere.phi.label = 'B phi'
#
#    # Specify which parameters are to be added to the monitor and printed in
#    # metadata
#    param_monitor_list = [
#        qdac.ch01_v, qdac.ch02_v, qdac.ch03_v, qdac.ch04_v,
#        samp_ctrl.num_avg, samp_ctrl.int_time, samp_ctrl.int_delay,
#        rec_ctrl.num_avg, rec_ctrl.int_time, rec_ctrl.int_delay,
#        ave_ctrl.num_avg, ave_ctrl.int_time, ave_ctrl.int_delay,
#        awg.state, awg.ch1_amp, awg.ch2_amp,
#        awg.ch3_amp, awg.ch4_amp,
#        alazar.seq_mode,
#        qubit.frequency, qubit.power, qubit.status, qubit.IQ_state,
#        localos.frequency, localos.power, localos.status,
#        cavity.frequency, cavity.power, cavity.status, cavity.IQ_state,
#        vna.channels.S21.power, vna.channels.S21.start,
#        vna.channels.S21.stop, vna.channels.S21.avg,
#        vna.channels.S21.bandwidth, vna.channels.S21.npts,
#        mercury.x_fld, mercury.z_fld, keith.By,
#        mag_sphere.radius, mag_sphere.theta, mag_sphere.phi
#    ]
#
#    # Get parameter values to populate monitor initially
#    print('Querying all instrument parameters for metadata.'
#          'This may take a while...')
#    start = time.time()
#    for param in param_monitor_list:
#        param.get()
#
#    end = time.time()
#    print("done Querying all instruments took {}".format(end - start))

    # Put parameters into monitor
    # qc.Monitor(*param_monitor_list)
