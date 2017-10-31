# Module file for conductance measurements with the
# SR830. Implementing the good ideas of Dave Wecker

from typing import Union, Optional
from time import sleep
import numpy as np
import qcodes as qc
from qcodes.instrument.parameter import Parameter
from wrappers.sweep_functions import _do_measurement
from qcodes.instrument_drivers.QDev.QDac_channels import QDac as QDacch

from customised_instruments import SR830_T3

def do2Dconductance(outer_param: Parameter,
                    outer_start: Union[float, int],
                    outer_stop: Union[float, int],
                    outer_npts: int,
                    inner_param: Parameter,
                    inner_start: Union[float, int],
                    inner_stop: Union[float, int],
                    inner_npts: int,
                    lockin: SR830_T3,
                    delay: Optional[float]=None):
    """
    Function to perform a sped-up 2D conductance measurement

    Args:
        outer_param: The outer loop voltage parameter
        outer_start: The outer loop start voltage
        outer_stop: The outer loop stop voltage
        outer_npts: The number of points in the outer loop
        inner_param: The inner loop voltage parameter
        inner_start: The inner loop start voltage
        inner_stop: The inner loop stop voltage
        inner_npts: The number of points in the inner loop
        lockin: The lock-in amplifier to use
        delay: Delay to wait after setting inner parameter before triggering lockin.
          If None will use default delay, otherwise used the supplied.
    """
    station = qc.Station.default

    sr = lockin

    # Validate the instruments
    if sr.name not in station.components:
        raise KeyError('Unknown lock-in! Refusing to proceed until the '
                       'lock-in has been added to the station.')
    if (outer_param._instrument.name not in station.components and
        outer_param._instrument._parent.name not in station.components):
        raise KeyError('Unknown instrument for outer parameter. '
                       'Please add that instrument to the station.')
    if (inner_param._instrument.name not in station.components and
        inner_param._instrument._parent.name not in station.components):
        raise KeyError('Unknown instrument for inner parameter. '
                       'Please add that instrument to the station.')

    tau = sr.time_constant()
    min_delay = 0.002  # what's the physics behind this number?
    if delay is None:
        delay = tau + min_delay
    # Prepare for the first iteration
    # Some of these things have to be repeated during the loop
    sr.buffer_reset()
    sr.buffer_start()
    #sr.buffer_trig_mode('ON')
    sr.buffer_SR('Trigger')
    sr.conductance.shape = (inner_npts,)
    sr.conductance.setpoint_names = (inner_param.name,)
    sr.conductance.setpoint_labels = (inner_param.label,)
    sr.conductance.setpoint_units = ('V',)
    sr.conductance.setpoints = (tuple(np.linspace(inner_start,
                                                  inner_stop,
                                                  inner_npts)),)

    def trigger():
        sleep(delay)
        sr.send_trigger()

    def prepare_buffer():
        # here it should be okay to call ch1_databuffer... I think...
        sr.ch1_databuffer.prepare_buffer_readout()
        # For the dataset/plotting, put in the correct setpoints
        sr.conductance.setpoint_names = (inner_param.name,)
        sr.conductance.setpoint_labels = (inner_param.label,)
        sr.conductance.setpoint_units = ('V',)
        sr.conductance.setpoints = (tuple(np.linspace(inner_start,
                                                      inner_stop,
                                                      inner_npts)),)

    def start_buffer():
        sr.buffer_start()
        sr.conductance.shape = (inner_npts,)  # This is something

    def reset_buffer():
        sr.buffer_reset()

    trig_task = qc.Task(trigger)
    reset_task = qc.Task(reset_buffer)
    start_task = qc.Task(start_buffer)
    inner_loop = qc.Loop(inner_param.sweep(inner_start,
                                           inner_stop,
                                           num=inner_npts)).each(trig_task)
    outer_loop = qc.Loop(outer_param.sweep(outer_start,
                                           outer_stop,
                                           num=outer_npts)).each(start_task,
                                                                 inner_loop,
                                                                 sr.conductance,
                                                                 reset_task)

    set_params = ((inner_param, inner_start, inner_stop),
                  (outer_param, outer_start, outer_stop))
    meas_params = (sr.conductance,)
    prepare_buffer()
    qdac = None
    # ensure that any waveform generator is unbound from the qdac channels that we step if
    # we are stepping the qdac
    if isinstance(inner_param._instrument, QDacch):
        qdacch = inner_param._instrument
        qdacch.slope('Inf')
    if isinstance(outer_param._instrument, QDacch):
        qdacch = outer_param._instrument
        qdacch.slope('Inf')
    if qdac:
        qdac.fast_voltage_set(True)  # now that we have unbound the function generators
                                     # we don't need to do it in the loop
        qdac.voltage_set_dont_wait(False)  # this is un safe and highly experimental
    plot, data = _do_measurement(outer_loop, set_params, meas_params, do_plots=True)
    return plot, data