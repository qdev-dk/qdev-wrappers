import logging

import numpy as np
import matplotlib.pyplot as plt
from qcodes.dataset.measurements import Measurement
from qcodes.dataset.plotting import plot_by_id
from qcodes.dataset.data_set import load_by_id
from qcodes.dataset import experiment_container
from qcodes import ManualParameter
import time
import progressbar
from qdev_wrappers.sag.parameters import TimeParameter

log = logging.getLogger(__name__)


def do2dhalfd_gatemod(param_set_1, start_1, stop_1, num_points_1, delay_1,
             param_set_2, param_set_3, start_2, stop_2, num_points_2, delay_2,
             param_meas2, param_meas3, dac ,gate_chan, mod_amplitude, mod_frequency):
    '''Scan 2D of param_set and measure param_meas.'''
    log.info('Starting scan')
    meas = Measurement()
    refresh_time = 5. # in s
    meas.write_period = refresh_time
    meas.register_parameter(param_set_1)
    param_set_1.post_delay = 0.
    proxy_label = 'Bias'
    proxy_name = 'bias'
    proxy_unit = param_set_2.unit
    proxy_param = ManualParameter(name=proxy_name, label=proxy_label,
                                  unit=proxy_unit)
    meas.register_parameter(proxy_param)
    param_set_2.post_delay = delay_2
    param_set_3.post_delay = delay_2

    for parameter in param_meas2 + param_meas3:
        meas.register_parameter(parameter, setpoints=(param_set_1,
                                                      proxy_param))
    num_points = num_points_1 * num_points_2
    progress_bar = progressbar.ProgressBar(max_value=num_points)
    points_taken = 0
    time.sleep(0.1)

    setpoints_2 = np.linspace(start_2, stop_2, num_points_2)
    with meas.run() as datasaver:
        run_id = datasaver.run_id       
        for set_point1 in np.linspace(start_1, stop_1, num_points_1):
            outputs = [[(param_set_1, set_point1), (proxy_param, set_point2)] \
                       for set_point2 in setpoints_2]
            param_set_1.set(set_point1)
            temp=dac.channels[gate_chan-1].v()
            dac._turnon_sine(gate_chan, mod_amplitude, mod_frequency,-1)
            param_set_2.set(start_2)
            param_set_3.set(0.)
            time.sleep(delay_1)
            for set_point, output in zip(setpoints_2, outputs):
                param_set_2.set(set_point)
                for param_meas in param_meas2:
                    output.append((param_meas, param_meas.get()))
            param_set_2.set(0.)
            param_set_3.set(start_2)
            time.sleep(delay_1)
            for set_point, output in zip(setpoints_2, outputs):
                param_set_3.set(set_point)
                for param_meas in param_meas3:
                    output.append((param_meas, param_meas.get()))
            for output in outputs:
                datasaver.add_result(*output)
            points_taken += num_points_2
            dac._turnoff_sine(gate_chan, temp)
            progress_bar.update(points_taken)

    return run_id

def do2dhalfd_glissandomod(gate_chan_list, delay_1,
             param_set_2, param_set_3, start_2, stop_2, num_points_2, delay_2,
             param_meas2, param_meas3, dac ,gate_chan, mod_amplitude, mod_frequency):
    '''Scan 2D of param_set and measure param_meas.'''
    log.info('Starting scan')
    meas = Measurement()
    refresh_time = 5. # in s
    meas.write_period = refresh_time
    proxy_label = 'Bias'
    proxy_name = 'bias'
    proxy_unit = param_set_2.unit
    proxy_param = ManualParameter(name=proxy_name, label=proxy_label,
                                  unit=proxy_unit)
    gate_param = ManualParameter(name='gate_index', label='finger gate index', unit='')
   
    meas.register_parameter(proxy_param)
    meas.register_parameter(gate_param)
   
    param_set_2.post_delay = delay_2
    param_set_3.post_delay = delay_2

    for parameter in param_meas2 + param_meas3:
        meas.register_parameter(parameter, setpoints=(gate_param,
                                                      proxy_param))
    num_points = len(gate_chan_list) * num_points_2
    progress_bar = progressbar.ProgressBar(max_value=num_points)
    points_taken = 0
    time.sleep(0.1)

    setpoints_2 = np.linspace(start_2, stop_2, num_points_2)
    with meas.run() as datasaver:
        run_id = datasaver.run_id       
        for gate_chan in gate_chan_list:
            outputs = [[(gate_param, gate_chan), (proxy_param, set_point2)] \
                       for set_point2 in setpoints_2]
            temp=dac.channels[gate_chan-1].v()
            dac._turnon_sine(gate_chan, mod_amplitude, mod_frequency,-1)
            param_set_2.set(start_2)
            param_set_3.set(0.)
            time.sleep(delay_1)
            for set_point, output in zip(setpoints_2, outputs):
                param_set_2.set(set_point)
                for param_meas in param_meas2:
                    output.append((param_meas, param_meas.get()))
            param_set_2.set(0.)
            param_set_3.set(start_2)
            time.sleep(delay_1)
            for set_point, output in zip(setpoints_2, outputs):
                param_set_3.set(set_point)
                for param_meas in param_meas3:
                    output.append((param_meas, param_meas.get()))
            for output in outputs:
                datasaver.add_result(*output)
            points_taken += num_points_2
            dac._turnoff_sine(gate_chan, temp)
            progress_bar.update(points_taken)

    return run_id

def do2halfd_2(param_set_1, start_1, stop_1, num_points_1, delay_1,
             param_set_2, param_set_3, start_2, stop_2, num_points_2, delay_2,
             param_meas2, param_meas3,lockins=[],proxy_label=None,proxy_name=None):
    '''Scan 2D of param_set and measure param_meas.'''
    log.info('Starting scan')
    meas = Measurement()
    refresh_time = 1. # in s
    meas.write_period = refresh_time
    meas.register_parameter(param_set_1)
    param_set_1.post_delay = 0.
    if proxy_label==None:
        proxy_label = 'Bias'
    if proxy_name==None:
        proxy_name = 'bias'
    proxy_unit = param_set_2.unit
    proxy_param = ManualParameter(name=proxy_name, label=proxy_label,
                                  unit=proxy_unit)
    meas.register_parameter(proxy_param)
    param_set_2.post_delay = delay_2
    param_set_3.post_delay = delay_2
    if len(lockins)!=0:
        loc_lockin_1=lockins[0]
        lockin_A_1=loc_lockin_1.amplitude()
        loc_lockin_2=lockins[1]
        lockin_A_2=loc_lockin_2.amplitude()
    for parameter in param_meas2 + param_meas3:
        meas.register_parameter(parameter, setpoints=(param_set_1,
                                                      proxy_param))
    num_points = num_points_1 * num_points_2
    # progress_bar = progressbar.ProgressBar(max_value=num_points)
    points_taken = 0
    time.sleep(0.1)

    setpoints_2 = np.linspace(start_2, stop_2, num_points_2)
    with meas.run() as datasaver:
        run_id = datasaver.run_id
        for set_point1 in np.linspace(start_1, stop_1, num_points_1):
            outputs = [[(param_set_1, set_point1), (proxy_param, set_point2)] \
                       for set_point2 in setpoints_2]
            param_set_1.set(set_point1)
            param_set_2.set(start_2)
            param_set_3.set(0.)
            if len(lockins)!=0:
                loc_lockin_2.amplitude(0)
                loc_lockin_1.amplitude(lockin_A_1)
            time.sleep(delay_1)
            for set_point, output in zip(setpoints_2, outputs):
                param_set_2.set(set_point)
                for param_meas in param_meas2:
                    output.append((param_meas, param_meas.get()))
            param_set_2.set(0.)
            param_set_3.set(start_2)
            if len(lockins)!=0:
                loc_lockin_1.amplitude(0)
                loc_lockin_2.amplitude(lockin_A_2)
            time.sleep(delay_1)
            for set_point, output in zip(setpoints_2, outputs):
                param_set_3.set(set_point)
                for param_meas in param_meas3:
                    output.append((param_meas, param_meas.get()))
            for output in outputs:
                datasaver.add_result(*output)
            points_taken += num_points_2
            # progress_bar.update(points_taken)
        if len(lockins)!=0:
            loc_lockin_1.amplitude(lockin_A_1)
            loc_lockin_2.amplitude(lockin_A_2)
    return run_id


def wait_for_setpoint(parameter, setpoint, tolerance):
    last_error = abs(parameter.get() - setpoint)
    while last_error > tolerance:
        new_error = abs(parameter.get() - setpoint)
        last_error = new_error


def ramp_parameter(parameter, start, stop, num_points, delay):
    instrument = parameter.instrument
    scan_time = num_points * delay
    param_range = abs(stop - start)
    safety_factor = 1.5
    ramp_rate = param_range / scan_time / safety_factor
    print('Ramp rate: {:.3g}'.format(ramp_rate))
    # this only works for magnets!
    for magnet in [ix, iy, iz]:
        magnet.ramp_rate(ramp_rate / np.sqrt(2.))
    instrument.block_during_ramp(False)
    instrument.field(stop)


def do1halfd(param_set_1, param_set_2, start, stop, num_points, delay,
             param_meas1, param_meas2):
    '''Scan 1D of param_set and measure param_meas.'''
    meas = Measurement()
    refresh_time = 1. # in s
    meas.write_period = refresh_time
    param_set_1.post_delay = delay
    param_set_2.post_delay = delay
    proxy_label = 'Bias'
    proxy_unit = param_set_1.unit
    proxy_param = ManualParameter(name='proxy', label=proxy_label,
                                  unit=proxy_unit)
    meas.register_parameter(proxy_param)
    for parameter in param_meas1 + param_meas2:
        meas.register_parameter(parameter, setpoints=(proxy_param,))
    # progress_bar = progressbar.ProgressBar(max_value=2 * num_points)
    points_taken = 0
    time.sleep(0.1)

    setpoints = np.linspace(start, stop, num_points)
    with meas.run() as datasaver:
        run_id = datasaver.run_id
        outputs = [[(proxy_param, set_point)] \
                    for set_point in setpoints]
        param_set_1.set(start)
        param_set_2.set(0.)
        time.sleep(delay)
        for set_point, output in zip(setpoints, outputs):
            param_set_1.set(set_point)
            for param_meas in param_meas1:
                output.append((param_meas, param_meas.get()))
        param_set_1.set(0.)
        param_set_2.set(start)
        time.sleep(delay)
        for set_point, output in zip(setpoints, outputs):
            param_set_2.set(set_point)
            for param_meas in param_meas2:
                output.append((param_meas, param_meas.get()))
        for output in outputs:
            datasaver.add_result(*output)
        points_taken += num_points
        # progress_bar.update(points_taken)
    return run_id
