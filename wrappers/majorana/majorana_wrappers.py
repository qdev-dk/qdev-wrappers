from time import sleep
from functools import partial

from qcodes.instrument_drivers.devices import VoltageDivider
from qcodes.instrument_drivers.QDev.QDac_channels import QDacChannel
from qcodes.instrument.parameter import ManualParameter
from qcodes.instrument.parameter import StandardParameter
from qcodes.utils.validators import Enum

import re

import logging
import os
import time

from wrappers.plot_functions import _plot_setup, _save_individual_plots
from wrappers.sweep_functions import  do1d, do2d
from wrappers.show_num import show_num
from reload_settings import used_channels

##################################################
# Helper functions and wrappers


def print_voltages():
    """
    Print qDac voltages
    """

    max_col_width = 38
    for channel in used_channels():
        col_width = max_col_width - len(qdac.channels[channel-1].v.label)
        mssg = ('Ch {: >2} - {} '.format(channel, qdac.channels[channel-1].v.label) +
                ': {:>{col_width}}'.format(qdac.channels[channel-1].v.get(),
                                           col_width=col_width))
        print(mssg)


def set_all_voltages(voltage):
    """
    Set all AT SAMPLE voltages from QDac channels to the given voltage
    """
    qdac.channels.v(voltage)


def _unassign_qdac_slope(sweep_parameter):
    """
    Helper function for do1D and do2D to unassign QDac slopes

    The sweep_parameter is a qdac channel
    """

    if not isinstance(sweep_parameter._parent, QDac):
        raise ValueError("Can't unassign slope from a non-qdac instrument!")


    slope_parameter = sweep_parameter.slope
    slope_parameter('Inf')


def reset_qdac(sweep_parameters):
    """
    Reset the qdac channels (unassigns slopes)
    Input amy be a list of sweep_parameter or a single one
    """
    if not isinstance(sweep_parameters, list):
        sweep_parameters = [sweep_parameters]

    for swp in sweep_parameters:
        try:
            if isinstance(swp, VoltageDivider):
                # check wether we are dealing with a voltage divider, and if so,
                # dig out the qdac parameter
                orig_channel_name = swp._instrument.name
                print(orig_channel_name)
                channel_id = int(re.findall('\d+', orig_channel_name)[0])
                print(channel_id)
                channel = qdac.channels[channel_id-1]
                _unassign_qdac_slope(channel)
            else:
                channel = swp._instrument
                _unassign_qdac_slope(channel)
        except ValueError:
            pass


def prepare_qdac(qdac_channel, start, stop, n_points, delay, ramp_slope=None):
    """
    Args:
        qdac_channel:  Instrument to sweep over
        start:  Start of sweep
        stop:  End of sweep
        division:  Spacing between values
        delay:  Delay at every step
        ramp_slope:

    Return:
        additional_delay: Additional delay we need to add in the Loop
                          in order to take into account the ramping
                          time of the QDac
    """

    if ramp_slope is None:
        QDAC_SLOPES = qdac_slopes()
        channel_id = int(re.findall('\d+', qdac_channel.name)[0])
        ramp_slope = QDAC_SLOPES[channel_id]

    qdac_channel.slope(ramp_slope)

    try:
        init_ramp_time = abs(start-qdac_channel.get())/ramp_slope
    except TypeError:
        init_ramp_time = 0

    qdac_channel.v.set(start)
    time.sleep(init_ramp_time)

    try:
        additional_delay_perPoint = (abs(stop-start)/n_points)/ramp_slope
    except TypeError:
        additional_delay_perPoint = 0

    return additional_delay_perPoint, ramp_slope


def do1d_M(inst_set, start, stop, n_points, delay, *inst_meas, ramp_slope=None):
    """
    Args:
        inst_set:  Parameter to sweep over
        start:  Start of sweep
        stop:  End of sweep
        division:  Spacing between values
        delay:  Delay at every step
        *inst_meas:  any number of instrument to measure
        ramp_slope:

    Returns:
        plot, data : returns the plot and the dataset

    """
    if isinstance(inst_set._instrument, QDacChannel):
        ramp_qdac(inst_set._instrument, start, ramp_slope)

    plot, data = do1d(inst_set, start, stop, n_points, delay, *inst_meas)

    return plot, data


def do2d_M(inst_set, start, stop, n_points, delay, inst_set2, start2, stop2,
           n_points2, delay2, *inst_meas, ramp_slope1=None, ramp_slope2=None):
    """
    Args:
        inst_set:  Instrument to sweep over
        start:  Start of sweep
        stop:  End of sweep
        division:  Spacing between values
        delay:  Delay at every step
        inst_set_2:  Second instrument to sweep over
        start_2:  Start of sweep for second intrument
        stop_2:  End of sweep for second intrument
        division_2:  Spacing between values for second intrument
        delay_2:  Delay at every step for second intrument
        *inst_meas:
        ramp_slope:

    Returns:
        plot, data : returns the plot and the dataset
    """
    if isinstance(inst_set2._instrument, QDacChannel):
        ramp_qdac(inst_set2._instrument, start, ramp_slope2)

    if isinstance(inst_set._instrument, QDacChannel):
        ramp_qdac(inst_set._instrument, start, ramp_slope1)

    for inst in inst_meas:
        if getattr(inst, "setpoints", False):
            raise ValueError("3d plotting is not supported")

    plot, data = do2d(inst_set, start, stop, n_points, delay, inst_set2, start2, stop2, n_points2, delay2, *inst_meas)

    return plot, data

def ramp_qdac(chan, target_voltage, slope=None):
    """
    Ramp a qdac channel. Blocking.

    Args:
        chan: QDac Channel
        target_voltage (float): Voltage to ramp to
        slope (float): The slope in (V/s)
    """
    if slope is None:
        try:
            QDAC_SLOPES = qdac_slopes()
            channel_id = int(re.findall('\d+', chan.name)[0])
            slope = QDAC_SLOPES[channel_id]
        except KeyError:
            raise ValueError('No slope found in QDAC_SLOPES. '
                             'Please provide a slope!')

    # Make the ramp blocking, so that we may unassign the slope
    ramp_time = abs(chan.v.get() -
                    target_voltage)/slope + 0.03

    chan.slope.set(slope)
    chan.v.set(target_voltage)
    sleep(ramp_time)
    chan.slope.set('Inf')


def ramp_several_qdac_channels(loc, target_voltage, slope=None):
    """
    Ramp several QDac channels to the same value

    Args:
        loc (list): List of channels to ramp
        target_voltage (float): Voltage to ramp to
        slope (float): The slope in (V/s)
    """
    for ch in loc:
        ramp_qdac(ch, target_voltage, slope)