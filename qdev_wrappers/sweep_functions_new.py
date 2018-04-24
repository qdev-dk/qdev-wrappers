import numpy as np
import matplotlib.pyplot as plt
from qcodes.dataset.measurements import Measurement
from qcodes.dataset.plotting import plot_by_id
from qcodes.dataset.data_set import load_by_id
from qcodes.dataset import experiment_container


def make_title(dataset):
    '''Make a descriptive title for the dataset.'''
    experiment = experiment_container.load_experiment(dataset.exp_id)
    title = '{} on {} - {}.{} ({})'
    title = title.format(experiment.name, experiment.sample_name,
                         experiment.exp_id, dataset.counter, dataset.run_id)
    return title
        

def redraw(run_id, axes, cbars):
    '''Call plot_by_id to plot the available data on axes.'''
    pause_time = 0.001
    dataset = load_by_id(run_id)
    if not dataset: # there is not data available yet
        axes, cbars = [], []
    elif not axes: # there is data available but no plot yet
        axes, cbars = plot_by_id(run_id)
    else: # there is a plot already
        for axis in axes:
            axis.clear()
        for cbar in cbars:
            if cbar is not None:
                cbar.remove()
        axes, cbars = plot_by_id(run_id, axes)
        title = make_title(dataset)
        for axis in axes:
            axis.set_title(title)
        plt.pause(pause_time)
    return axes, cbars


def do0d(*param_meas):
    '''Measure param_meas, with basic real-time plotting.
    
    .. todo:: Refactor plot_by_id and retrieve not the whole axes but only
    the data. This way you could zoom in and manipulate the plot without it
    being resized every frame.'''
    
    meas = Measurement()
    meas.write_period = 1. # update rate in s
    output = []
    for parameter in param_meas:
        meas.register_parameter(parameter, setpoints=())
        output.append([parameter, None])

    axes, cbars = [], []
    with meas.run() as datasaver:
        run_id = datasaver.run_id
        for i, parameter in enumerate(param_meas):
            output[i][1] = parameter.get()
        datasaver.add_result(*output)
        axes, cbars = redraw(run_id, axes, cbars)
    return run_id


def do1d(param_set, start, stop, num_points, delay, *param_meas):
    '''Scan param_set and measure param_meas, with basic real-time plotting.
    
    .. todo:: Refactor plot_by_id and retrieve not the whole axes but only
    the data. This way you could zoom in and manipulate the plot without it
    being resized every frame.'''
    
    meas = Measurement()
    meas.write_period = 1. # update rate in s
    meas.register_parameter(param_set)
    output = []
    param_set.post_delay = delay
    for parameter in param_meas:
        meas.register_parameter(parameter, setpoints=(param_set,))
        output.append([parameter, None])

    axes, cbars = [], []
    with meas.run() as datasaver:
        run_id = datasaver.run_id
        for set_point in np.linspace(start, stop, num_points):
            param_set.set(set_point)
            for i, parameter in enumerate(param_meas):
                output[i][1] = parameter.get()
            datasaver.add_result((param_set, set_point),
                                 *output)
            axes, cbars = redraw(run_id, axes, cbars)
    return run_id


def do2d(param_set1, start1, stop1, num_points1, delay1,
         param_set2, start2, stop2, num_points2, delay2,
         *param_meas):
    '''Scan param_set and measure param_meas, with basic real-time plotting.
    
    .. todo:: Refactor plot_by_id and retrieve not the whole axes but only
    the data. This way you could zoom in and manipulate the plot without it
    being resized every frame.'''
    
    meas = Measurement()
    meas.write_period = 1. # update rate in s
    meas.register_parameter(param_set1)
    param_set1.post_delay = delay1
    meas.register_parameter(param_set2)
    param_set1.post_delay = delay2
    output = []
    for parameter in param_meas:
        meas.register_parameter(parameter, setpoints=(param_set1, param_set2))
        output.append([parameter, None])

    axes, cbars = [], []
    with meas.run() as datasaver:
        run_id = datasaver.run_id
        for set_point1 in np.linspace(start1, stop1, num_points1):
            param_set1.set(set_point1)
            for set_point2 in np.linspace(start2, stop2, num_points2):
                param_set2.set(set_point2)
                for i, parameter in enumerate(param_meas):
                    output[i][1] = parameter.get()
                datasaver.add_result((param_set1, set_point1),
                                     (param_set2, set_point2),
                                     *output)
                axes, cbars = redraw(run_id, axes, cbars)
    return run_id