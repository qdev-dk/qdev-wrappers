# -*- coding: utf-8 -*-
"""
Created on Wed Feb 20 13:28:45 2019

@author: AndreasPoeschl
"""

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


def do2threequarterd(param_set_1, start_1, stop_1, num_points_1, delay_1,
             param_set_2, param_set_3, param_set_4, start_2, stop_2, num_points_2, delay_2,
             param_meas2, param_meas3, param_meas4):
    '''Scan 2D of param_set and measure param_meas.'''
    meas = Measurement()
    refresh_time = 1. # in s
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
    param_set_4.post_dalay=delay_2
    for parameter in param_meas2 + param_meas3 + param_meas4:
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
            param_set_2.set(start_2)
            param_set_3.set(0.)
            param_set_4.set(0.)
            time.sleep(delay_1)
            for set_point, output in zip(setpoints_2, outputs):
                param_set_2.set(set_point)  
                for param_meas in param_meas2:
                    output.append((param_meas, param_meas.get()))
            param_set_2.set(0.)
            param_set_3.set(start_2)
            param_set_4.set(0.)
            time.sleep(delay_1)
            for set_point, output in zip(setpoints_2, outputs):
                param_set_3.set(set_point)  
                for param_meas in param_meas3:
                    output.append((param_meas, param_meas.get()))
            param_set_2.set(0.)
            param_set_3.set(0.)
            param_set_4.set(start_2)
            time.sleep(delay_1)
            for set_point, output in zip(setpoints_2, outputs):
                param_set_4.set(set_point)  
                for param_meas in param_meas4:
                    output.append((param_meas, param_meas.get()))
            for output in outputs:
                datasaver.add_result(*output)
            points_taken += num_points_2
            progress_bar.update(points_taken)
    return run_id


def do1threequarterd(param_set_1, param_set_2,param_set_3, start, stop, num_points, delay,
             param_meas1, param_meas2,param_meas3):
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
    for parameter in param_meas1 + param_meas2+param_meas3:
        meas.register_parameter(parameter, setpoints=(proxy_param,))
    progress_bar = progressbar.ProgressBar(max_value=3 * num_points)
    points_taken = 0
    time.sleep(0.1)
    
    setpoints = np.linspace(start, stop, num_points)
    with meas.run() as datasaver:
        run_id = datasaver.run_id
        outputs = [[(proxy_param, set_point)] 
                    for set_point in setpoints]
        param_set_1.set(start)
        param_set_2.set(0.)
        param_set_3.set(0.)
        time.sleep(delay)
        for set_point, output in zip(setpoints, outputs):
            param_set_1.set(set_point)  
            for param_meas in param_meas1:
                output.append((param_meas, param_meas.get()))
        param_set_1.set(0.)
        param_set_2.set(start)
        param_set_3.set(0.)
        time.sleep(delay)
        for set_point, output in zip(setpoints, outputs):
            param_set_2.set(set_point)  
            for param_meas in param_meas2:
                output.append((param_meas, param_meas.get()))
        param_set_1.set(0.)
        param_set_2.set(0)
        param_set_3.set(start)
        time.sleep(delay)
        for set_point, output in zip(setpoints, outputs):
            param_set_3.set(set_point)  
            for param_meas in param_meas3:
                output.append((param_meas, param_meas.get()))
        for output in outputs:
            datasaver.add_result(*output)
        points_taken += num_points
        progress_bar.update(points_taken)
    return run_id