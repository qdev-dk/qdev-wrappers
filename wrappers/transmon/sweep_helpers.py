import qcodes as qc
from wrappers.sweep_functions import _do_measurement, \
    _select_plottables


def measure(meas_param, do_plots=True):
    """
    Function which measures the specified parameter and optionally
    plots the results.

    Args:
        meas_param: parameter to measure
        do_plots: Default True: If False no plots are produced.
            Data is still saved and can be displayed with show_num.

    Returns:
        data (qcodes dataset)
        plot: QT plot
    """
    measurement = qc.Measure(meas_param)
    set_params = ((None, None, None),)
    meas_params = _select_plottables(meas_param)
    plot, data = _do_measurement(measurement, set_params, meas_params,
                                 do_plots=do_plots)

    return data, plot


def sweep1d(meas_param, sweep_param, start, stop, step, delay=0.01,
            do_plots=True):
    """
    Function which does a 1 dimensional sweep and optionally plots the results.

    Args:
        meas_param: parameter which we want the value of at each point
        sweep_param: parameter to be swept in outer loop (default on y axis)
        start: starting value for sweep_param1
        stop: final value for sweep_param1
        step: value to step sweep_param1 by
        delay (default 0.01): mimimum time to spend on each point
        do_plots: Default True: If False no plots are produced.
            Data is still saved and can be displayed with show_num.

    Returns:
        data (qcodes dataset)
        plot: QT plot
    """
    loop = qc.Loop(sweep_param.sweep(
        start, stop, step), delay).each(meas_param)

    set_params = ((sweep_param, start, stop),)
    meas_params = _select_plottables(meas_param)

    plot, data = _do_measurement(loop, set_params, meas_params,
                                 do_plots=do_plots)

    return data, plot


def sweep2d(meas_param, sweep_param1, start1, stop1, step1,
            sweep_param2, start2, stop2, step2, delay=0.01,
            do_plots=True):
    """
    Function which does a 2 dimensional sweep and optionally plots the results.

    Args:
        meas_param: parameter which we want the value of at each point
        sweep_param1: parameter to be swept in outer loop (default on y axis)
        start1: starting value for sweep_param1
        stop1: final value for sweep_param1
        step1: value to step sweep_param1 by
        sweep_param2: parameter to be swept in inner loop (default on x axis)
        start2: starting value for sweep_param2
        stop2: final value for sweep_param2
        step2: value to step sweep_param2 by
        delay (default 0.01): mimimum time to spend on each point
        do_plots: Default True: If False no plots are produced.
            Data is still saved and can be displayed with show_num.

    Returns:
        data (qcodes dataset)
        plot: QT plot
    """
    innerloop = qc.Loop(sweep_param2.sweep(
        start2, stop2, step2), delay).each(meas_param)

    outerloop = qc.Loop(sweep_param1.sweep(
        start1, stop1, step1), delay).each(innerloop)

    set_params = ((sweep_param1, start1, stop1),
                  (sweep_param2, start2, stop2))

    meas_params = _select_plottables(meas_param)

    plot, data = _do_measurement(outerloop, set_params, meas_params,
                                 do_plots=do_plots)

    return data, plot
