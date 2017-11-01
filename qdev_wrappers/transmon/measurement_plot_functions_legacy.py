import qcodes as qc
from . import get_title

# TODO: names, full names and all the fun you didn't know you were missing


def plot_data(data, key=None, matplot=False):
    """
    Plotting function for plotting arrays of a dataset in seperate
    QtPlots, cannot be used with live_plot if there is more than one
    subplot. If key is specified returns only the plot for the array
    with the key in the name.
    Args:
        data (qcodes dataset): dataset to be plotted
        key (str): key which if specified is used to select the first array
            from the dataset for plotting with a name which contains this key.
        matplot (bool) (default False): default is to QtPlot the data

    Returns:
        qc Matplot or QtPlot
    """
    if hasattr(data, "data_num"):
        title = title = get_title(data.data_num)
    else:
        title = ""
    if key is None:
        plots = []
        for value in data.arrays.keys():
            if "set" not in value:
                if matplot:
                    pl = qc.MatPlot(getattr(data, value))
                else:
                    pl = qc.QtPlot(getattr(data, value), figsize=(700, 500))
                    pl.subplots[0].setTitle(title)
                    pl.subplots[0].showGrid(True, True)
                plots.append(pl)
        return plots
    else:
        try:
            key_array_name = [v for v in data.arrays.keys() if key in v][0]
        except IndexError:
            raise KeyError('key: {} not in data array '
                           'names: {}'.format(key,
                                              list(data.arrays.keys())))
        if matplot:
            pl = qc.MatPlot(getattr(data, key_array_name))
        else:
            pl = qc.QtPlot(getattr(data, key_array_name), figsize=(700, 500))
            pl.subplots[0].setTitle(title)
            pl.subplots[0].showGrid(True, True)
        return pl


def plot_data_single_window(dataset, meas_param, key=None):
    """
    Plotting function for plotting arrays of a dataset in a single window
    (works with live plot but not great if you want to save a png)

    Args:
        dataset (qcodes dataset): dataset to be plotted
        meas_param: parameter being measured
        key (str) (default None): string to search the array names of the
            measured param for, all arrays with key in name will be added
            as subplots. Default is to plot all.

    Returns:
        QtPlot
    """
    if hasattr(dataset, "data_num"):
        title = title = get_title(dataset.data_num)
    else:
        title = ""
    plot_array_names = []
    if hasattr(meas_param, 'full_names'):
        for array_name in meas_param.full_names:
            if (key is None) or (key in array_name):
                plot_array_names.append(array_name)
    elif hasattr(meas_param, 'full_name'):
        if (key is None) or (key in array_name):
            plot_array_names.append(meas_param.full_name)
    if len(plot_array_names) == 0:
        raise KeyError('key: {} not in parameter array '
                       'names: {}'.format(key,
                                          list(meas_param.names)))
    plot = qc.QtPlot(figsize=(700 * len(plot_array_names), 500))
    for i, plot_array_name in enumerate(plot_array_names):
        plot.add(getattr(dataset, plot_array_name), subplot=i + 1)
        plot.subplots[i].showGrid(True, True)
    plot.subplots[0].setTitle(title)
    return plot


def save_plot(dataset, key):
    """
    Function for saving one of the subplots from a dataset based on a
    given key.

    Args:
        dataset (qcodes dataset): dataset to plot
        key (str): string specifying parameter array/values to plot
        (eg key="mag" will search arrays of the dataset for any with "mag"
         in the name).

    Returns:
        plot
    """
    plot = plot_data(dataset, key=key)
    plot.save()
    return plot
