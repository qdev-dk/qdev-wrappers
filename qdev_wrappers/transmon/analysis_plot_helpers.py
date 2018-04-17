import matplotlib.pyplot as plt
import numpy as np
import qcodes as qc

from . import get_title, get_pulse_location, get_analysis_location, get_data_num

# TODO extend 'plot_with_markers' to 2d


def plot_cf_data(data_list,
                 subplot=None, xdata=None,
                 legend_labels=[], axes_labels=[]):
    """
    Function to plot multiple arrays (of same length) on one axis

    Args:
        data_list: list of arrays to be compared
        subplot (matplotlib AxesSubplot): optional subplot which this data
            should be plotted on default None will create new one
        xdata (array): optional x axis data, default None results in indices
            of data1 being used
        legend_labels ['d1 label', ..]: optional labels for data
        axes_labels ['xlabel', 'ylabel']: optional labels for axes

    Returns:
        fig, sub (matplotlib.figure.Figure, matplotlib AxesSubplot) if
            subplot kwarg not None
    """
    if subplot is None:
        fig, sub = plt.subplots()
    else:
        fig, sub = subplot.figure, subplot
    nums = [get_data_num(d) for d in data_list]
    title = ""
    for n in nums[:-1]:
        title += '{0:03d}_'.format(n)
    title += get_title(nums[-1])
    sub.set_title(title)
    if (len(legend_labels) == 0) or (len(legend_labels) != len(data_list)):
        legend_labels = [[]] * len(data_list)
    if (len(axes_labels) == 0) or (len(axes_labels) != 2):
        axes_labels = [[]] * 2
    if xdata is None:
        xdata = np.arange(len(data_list[0]))

    for i, data in enumerate(data_list):
        sub.plot(xdata, data, linewidth=1.0, label=legend_labels[i])

    if any(legend_labels):
        box = sub.get_position()
        sub.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        sub.legend(fontsize=10, bbox_to_anchor=(1, 1))
    if any(axes_labels):
        sub.set_xlabel(axes_labels[0])
        sub.set_ylabel(axes_labels[1])

    if subplot is None:
        return fig, sub


def line_cut(dataset, key, vals, axis='y'):
    """
    Function which given an array of a dataset selects array within it
    which corresponds to the set array values given and plots.

    Args:
        dataset (qcodes dataset)
        key (string): key to search dataset for to find array to plot
        vals (list): list of values of setpoints for which to cut the
            specified array at (can be x or y axis depending on axis setting)
        axis ('x' or 'y') (default 'y'): axis to cut along

    Returns:
        subplot with line cuts plotted
    """
    array = next(getattr(dataset, k)
                 for k in dataset.arrays.keys() if key in k)
    x_data = np.array(getattr(array, "set_arrays")[1][0])
    y_data = np.array(getattr(array, "set_arrays")[0])
    x_label = '{} ({})'.format(getattr(array, "set_arrays")[
        1].label, getattr(array, "set_arrays")[1].unit)
    y_label = '{} ({})'.format(getattr(array, "set_arrays")[
        0].label, getattr(array, "set_arrays")[0].unit)
    z_label = array.name
    if axis == 'x':
        z_data = np.zeros((len(vals), len(y_data)))
        for i, v in enumerate(vals):
            x_index = np.where(x_data == v)
            z_data[i] = array[:, x_index]
        fig, sub = plot_cf_data(z_data,
                                xdata=y_data,
                                legend_labels=["{} {}".format(
                                    v, x_label) for v in vals],
                                axes_labels=[y_label, z_label])

    elif axis == 'y':
        z_data = np.zeros((len(vals), len(x_data)))
        for i, v in enumerate(vals):
            y_index = np.where(y_data == v)
            z_data[i] = array[y_index, :]
        fig, sub = plot_cf_data(z_data,
                                xdata=x_data,
                                legend_labels=[str(v) + y_label for v in vals],
                                axes_labels=[x_label, z_label])
    return sub


def plot_subset(dataset, key, x_start=None, x_stop=None,
                y_start=None, y_stop=None):
    """
    Function which plots a subset of a 2D dataset

    Args:
        dataset (qcodes dataset)
        key (string): key to search dataset for to find array to plot
        x_start (default is first x val)
        x_stop (default is final x val)
        y_start (default is first y val)
        y_stop (default is final y val)

    Returns:
        subset plot
    """
    array = next(getattr(dataset, k)
                 for k in dataset.arrays.keys() if key in k)
    x_data = np.array(getattr(array, "set_arrays")[1][0])
    y_data = np.array(getattr(array, "set_arrays")[0])
    x_label = '{} ({})'.format(getattr(array, "set_arrays")[
        1].label, getattr(array, "set_arrays")[1].unit)
    y_label = '{} ({})'.format(getattr(array, "set_arrays")[
        0].label, getattr(array, "set_arrays")[0].unit)
    x_indices = np.where((x_data >= (x_start or -1 * np.inf)) &
                         (x_data <= (x_stop or np.inf)))[0]
    y_indices = np.where((y_data >= (y_start or -1 * np.inf)) &
                         (y_data <= (y_stop or np.inf)))[0]
    pl = qc.MatPlot(x_data[x_indices[0]:x_indices[-1]],
                    y_data[y_indices[0]:y_indices[-1]],
                    array[y_indices[0]:y_indices[-1],
                          x_indices[0]:x_indices[-1]])
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(get_title(get_data_num(dataset)))
    return pl


def plot_with_markers(dataset, indices, subplot=None, x_key="set", y_key="mag",
                      title=None):
    """
    Function which does simple plot of data with points at specified indices
    added

    Args:
        dataset (qcodes DataSet)
        indices (array): array of data indices of resonances
        subplot (default None) subplot to add markers to, default is to create
            new one
        x_key (default "mag"): key to search dataset for y_array to
            plot
        y_key (default "mag"): key to search dataset for y_array to
            plot
        title (default None): addition to sataset num to add as title


    Returns:
        subplot (matplotlib AxesSubplot): plot of results
    """
    if subplot is None:
        subplot = plt.subplot(111)
    try:
        setpoints = next(getattr(dataset, k)
                         for k in dataset.arrays.keys() if x_key in k)
        magnitude = next(getattr(dataset, k)
                         for k in dataset.arrays.keys() if y_key in k)
    except Exception:
        raise Exception('could not get {} and {} arrays from dataset, check '
                        'dataset has these keys array '
                        'names'.format(x_key, y_key))
    subplot.plot(setpoints, magnitude, 'b')
    subplot.plot(setpoints[indices], magnitude[indices], 'gs')
    subplot.set_xlabel('frequency(Hz)')
    subplot.set_ylabel('S21')

    pl_title = (title or '') + get_title(get_data_num(dataset))
    subplot.figure.suptitle(pl_title, fontsize=12)
    return subplot


def save_fig(plot_to_save, name='analysis', counter=None, pulse=False):
    """
    Function which saves a matplot figure in analysis_location from
    get_analysis_location()

    Args:
        plot_to_save (matplotlib AxesSubplot or Figure)
        name  (str): plot will be saved with '{counter}_{name}.png'
            so counter and/or name must be unique, default 'analysis'
        counter (int): counter for fig naming as above, if not specified
            will try to use one from the plot.
        pulse (bool): if true saves fig in pulse_lib folder from config,
            otherwise save in analysis folder from config, default False.
    """

    fig = getattr(plot_to_save, 'figure', plot_to_save) or plot_to_save

    if counter == None and name == 'analysis':
        raise AttributeError('No name or counter specified will result'
                             ' in non unique plot name')
    elif counter is None:
        full_name = name + '.png'
    else:
        full_name = '{0:03d}'.format(counter) + '_' + name + '.png'

    if pulse:
        location = get_pulse_location()
    else:
        location = get_analysis_location()
    fig.savefig(location + full_name)
