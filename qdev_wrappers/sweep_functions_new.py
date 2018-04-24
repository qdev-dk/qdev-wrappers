import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as anim
from qcodes.dataset.measurements import Measurement
from qcodes.dataset.plotting import plot_by_id
from qcodes.dataset.data_set import load_by_id
from time import sleep, time
import matplotlib.animation as animation

        
def load_axes(run_id):
    data = load_by_id(run_id)
    if data:
        axes, cbaxes = plot_by_id(run_id)
        return axes, cbaxes
    else:
        return None, None

    
def redraw(run_id, axes, cbaxes=None):
    pause_time = 0.001
    for axis in axes:
        axis.clear()
    for cbaxis in cbaxes:
        if cbaxis is not None:
            cbaxis.remove()
    axes, cbaxes = plot_by_id(run_id, axes)
    plt.pause(pause_time)
    return axes, cbaxes


def do0d(*param_meas):
    meas = Measurement()
    output = []
    for parameter in param_meas:
        meas.register_parameter(parameter, setpoints=())
        output.append([parameter, None])

    axes = None
    with meas.run() as datasaver:
        run_id = datasaver.run_id
        for i, parameter in enumerate(param_meas):
            output[i][1] = parameter.get()
        datasaver.add_result(*output)
        if axes is None:
            axes, cbaxes = load_axes(run_id)
        else:
            axes, cbaxes = redraw(run_id, axes, cbaxes)
    return run_id


def do1d(param_set, start, stop, num_points, delay, *param_meas):
    '''
    do1D enforces a simple relationship between measured parameters
    and set parameters. For anything more complicated this should be
    reimplemented from scratch.
    '''
    meas = Measurement()
    meas.register_parameter(param_set)
    output = []
    param_set.post_delay = delay
    for parameter in param_meas:
        meas.register_parameter(parameter, setpoints=(param_set,))
        output.append([parameter, None])

    axes = None
    with meas.run() as datasaver:
        run_id = datasaver.run_id
        for set_point in np.linspace(start, stop, num_points):
            param_set.set(set_point)
            for i, parameter in enumerate(param_meas):
                output[i][1] = parameter.get()
            datasaver.add_result((param_set, set_point),
                                 *output)
            if axes is None:
                axes, cbaxes = load_axes(run_id)
            else:
                axes, cbaxes = redraw(run_id, axes, cbaxes)
    return run_id


def do2d(param_set1, start1, stop1, num_points1, delay1,
         param_set2, start2, stop2, num_points2, delay2,
         *param_meas):
    meas = Measurement()
    meas.register_parameter(param_set1)
    param_set1.post_delay = delay1
    meas.register_parameter(param_set2)
    param_set1.post_delay = delay2
    output = []
    for parameter in param_meas:
        meas.register_parameter(parameter, setpoints=(param_set1, param_set2))
        output.append([parameter, None])

    axes = None
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
                if axes is None:
                    axes, cbaxes = load_axes(run_id)
                else:
                    axes, cbaxes = redraw(run_id, axes, cbaxes)
    dataid = datasaver.run_id
    return dataid