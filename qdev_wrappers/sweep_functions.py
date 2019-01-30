import matplotlib.pyplot as plt
from os.path import sep
from typing import Optional, Tuple, Sequence, Union
Number = Union[float, int]
from collections import Iterable
from contextlib import suppress
from pyqtgraph.multiprocess.remoteproxy import ClosedError

import qcodes as qc
from qcodes.instrument.visa import VisaInstrument
from qcodes.plots.pyqtgraph import QtPlot
from qcodes.actions import Task
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
    instr_names = set(p.root_instrument.name
                      for p in params
                      if p.root_instrument is not None)
    for name in instr_names:
        instr = qc.Instrument.find_instrument(name)
        # suppress for non visa instruments, that do not implement this
        # method
        with suppress(AttributeError):
            instr.device_clear()


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

            if 'pdf_subfolder' in CURRENT_EXPERIMENT or 'png_subfolder' in CURRENT_EXPERIMENT:
                _do_MatPlot(data,meas_params)

        else:
            plot = None

        log.info("#[QCoDeS]# Saved dataset to: {}".format(data.location))

        if interrupted:
            raise KeyboardInterrupt
    except:
        log.exception("Exception in doO")
        raise
    return plot, data


def _do_measurement(loop: Loop, set_params: tuple, meas_params: tuple,
                    do_plots: Optional[bool]=True,
                    use_threads: bool=True,
                    auto_color_scale: Optional[bool]=None,
                    cutoff_percentile: Optional[Union[Tuple[Number, Number], Number]]=None) -> Tuple[QtPlot, DataSet]:
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
        auto_color_scale: if True, the colorscale of heatmap plots will be
            automatically adjusted to disregard outliers.
        cutoff_percentile: percentile of data that may maximally be clipped
            on both sides of the distribution.
            If given a tuple (a,b) the percentile limits will be a and 100-b.
            See also the plotting tuorial notebook.
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
                plot, _ = _plot_setup(data, meas_params, startranges=startranges,
                                      auto_color_scale=auto_color_scale,
                                      cutoff_percentile=cutoff_percentile)
            except (ClosedError, ConnectionError):
                log.warning('Remote process crashed png will not be saved')
                # if remote process crashed continue without plots
                do_plots = False
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
                # if remote process crashed continue without plots
                do_plots = False

            if 'pdf_subfolder' in CURRENT_EXPERIMENT or 'png_subfolder' in CURRENT_EXPERIMENT:
                _do_MatPlot(data,meas_params,
                            auto_color_scale=auto_color_scale,
                            cutoff_percentile=cutoff_percentile)

        if CURRENT_EXPERIMENT.get('device_image'):
            log.debug('Saving device image')
            save_device_image(tuple(sp[0] for sp in set_params))

        log.info("#[QCoDeS]# Saved dataset to: {}".format(data.location))
        if interrupted:
            raise KeyboardInterrupt
    except:
        log.exception("Exception in doND")
        raise
    return plot, data


def _do_MatPlot(data,meas_params,
                auto_color_scale: Optional[bool]=None,
                cutoff_percentile: Optional[Union[Tuple[Number, Number], Number]]=None):
    plt.ioff()
    plot, num_subplots = _plot_setup(data, meas_params, useQT=False,
                                     auto_color_scale=auto_color_scale,
                                     cutoff_percentile=cutoff_percentile)
    # pad a bit more to prevent overlap between
    # suptitle and title
    plot.rescale_axis()
    plot.fig.tight_layout(pad=3)

    if 'pdf_subfolder' in CURRENT_EXPERIMENT:
        title_list = plot.get_default_title().split(sep)
        title_list.insert(-1, CURRENT_EXPERIMENT['pdf_subfolder'])
        title = sep.join(title_list)
        plot.save("{}.pdf".format(title))

    if 'png_subfolder' in CURRENT_EXPERIMENT:
        title_list = plot.get_default_title().split(sep)
        title_list.insert(-1, CURRENT_EXPERIMENT['png_subfolder'])
        title = sep.join(title_list)
        plot.fig.savefig("{}.png".format(title),dpi=500)

    if (pdfdisplay['combined'] or
            (num_subplots == 1 and pdfdisplay['individual'])):
        plot.fig.canvas.draw()
        plt.show()
    else:
        plt.close(plot.fig)
    if num_subplots > 1:
        _save_individual_plots(data, meas_params,
                               pdfdisplay['individual'],
                               auto_color_scale=auto_color_scale,
                               cutoff_percentile=cutoff_percentile)
    plt.ion()


def do1d(inst_set, start, stop, num_points, delay, *inst_meas, do_plots=True,
         use_threads=False,
         auto_color_scale: Optional[bool]=None,
         cutoff_percentile: Optional[Union[Tuple[Number, Number], Number]]=None):
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
        auto_color_scale: if True, the colorscale of heatmap plots will be
            automatically adjusted to disregard outliers.
        cutoff_percentile: percentile of data that may maximally be clipped
            on both sides of the distribution.
            If given a tuple (a,b) the percentile limits will be a and 100-b.
            See also the plotting tuorial notebook.

    Returns:
        plot, data : returns the plot and the dataset

    """

    loop = qc.Loop(inst_set.sweep(start,
                                  stop,
                                  num=num_points), delay).each(*inst_meas)

    set_params = (inst_set, start, stop),
    meas_params = _select_plottables(inst_meas)

    plot, data = _do_measurement(loop, set_params, meas_params,
                                 do_plots=do_plots, use_threads=use_threads,
                                 auto_color_scale=auto_color_scale,
                                 cutoff_percentile=cutoff_percentile)

    return plot, data


def do1dDiagonal(inst_set, inst2_set, start, stop, num_points,
                 delay, start2, slope, *inst_meas, do_plots=True,
                 use_threads=False,
                 auto_color_scale: Optional[bool]=None,
                 cutoff_percentile: Optional[Union[Tuple[Number, Number], Number]]=None):
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
        auto_color_scale: if True, the colorscale of heatmap plots will be
            automatically adjusted to disregard outliers.
        cutoff_percentile: percentile of data that may maximally be clipped
            on both sides of the distribution.
            If given a tuple (a,b) the percentile limits will be a and 100-b.
            See also the plotting tuorial notebook.

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
                                 do_plots=do_plots, use_threads=use_threads,
                                 auto_color_scale=auto_color_scale,
                                 cutoff_percentile=cutoff_percentile)

    return plot, data


def do2d(inst_set, start, stop, num_points, delay,
         inst_set2, start2, stop2, num_points2, delay2,
         *inst_meas, do_plots=True, use_threads=False,
         set_before_sweep: Optional[bool]=False,
         innerloop_repetitions: Optional[int]=1,
         innerloop_pre_tasks: Optional[Sequence]=None,
         innerloop_post_tasks: Optional[Sequence]=None,
         auto_color_scale: Optional[bool]=None,
         cutoff_percentile: Optional[Union[Tuple[Number, Number], Number]]=None):
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
        set_before_sweep: if True the outer parameter is set to its first value
            before the inner parameter is swept to its next value.
        innerloop_pre_tasks: Tasks to execute before each iteration of the
            outer loop
        innerloop_post_tasks: Tasks to execute after each iteration of the
            outer loop
        auto_color_scale: if True, the colorscale of heatmap plots will be
            automatically adjusted to disregard outliers.
        cutoff_percentile: percentile of data that may maximally be clipped
            on both sides of the distribution.
            If given a tuple (a,b) the percentile limits will be a and 100-b.
            See also the plotting tuorial notebook.

    Returns:
        plot, data : returns the plot and the dataset

    """

    for inst in inst_meas:
        if getattr(inst, "setpoints", False):
            setpoints = inst.setpoints
            if isinstance(setpoints, Iterable):
                if all(len(v) == 0 for v in setpoints):
                    continue
            raise ValueError("3d plotting is not supported")

    actions = []
    for i_rep in range(innerloop_repetitions):
        innerloop = qc.Loop(inst_set2.sweep(start2,
                                            stop2,
                                            num=num_points2),
                            delay2).each(*inst_meas)
        if set_before_sweep:
            ateach = [innerloop, Task(inst_set2, start2)]
        else:
            ateach = [innerloop]

        if innerloop_pre_tasks is not None:
            ateach = list(innerloop_pre_tasks) + ateach
        if innerloop_post_tasks is not None:
            ateach = ateach + list(innerloop_post_tasks)

        actions += ateach

    outerloop = qc.Loop(inst_set.sweep(start,
                                       stop,
                                       num=num_points),
                        delay).each(*actions)

    set_params = ((inst_set, start, stop),
                  (inst_set2, start2, stop2))
    meas_params = _select_plottables(inst_meas)

    plot, data = _do_measurement(outerloop, set_params, meas_params,
                                 do_plots=do_plots, use_threads=use_threads,
                                 auto_color_scale=auto_color_scale,
                                 cutoff_percentile=cutoff_percentile)

    return plot, data


def do0d(*inst_meas, do_plots=True, use_threads=False):
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
    return plot, data
