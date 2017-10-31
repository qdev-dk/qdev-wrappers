import qcodes as qc
import os
import time
import logging
import re
import numpy as np
from functools import partial

import matplotlib as mpl
import matplotlib.pyplot as plt
mpl.rcParams['figure.figsize'] = (8, 3)
mpl.rcParams['figure.subplot.bottom'] = 0.15 
mpl.rcParams['font.size'] = 8

from qcodes.utils.configreader import Config
from qcodes.utils.natalie_wrappers.file_setup import your_init

from majorana_wrappers import *
from reload_settings import *
from customised_instruments import *


from qcodes.instrument_drivers.Harvard.Decadac import Decadac
from qcodes.instrument_drivers.stanford_research.SR830 import SR830
from qcodes.instrument_drivers.stanford_research.SR830 import ChannelBuffer
# from qcodes.instrument_drivers.Keysight.Keysight_33500B import Keysight_33500B
# from qcodes.instrument_drivers.Keysight.Keysight_34465A import Keysight_34465A
# from qcodes.instrument_drivers.ZI.ZIUHFLI import ZIUHFLI
from qcodes.instrument_drivers.devices import VoltageDivider

# import qcodes.instrument_drivers.tektronix.Keithley_2600 as keith
# import qcodes.instrument_drivers.rohde_schwarz.SGS100A as sg
# import qcodes.instrument_drivers.tektronix.AWG5014 as awg
# from modules.pulsebuilding import broadbean as bb
from qcodes.instrument_drivers.oxford.mercuryiPS import MercuryiPS
# import qcodes.instrument_drivers.HP .HP8133A as hpsg
import qcodes.instrument_drivers.rohde_schwarz.ZNB as vna

from qcodes.utils.natalie_wrapper.configreader import Config
from qcodes.utils.validators import Numbers
import logging
import re
import time
from functools import partial
import atexit

from conductance_measurements import do2Dconductance

if __name__ == '__main__':

    #logging.basicConfig(filename=os.path.join(os.getcwd(), 'pythonlog.txt'), level=logging.DEBUG)

    init_log = logging.getLogger(__name__)

    config = Config('D:\MajoranacQED\Majorana\sample.config')
    Config.default = config

    def close_station(station):
        for comp in station.components:
            print("Closing connection to {}".format(comp))
            try:
                qc.Instrument.find_instrument(comp).close()
            except KeyError:
                pass


    if qc.Station.default:
        close_station(qc.Station.default)

    # Initialisation of intruments
    deca = Decadac_T3('Decadac', 'ASRL1::INSTR', config)

    # lockin_1 = SR830_T10('lockin_1', 'GPIB0::1::INSTR')
    lockin_2 = SR830_T3('lockin_2', 'GPIB0::2::INSTR', config)

    # zi = ZIUHFLI_T10('ziuhfli', 'dev2189')
    # keysightgen_left = Keysight_33500B('keysight_gen_left', 'TCPIP0::192.168.15.101::inst0::INSTR')
    # keysightgen_left.add_function('sync_phase',call_cmd='SOURce1:PHASe:SYNChronize')

    #keithleybot_a = keith.Keithley_2600('keithley_bot','TCPIP0::192.168.15.115::inst0::INSTR',"a")
    # awg1 = awg.Tektronix_AWG5014('AWG1','TCPIP0::192.168.15.105::inst0::INSTR',timeout=40)
    # sg1 = sg.RohdeSchwarz_SGS100A("sg1","TCPIP0::192.168.15.107::inst0::INSTR")
    # sg1.frequency.set_validator(Numbers(1e5,43.5e9))  # SMF100A can go to 43.5 GHz.

    mercury = MercuryiPS(name='mercury',
                         address='172.20.10.148',
                         port=7020,
                         axes=['X', 'Y', 'Z'])

    v1 = vna.ZNB('VNA', 'TCPIP0::192.168.15.103::inst0::INSTR', init_s_params=False)
    v1.add_channel('S21')
   
    print('Querying all instrument parameters for metadata.'
          'This may take a while...')

    start = time.time()
    STATION = qc.Station( lockin_2, mercury, deca, v1)
                        # lockin_1, deca)
                         # keysightgen_left, keysightgen_mid, keithleybot_a,
                         # keysightdmm_mid, keysightdmm_bot,
                         # keysightdmm_top, keysightdmm_mid, keysightdmm_bot,
                         # awg1, zi, sg1, hpsg1)# keysightgen_pulse)

    end = time.time()
    print("Querying took {} s".format(end-start))
    # Initialisation of the experiment

    end = time.time()
    print("done Querying all instruments took {}".format(end-start))
    your_init("./data", "natalie_playing", STATION,
            display_pdf=False, display_individual_pdf=False)

    logger = logging.getLogger()
    logger.setLevel(logging.WARNING)

    #make sure the right values will be displayed in monitor when firing it up
    lockin_2.acbias()
    deca.dcbias.get()
    deca.lcut.get()
    deca.rcut.get()
    deca.jj.get()
    deca.rplg.get()
    deca.lplg.get()
                
    qc.Monitor(mercury.x_fld, mercury.y_fld, mercury.z_fld,
                deca.dcbias, deca.lcut, deca.rcut, deca.jj, deca.rplg,
                deca.lplg,
                lockin_2.acbias)#, v1.channels.S21.power
                #)

    # lockin_1.acfactor = float(config.get('Gain settings','ac factor'))
    lockin_2.acfactor = float(config.get('Gain settings',
                                              'ac factor'))


    # lockin_1.ivgain = float(config.get('Gain settings', 'iv gain'))
    lockin_2.ivgain = float(config.get('Gain settings',
                                            'iv gain'))



    # Try to close all instruments when exiting
    atexit.register(close_station, STATION)
