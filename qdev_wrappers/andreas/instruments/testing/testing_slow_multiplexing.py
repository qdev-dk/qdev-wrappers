#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov  7 14:46:08 2019

@author: andreasposchl
"""

from qcodes.logger import start_all_logging
start_all_logging()

import qcodes as qc
from qcodes.dataset.experiment_container import load_or_create_experiment, Experiment
from qcodes.dataset.data_set import load_by_id
from qcodes.dataset.data_export import (get_data_by_id, flatten_1D_data_for_plot,
                          get_1D_plottype, get_2D_plottype, reshape_2D_data,
                          _strings_as_ints)
from qcodes.dataset.database import initialise_database
import time
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from functools import partial

from typing import Sequence, Callable

#from qdev_wrappers.sag.instruments.SR830_ext import soft_sweep
#from lockin_buffers import call1d
from qdev_wrappers.sag.measurements.do2halfd import (do2halfd, do1halfd)
from qdev_wrappers.sag.measurements.sweep import (do2d,do1d,do0d,do1d_time)
#from qdev_wrappers.sag.measurements.sweep_temp1 import (do2d,do1d,do0d,do1d_time)
#from qdev_wrappers.customised_instruments.SR830_ext import soft_sweep
from qdev_wrappers.station_configurator import StationConfigurator
#from qdev_wrappers.dataset.doNd import do1d, do2d, do0d
from qdev_wrappers.dataset.plotting_tools import plot_id, save_image
from qdev_wrappers.sag.parameters.conductance import Conductance,ThirdHarmonic, SecondHarmonic
from qdev_wrappers.sag.parameters.amplified import Amplified
from qdev_wrappers.sag.parameters.currentcost import CurrentCost
from qcodes.instrument_drivers.devices import VoltageDivider
from qdev_wrappers.sag.parameters.offset import Offset


station = qc.Station()
qc.config['core']['db_location']='.\test_experiments.db'
initialise_database()  # just in case no database file exists

# Init instruments

scfg = StationConfigurator('testing_station.yaml', station=station)

# Init scope

scope=scfg.load_instrument('scope')
wg_1=scfg.load_instrument('wg_1')


# try to acquire trace from the scope
# figure out different settings, npts, sampling frequency, input range, etc.

scope.prepare_curvedata()


# make the scope be triggered by the waveform generator wg



# now use the demodulator written by dominik, to demodulate the signal, look if it looks fine
# check what the amplitude is, is there noise, etc.
# compare with direct lockin measurement. Is the amplitude the same?
# does it return x and y? how long does it take?



# implement it for a measurement with a convenient definition of frequencies, filters
# harmonics, etc.


