import matplotlib.pyplot as plt
from os.path import sep
from typing import Optional, Tuple
from pyqtgraph.multiprocess.remoteproxy import ClosedError

import qcodes as qc
from qcodes.instrument.visa import VisaInstrument
from qcodes.plots.pyqtgraph import QtPlot
from qcodes.data.data_set import DataSet
from qcodes.loops import Loop
from qcodes.measure import Measure
from qdev_wrappers.file_setup import CURRENT_EXPERIMENT
from qdev_wrappers.file_setup import pdfdisplay
from qdev_wrappers.plot_functions import _plot_setup, \
    _save_individual_plots
from qdev_wrappers.device_annotator.device_image import save_device_image


import logging
log = logging.getLogger(__name__)


def _flush_buffers(*params):
    """
    If possible, flush the VISA buffer of the instrument of the
    provided parameters. The params can be instruments as well.

    Supposed to be called inside doNd like so:
    _flush_buffers(inst_set, *inst_meas)
    """

    for param in params:
        if hasattr(param, '_instrument'):
            inst = param._instrument
            if hasattr(inst, 'visa_handle'):
                status_code = inst.visa_handle.clear()
                if status_code is not None:
                    log.warning("Cleared visa buffer on "
                                "{} with status code {}".format(inst.name,
                                                                status_code))
        elif isinstance(param, VisaInstrument):
            inst = param
            status_code = inst.visa_handle.clear()
            if status_code is not None:
                log.warning("Cleared visa buffer on "
                            "{} with status code {}".format(inst.name,
                                                            status_code))


def _select_plottables(tasks):
    """
    Helper function to select plottable tasks. Used inside the doNd functions.

    A task is here understood to be anything that the qc.Loop 'each' can eat.
    """
    # allow passing a single task
    if not hasattr(tasks, '__iter__'):
        tasks = (tasks,)

    # is the following check necessary AND sufficient?
    plottables = [task for task in tasks if hasattr(task, '_instrument')]

    return tuple(plottables)


def _do_measurement_single(measurement: Measure, meas_params: tuple,
                           do_plots: Optional[bool]=True,
                           use_threads: bool=True) -> Tuple[QtPlot, DataSet]:

    try:
        parameters = list(meas_params)
        _flush_buffers(*parameters)
        interrupted = False

        try:
            data = measurement.run(use_threads=use_threads)
        except KeyboardInterrupt:
            interrupted = True
            print("Measurement Interrupted")

        if do_plots:
            plot, _ = _plot_setup(data, meas_params)
            # Ensure the correct scaling before saving
            plot.autorange()
            plot.save()
            if 'pdf_subfolder' in CURRENT_EXPERIMENT:
                plt.ioff()
                pdfplot, num_subplots = _plot_setup(
                    data, meas_params, useQT=False)
                # pad a bit more to prevent overlap between
                # suptitle and title
                pdfplot.rescale_axis()
                pdfplot.fig.tight_layout(pad=3)
                title_list = plot.get_default_title().split(sep)
                title_list.insert(-1, CURRENT_EXPERIMENT['pdf_subfolder'])
                title = sep.join(title_list)

                pdfplot.save("{}.pdf".format(title))
                if (pdfdisplay['combined'] or
                        (num_subplots == 1 and pdfdisplay['individual'])):
                    pdfplot.fig.canvas.draw()
                    plt.show()
                else:
                    plt.close(pdfplot.fig)
                if num_subplots > 1:
                    _save_individual_plots(data, meas_params,
                                           pdfdisplay['individual'])
        else:
            plot = None

        # add the measurement ID to the logfile
        with open(CURRENT_EXPERIMENT['logfile'], 'a') as fid:
            print("#[QCoDeS]# Saved dataset to: {}".format(data.location),
                  file=fid)
        if interrupted:
            raise KeyboardInterrupt
    except:
        log.exception("Exception in doO")
        raise
    return plot, data


def _do_measurement(loop: Loop, set_params: tuple, meas_params: tuple,
                    do_plots: Optional[bool]=True,
                    use_threads: bool=True) -> Tuple[QtPlot, DataSet]:
    """
    The function to handle all the auxiliary magic of the T10 users, e.g.
    their plotting specifications, the device image annotation etc.
    The input loop should just be a loop ready to run and perform the desired
    measurement. The two params tuple are used for plotting.
    Args:
        loop: The QCoDeS loop object describing the actual measurement
        set_params: tuple of tuples. Each tuple is of the form
            (param, start, stop)
        meas_params: tuple of parameters to measure
        do_plots: Whether to do a live plot
        use_threads: Whether to use threads to parallelise simultaneous
            measurements. If only one thing is being measured at the time
            in loop, this does nothing.
    Returns:
        (plot, data)
    """
    try:
        parameters = [sp[0] for sp in set_params] + list(meas_params)
        _flush_buffers(*parameters)

        # startranges for _plot_setup
        try:
            startranges = {}
            for sp in set_params:
                minval = min(sp[1], sp[2])
                maxval = max(sp[1], sp[2])
                startranges[sp[0].full_name] = {'max': maxval, 'min': minval}
        except Exception:
            startranges = None

        interrupted = False

        data = loop.get_data_set()

        if do_plots:
            try:
                plot, _ = _plot_setup(
                    data, meas_params, startranges=startranges)
            except (ClosedError, ConnectionError):
                log.warning('Remote process crashed png will not be saved')
        else:
            plot = None
        try:
            if do_plots:
                _ = loop.with_bg_task(plot.update).run(use_threads=use_threads)
            else:
                _ = loop.run(use_threads=use_threads)
        except KeyboardInterrupt:
            interrupted = True
            print("Measurement Interrupted")
        if do_plots:
            # Ensure the correct scaling before saving
            try:
                plot.autorange()
                plot.save()
            except (ClosedError, ConnectionError):
                log.warning('Remote process crashed png will not be saved')

            if any(k in CURRENT_EXPERIMENT for k in ('pdf_subfolder', 'png_subfolder')):
                plt.ioff()
                pdfplot, num_subplots = _plot_setup(
                    data, meas_params, useQT=False)
                # pad a bit more to prevent overlap between
                # suptitle and title
                pdfplot.rescale_axis()
                pdfplot.fig.tight_layout(pad=3)

                if 'pdf_subfolder' in CURRENT_EXPERIMENT:
                    title_list = plot.get_default_title().split(sep)
                    title_list.insert(-1, CURRENT_EXPERIMENT['pdf_subfolder'])
                    title = sep.join(title_list)
                    pdfplot.save("{}.pdf".format(title))

                if 'png_subfolder' in CURRENT_EXPERIMENT:
                    # Hack to save PNG also
                    title_list_png = plot.get_default_title().split(sep)
                    title_list_png.insert(-1,
                                          CURRENT_EXPERIMENT['png_subfolder'])
                    title_png = sep.join(title_list_png)

                    plt.savefig("{}.png".format(title_png), dpi=500)

                if (pdfdisplay['combined'] or
                        (num_subplots == 1 and pdfdisplay['individual'])):
                    pdfplot.fig.canvas.draw()
                    plt.show()
                else:
                    plt.close(pdfplot.fig)
                if num_subplots > 1:
                    _save_individual_plots(data, meas_params,
                                           pdfdisplay['individual'])
                plt.ion()
        if CURRENT_EXPERIMENT.get('device_image'):
            log.debug('Saving device image')
            save_device_image(tuple(sp[0] for sp in set_params))

        # add the measurement ID to the logfile
        with open(CURRENT_EXPERIMENT['logfile'], 'a') as fid:
            print("#[QCoDeS]# Saved dataset to: {}".format(data.location),
                  file=fid)
        if interrupted:
            raise KeyboardInterrupt
    except:
        log.exception("Exception in doND")
        raise
    return plot, data


def do1d(inst_set, start, stop, num_points, delay, *inst_meas, do_plots=True,
         use_threads=True):
    """

    Args:
        inst_set:  Instrument to sweep over
        start:  Start of sweep
        stop:  End of sweep
        num_points:  Number of steps to perform
        delay:  Delay at every step
        *inst_meas:  any number of instrument to measure and/or tasks to
          perform at each step of the sweep
        do_plots: Default True: If False no plots are produced.
            Data is still saved
             and can be displayed with show_num.
        use_threads: If True and if multiple things are being measured,
            multiple threads will be used to parallelise the waiting.

    Returns:
        plot, data : returns the plot and the dataset

    """

    loop = qc.Loop(inst_set.sweep(start,
                                  stop,
                                  num=num_points), delay).each(*inst_meas)

    set_params = (inst_set, start, stop),
    meas_params = _select_plottables(inst_meas)

    plot, data = _do_measurement(loop, set_params, meas_params,
                                 do_plots=do_plots, use_threads=use_threads)
    data.data_num = qc.data.data_set.DataSet.location_provider.counter
    return plot, data


def do1dDiagonal(inst_set, inst2_set, start, stop, num_points,
                 delay, start2, slope, *inst_meas, do_plots=True,
                 use_threads=True):
    """
    Perform diagonal sweep in 1 dimension, given two instruments

    Args:
        inst_set:  Instrument to sweep over
        inst2_set: Second instrument to sweep over
        start:  Start of sweep
        stop:  End of sweep
        num_points:  Number of steps to perform
        delay:  Delay at every step
        start2:  Second start point
        slope:  slope of the diagonal cut
        *inst_meas:  any number of instrument to measure
        do_plots: Default True: If False no plots are produced.
            Data is still saved and can be displayed with show_num.
        use_threads: If True and if multiple things are being measured,
            multiple threads will be used to parallelise the waiting.

    Returns:
        plot, data : returns the plot and the dataset

    """

    # (WilliamHPNielsen) If I understand do1dDiagonal correctly, the inst2_set
    # is supposed to be varied secretly in the background
    set_params = ((inst_set, start, stop),)
    meas_params = _select_plottables(inst_meas)

    slope_task = qc.Task(inst2_set, (inst_set) *
                         slope + (slope * start - start2))

    loop = qc.Loop(inst_set.sweep(start, stop, num=num_points),
                   delay).each(slope_task, *inst_meas, inst2_set)

    plot, data = _do_measurement(loop, set_params, meas_params,
                                 do_plots=do_plots, use_threads=use_threads)
    data.data_num = qc.data.data_set.DataSet.location_provider.counter
    return plot, data


def do2d(inst_set, start, stop, num_points, delay,
         inst_set2, start2, stop2, num_points2, delay2,
         *inst_meas, do_plots=True, use_threads=True):
    """

    Args:
        inst_set:  Instrument to sweep over
        start:  Start of sweep
        stop:  End of sweep
        num_points:  Number of steps to perform
        delay:  Delay at every step
        inst_set2:  Second instrument to sweep over
        start2:  Start of sweep for second instrument
        stop2:  End of sweep for second instrument
        num_points2:  Number of steps to perform
        delay2:  Delay at every step for second instrument
        *inst_meas:
        do_plots: Default True: If False no plots are produced.
            Data is still saved and can be displayed with show_num.
        use_threads: If True and if multiple things are being measured,
            multiple threads will be used to parallelise the waiting.

    Returns:
        plot, data : returns the plot and the dataset

    """

    for inst in inst_meas:
        if getattr(inst, "setpoints", False):
            raise ValueError("3d plotting is not supported")

    innerloop = qc.Loop(inst_set2.sweep(start2,
                                        stop2,
                                        num=num_points2),
                        delay2).each(*inst_meas)
    outerloop = qc.Loop(inst_set.sweep(start,
                                       stop,
                                       num=num_points),
                        delay).each(innerloop)

    set_params = ((inst_set, start, stop),
                  (inst_set2, start2, stop2))
    meas_params = _select_plottables(inst_meas)

    plot, data = _do_measurement(outerloop, set_params, meas_params,
                                 do_plots=do_plots, use_threads=use_threads)
    data.data_num = qc.data.data_set.DataSet.location_provider.counter
    return plot, data


def do0d(*inst_meas, do_plots=True, use_threads=True):
    """
    Args:
        *inst_meas:
        do_plots: Default True: If False no plots are produced.
            Data is still saved and can be displayed with show_num.
        use_threads: If True and if multiple things are being measured,
            multiple threads will be used to parallelise the waiting.
    Returns:
        plot, data : returns the plot and the dataset
    """
    measurement = qc.Measure(*inst_meas)
    meas_params = _select_plottables(inst_meas)
    plot, data = _do_measurement_single(
        measurement, meas_params, do_plots=do_plots, use_threads=use_threads)
    data.data_num = qc.data.data_set.DataSet.location_provider.counter
    return plot, data
