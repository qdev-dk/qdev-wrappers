import numpy as np
import matplotlib.pyplot as plt
from qcodes.dataset.measurements import Measurement
from qcodes.dataset.plotting import plot_by_id
from qcodes.dataset.data_set import load_by_id
from qcodes.dataset import experiment_container
import time
import progressbar


def do0d(*param_meas):
    '''Measure param_meas.'''    
    meas = Measurement()
    refresh_time = 1. # in s
    meas.write_period = refresh_time
    output = []
    for parameter in param_meas:
        meas.register_parameter(parameter, setpoints=())
        output.append([parameter, None])

    with meas.run() as datasaver:
        run_id = datasaver.run_id
        for i, parameter in enumerate(param_meas):
            output[i][1] = parameter.get()
        datasaver.add_result(*output)
    return run_id


def do1d(param_set, start, stop, num_points, delay, *param_meas):
    '''Scan 1D of param_set and measure param_meas.'''
    meas = Measurement()
    refresh_time = 1. # in s
    meas.write_period = refresh_time
    meas.register_parameter(param_set)
    output = []
    param_set.post_delay = delay
    for parameter in param_meas:
        meas.register_parameter(parameter, setpoints=(param_set,))
        output.append([parameter, None])
    progress_bar = progressbar.ProgressBar(max_value=num_points)
    points_taken = 0
    time.sleep(0.1)
    
    with meas.run() as datasaver:
        run_id = datasaver.run_id
        last_time = time.time()
        for set_point in np.linspace(start, stop, num_points):
            param_set.set(set_point)
            for i, parameter in enumerate(param_meas):
                output[i][1] = parameter.get()
            datasaver.add_result((param_set, set_point),
                                 *output)
            points_taken += 1
            current_time = time.time()
            if current_time - last_time >= refresh_time:
                last_time = current_time
                progress_bar.update(points_taken)
        progress_bar.update(points_taken)
    return run_id


def do2d(param_set1, start1, stop1, num_points1, delay1,
         param_set2, start2, stop2, num_points2, delay2,
         *param_meas):
    '''Scan 2D of param_set and measure param_meas.'''
    meas = Measurement()
    refresh_time = 1. # in s
    meas.write_period = refresh_time
    meas.register_parameter(param_set1)
    param_set1.post_delay = delay1
    meas.register_parameter(param_set2)
    param_set2.post_delay = delay2
    output = []
    for parameter in param_meas:
        meas.register_parameter(parameter, setpoints=(param_set1, param_set2))
        output.append([parameter, None])
    progress_bar = progressbar.ProgressBar(max_value=num_points1 * num_points2)
    points_taken = 0
    time.sleep(0.1)
    
    with meas.run() as datasaver:
        run_id = datasaver.run_id
        last_time = time.time()
        for set_point1 in np.linspace(start1, stop1, num_points1):
            param_set1.set(set_point1)
            for set_point2 in np.linspace(start2, stop2, num_points2):
                param_set2.set(set_point2)
                for i, parameter in enumerate(param_meas):
                    output[i][1] = parameter.get()
                datasaver.add_result((param_set1, set_point1),
                                     (param_set2, set_point2),
                                     *output)
                points_taken += 1
                current_time = time.time()
                if current_time - last_time >= refresh_time:
                    last_time = current_time
                    progress_bar.update(points_taken)
        progress_bar.update(points_taken)
    return run_id
