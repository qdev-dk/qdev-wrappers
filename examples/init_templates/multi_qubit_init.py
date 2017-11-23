import qcodes as qc
import time
import sys
import logging
import numpy as np
from os.path import sep
import matplotlib as mpl
import matplotlib.pyplot as plt
mpl.rcParams['figure.figsize'] = (8, 3)
mpl.rcParams['figure.subplot.bottom'] = 0.15
mpl.rcParams['font.size'] = 8

from wrappers.file_setup import CURRENT_EXPERIMENT
from wrappers.configreader import Config
from wrappers.file_setup import close_station, my_init
from qcodes import ManualParameter

from wrappers import *
from wrappers.transmon import *
if qc.config.user.scriptfolder not in sys.path:
    sys.path.insert(0, qc.config.user.scriptfolder)
from customised_instruments import Decadac_T2, AWG5014_T2, \
    ATS9360Controller_T2, AlazarTech_ATS9360_T2, VNA_T2

from qcodes.instrument_drivers.oxford.mercuryiPS import MercuryiPS
from qcodes.instrument_drivers.rohde_schwarz.SGS100A import RohdeSchwarz_SGS100A


if __name__ == '__main__':

    init_log = logging.getLogger(__name__)

    # Close existing connections if present
    if qc.Station.default:
        close_station(qc.Station.default)

    STATION = qc.Station()

    # Set up folders, settings and logging for the experiment
    my_init("floquet_test3", STATION, qubit_count=4,
            pdf_folder=True, analysis_folder=True,
            calib_config=True, waveforms_folder=True,
            local_scripts_folder=True, instr_config=True,
            mainfolder=None, annotate_image=False, display_pdf=True,
            display_individual_pdf=False,
            plot_x_position=0.66)

    # Load instrument and calibration config
    instr_config = get_config('instr')
    make_local_config_file('calib')
    calib_config = get_config('calib')

    # Initialise intruments
    deca = Decadac_T2('Decadac', 'ASRL1::INSTR', instr_config)
    alazar = AlazarTech_ATS9360_T3('alazar', seq_mode='off')
    ave_ctrl = ATS9360Controller_T3('ave_ctrl', alazar, ctrl_type='ave')
    rec_ctrl = ATS9360Controller_T3('rec_ctrl', alazar, ctrl_type='rec')
    samp_ctrl = ATS9360Controller_T3('samp_ctrl', alazar, ctrl_type='samp')
    localos = RohdeSchwarz_SGS100A('localos_rs',
                                   'TCPIP0::192.168.15.104::inst0::INSTR')
    cavity_source = RohdeSchwarz_SGS100A('cavity_rs',
                                         'TCPIP0::192.168.15.105::inst0::INSTR')
    qubit_source = RohdeSchwarz_SGS100A('qubit_source',
                                        'TCPIP0::192.168.15.105::inst0::INSTR')
    awg1 = AWG5014_T3(
        'awg1', 'TCPIP0::192.168.15.101::inst0::INSTR', timeout=40)
    awg2 = AWG5014_T3(
        'awg2', 'TCPIP0::192.168.15.101::inst0::INSTR', timeout=40)
    vna = VNA_T3('VNA', 'TCPIP0::192.168.15.103::inst0::INSTR', S21=True)
    dummy_time = ManualParameter('dummy_time')

    # Specify which parameters are to be added to the monitir and printed in metadate
    # The instuments they beong to will be added to the STATION
    param_monitor_list = [
        deca.channels[0], deca.channels[1],
        deca.channels[2], deca.channels[3],
        samp_ctrl.num_avg, samp_ctrl.int_time, samp_ctrl.int_delay,
        rec_ctrl.num_avg, rec_ctrl.int_time, rec_ctrl.int_delay,
        ave_ctrl.num_avg, ave_ctrl.int_time, ave_ctrl.int_delay,
        awg1.state, awg1.ch1_amp, awg1.ch1_state, awg1.ch2_amp,
        awg1.ch3_state, awg1.ch4_amp, awg1.ch4_state,
        awg2.state, awg2.ch1_amp, awg2.ch1_state, awg2.ch2_amp,
        awg2.ch3_state, awg2.ch4_amp, awg2.ch4_state,
        alazar.seq_mode,
        cavity_source.frequency, cavity_source.power, cavity_source.status,
        qubit_source.frequency, qubit_source.power, qubit_source.status,
        localos.frequency, localos.power, localos.status,
        vna.channels.S21.power, vna.channels.S21.start,
        vna.channels.S21.stop, vna.channels.S21.avg,
        vna.channels.S21.bandwidth, vna.channels.S21.npts]

    # Add instruments to station so that metadata for them is recorded at
    # each measurement and connections are closed at end of session
    for param in param_monitor_list:
        if param._instrument.name not in STATION.components.keys():
            STATION.add_component(param._instrument)

    # Set log level
    logger = logging.getLogger()
    logger.setLevel(logging.WARNING)

    # Get parameter values to populate monitor
    print('Querying all instrument parameters for metadata.'
          'This may take a while...')
    start = time.time()

    for param in param_monitor_list:
        param.get()

    end = time.time()

    print("done Querying all instruments took {}".format(end - start))

    add_to_metadata_list(*param_monitor_list)

    # Put parameters into monitor
    Monitor(*param_monitor_list)
