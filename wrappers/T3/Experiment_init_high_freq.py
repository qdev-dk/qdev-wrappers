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
from majorana_wrappers import *
from reload_settings import *
from customised_instruments import SR830_T3, Decadac_T3, AWG5014_T3, \
ATS9360Controller_T3, AlazarTech_ATS9360_T3, VNA_T3
helper_fns_folder = r'D:\Transmon\Qcodes-contrib'
if helper_fns_folder not in sys.path:
    sys.path.insert(0, helper_fns_folder)
from qdev_transmon_helpers import *

from qcodes.instrument_drivers.oxford.mercuryiPS import MercuryiPS
from qcodes.instrument_drivers.rohde_schwarz.SGS100A import RohdeSchwarz_SGS100A

from conductance_measurements import do2Dconductance

if __name__ == '__main__':

    init_log = logging.getLogger(__name__)

    # Close existing connections if present
    if qc.Station.default:
        close_station(qc.Station.default)

    STATION = qc.Station()

    # Set up folders, settings and logging for the experiment
    my_init("AcQED_05_98_dev1", STATION,
            pdf_folder=True, analysis_folder=True,
            temp_dict_folder=True, waveforms_folder=True,
            annotate_image=False, mainfolder=None, display_pdf=True,
            display_individual_pdf=False, qubit_count=1,
            plot_x_position=0.66)

    # Load config from experiment file, if none found then uses one in mainfolder
    cfg_file = "{}{}".format(CURRENT_EXPERIMENT['exp_folder'], 'instr.config')
    instr_config = Config(cfg_file, isdefault=True)
    if len(instr_config.sections()) == 0:
        cfg_file = sep.join([CURRENT_EXPERIMENT['mainfolder'], 'instr.config'])
        instr_config = Config(cfg_file, isdefault=True)
        

    # Initialise intruments
    deca = Decadac_T3('Decadac', 'ASRL1::INSTR', instr_config)
#    lockin_2 = SR830_T3('lockin_2', 'GPIB0::2::INSTR', instr_config)
    alazar = AlazarTech_ATS9360_T3('alazar', seq_mode='off')
    ave_ctrl = ATS9360Controller_T3('ave_ctrl', alazar, ctrl_type='ave')
    rec_ctrl = ATS9360Controller_T3('rec_ctrl', alazar, ctrl_type='rec')
    samp_ctrl = ATS9360Controller_T3('samp_ctrl', alazar, ctrl_type='samp')
    localos = RohdeSchwarz_SGS100A('localos_rs',
                                   'TCPIP0::192.168.15.104::inst0::INSTR')
    cavity = RohdeSchwarz_SGS100A('cavity_rs',
                                  'TCPIP0::192.168.15.105::inst0::INSTR')
    awg = AWG5014_T3('awg', 'TCPIP0::192.168.15.101::inst0::INSTR', timeout=40)
    mercury = MercuryiPS(name='mercury',
                         address='172.20.10.148',
                         port=7020,
                         axes=['X', 'Y', 'Z'])
    vna = VNA_T3('VNA', 'TCPIP0::192.168.15.103::inst0::INSTR')
    dummy_time = ManualParameter('dummy_time')

    # Add instruments to station so that metadata for them is recorded at
    # each measurement and connections are closed at end of session
    STATION.add_component(deca)
#    STATION.add_component(lockin_2)
    STATION.add_component(vna)
    STATION.add_component(mercury)
    STATION.add_component(alazar)
    STATION.add_component(ave_ctrl)
    STATION.add_component(rec_ctrl)
    STATION.add_component(samp_ctrl)
    STATION.add_component(localos)
    STATION.add_component(cavity)
    STATION.add_component(awg)

    # Set log level
    logger = logging.getLogger()
    logger.setLevel(logging.WARNING)

    # Get parameter values to populate monitor
    print('Querying all instrument parameters for metadata.'
          'This may take a while...')
    start = time.time()

#    lockin_2.acbias()
    deca.dcbias.get()
    deca.lcut.get()
    deca.rcut.get()
    deca.jj.get()
    deca.rplg.get()
    deca.lplg.get()
    mercury.x_fld()
    mercury.y_fld()
    mercury.z_fld()
    vna.rf_power()
    vna.channels.S21.npts()
    vna.channels.S21.power()
    vna.channels.S21.start()
    vna.channels.S21.stop()
    vna.channels.S21.avg()
    vna.channels.S21.bandwidth()
    cavity.status()
    cavity.power()
    cavity.frequency()
    localos.status()
    localos.power()
    localos.frequency()
    awg.state()
    awg.ch1_amp()
    awg.ch1_state()

    end = time.time()

    print("done Querying all instruments took {}".format(end - start))

    # Put parameters into monitor
    Monitor(mercury.x_fld, mercury.y_fld, mercury.z_fld,
               deca.dcbias, deca.lcut, deca.rcut, deca.jj, deca.rplg,
               deca.lplg,
#               lockin_2.acbias,
               samp_ctrl.num_avg, samp_ctrl.int_time, samp_ctrl.int_delay,
               rec_ctrl.num_avg, rec_ctrl.int_time, rec_ctrl.int_delay,
               ave_ctrl.num_avg, ave_ctrl.int_time, ave_ctrl.int_delay,
               awg.state, awg.ch1_amp, awg.ch1_state, alazar.seq_mode,
               cavity.frequency, localos.frequency, cavity.power,
               localos.power, cavity.status, localos.status,
               vna.channels.S21.power, vna.channels.S21.start,
               vna.channels.S21.stop, vna.channels.S21.avg,
               vna.channels.S21.bandwidth, vna.channels.S21.npts)
