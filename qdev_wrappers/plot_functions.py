from os.path import sep
from copy import deepcopy
import functools
from matplotlib import ticker
import matplotlib.pyplot as plt

from qcodes.plots.pyqtgraph import QtPlot
from qcodes.plots.qcmatplotlib import MatPlot
from qdev_wrappers.file_setup import CURRENT_EXPERIMENT


def _plot_setup(data, inst_meas, useQT=True, startranges=None):
    title = "{} #{:03d}".format(CURRENT_EXPERIMENT["sample_name"],
                                data.location_provider.counter)
    rasterized_note = " rasterized plot"
    num_subplots = 0
    counter_two = 0
    for j, i in enumerate(inst_meas):
        if getattr(i, "names", False):
            num_subplots += len(i.names)
        else:
            num_subplots += 1
    if useQT:
        plot = QtPlot(fig_x_position=CURRENT_EXPERIMENT['plot_x_position'])
    else:
        plot = MatPlot(subplots=(1, num_subplots))

    def _create_plot(plot, i, name, data, counter_two, j, k):
        """
        Args:
            plot: The plot object, either QtPlot() or MatPlot()
            i: The parameter to measure
            name: -
            data: The DataSet of the current measurement
            counter_two: The sub-measurement counter. Each measurement has a
                number and each sub-measurement has a counter.
            j: The current sub-measurement
            k: -
        """
        color = 'C' + str(counter_two)
        parent_instr_name = (i._instrument.name + '_') if i._instrument else ''
        inst_meas_name = "{}{}".format(parent_instr_name, name)
        inst_meas_data = getattr(data, inst_meas_name)
        inst_meta_data = __get_plot_type(inst_meas_data, plot)
        if useQT:
            plot.add(inst_meas_data, subplot=j + k + 1)
            plot.subplots[j + k].showGrid(True, True)
            if j == 0:
                plot.subplots[0].setTitle(title)
            else:
                plot.subplots[j + k].setTitle("")

            plot.fixUnitScaling(startranges)
            QtPlot.qc_helpers.foreground_qt_window(plot.win)

        else:
            if 'z' in inst_meta_data:
                xlen, ylen = inst_meta_data['z'].shape
                rasterized = xlen * ylen > 5000
                plot.add(inst_meas_data, subplot=j + k + 1,
                         rasterized=rasterized)
            else:
                rasterized = False
                plot.add(inst_meas_data, subplot=j + k + 1, color=color)
                plot.subplots[j + k].grid()
            if j == 0:
                if rasterized:
                    fulltitle = title + rasterized_note
                else:
                    fulltitle = title
                plot.subplots[0].set_title(fulltitle)
            else:
                if rasterized:
                    fulltitle = rasterized_note
                else:
                    fulltitle = ""
                plot.subplots[j + k].set_title(fulltitle)


    subplot_index = 0
    for measurement in inst_meas:
        if getattr(measurement, "names", False):
            # deal with multidimensional parameter
            for name in measurement.names:
                _create_plot(plot, measurement, name, data, counter_two, subplot_index, 0)
                subplot_index += 1
                counter_two += 1
        else:
            # simple_parameters
            _create_plot(plot, measurement, measurement.name, data, counter_two, subplot_index, 0)
            subplot_index += 1
            counter_two += 1
    return plot, num_subplots


def __get_plot_type(data, plot):
    # this is a hack because expand_trace works
    # in place. Also it should probably * expand its args and kwargs. N
    # Same below
    data_copy = deepcopy(data)
    metadata = {}
    plot.expand_trace((data_copy,), kwargs=metadata)
    return metadata


def _save_individual_plots(data, inst_meas, display_plot=True):

    def _create_plot(i, name, data, counter_two, display_plot=True):
        # Step the color on all subplots no just on plots
        # within the same axis/subplot
        # this is to match the qcodes-pyqtplot behaviour.
        title = "{} #{:03d}".format(CURRENT_EXPERIMENT["sample_name"],
                                    data.location_provider.counter)
        rasterized_note = " rasterized plot full data available in datafile"
        color = 'C' + str(counter_two)
        counter_two += 1
        plot = MatPlot()
        inst_meas_name = "{}_{}".format(i._instrument.name, name)
        inst_meas_data = getattr(data, inst_meas_name)
        inst_meta_data = __get_plot_type(inst_meas_data, plot)
        if 'z' in inst_meta_data:
            xlen, ylen = inst_meta_data['z'].shape
            rasterized = xlen * ylen > 5000
            plot.add(inst_meas_data, rasterized=rasterized)
        else:
            rasterized = False
            plot.add(inst_meas_data, color=color)
            plot.subplots[0].grid()
        if rasterized:
            plot.subplots[0].set_title(title + rasterized_note)
        else:
            plot.subplots[0].set_title(title)
        title_list = plot.get_default_title().split(sep)
        title_list.insert(-1, CURRENT_EXPERIMENT['pdf_subfolder'])
        title = sep.join(title_list)
        plot.rescale_axis()
        plot.tight_layout()
        plot.save("{}_{:03d}.pdf".format(title,
                                         counter_two))
        if display_plot:
            plot.fig.canvas.draw()
            plt.show()
        else:
            plt.close(plot.fig)

    counter_two = 0
    for j, i in enumerate(inst_meas):
        if getattr(i, "names", False):
            # deal with multidimensional parameter
            for k, name in enumerate(i.names):
                _create_plot(i, name, data, counter_two, display_plot)
                counter_two += 1
        else:
            _create_plot(i, i.name, data, counter_two, display_plot)
            counter_two += 1
