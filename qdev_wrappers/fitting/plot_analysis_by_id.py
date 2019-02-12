import qcodes as qc
import numpy as np
import matplotlib.pyplot as plt
import os
from os.path import expanduser
from qcodes import config
from qcodes.dataset.data_export import get_data_by_id, load_by_id
from qcodes.dataset.plotting import _rescale_ticks_and_units, plot_by_id
from qcodes.dataset.sqlite_base import connect, transaction


def plot_analysis_by_id(analysis_run_id, save_plot=False, **setpoints):
    """Takes run_id of fit results, finds corresponding dataset.
        If dataset is 1d: plots fit result on top of dataset
        If dataset is 2d: plots fit result on top of data at setpoint given.
        If dataset is 2d and no setpoints are given: just plot coefficients vs setpoints (run plot_by_id)

        setpoint should be a dictionary, fx. {'frequency' : 5.4e9}"""

    data, data_run_id = _retrieve_basis_dataset(analysis_run_id)
    analysis_info = load_by_id(analysis_run_id)
    model_info = eval(analysis_info.metadata['model'])

    # check if this analysis run has a numpy function saved for plotting (in a locate-able format)
    # ToDo: save dill of model, use this instead of model metadata from fit
    if 'function' not in model_info.keys():
        raise RuntimeError("That model did not save function information for plotting, so plotting doesn't work.")
    elif type(model_info['function']) is not dict:
        raise RuntimeError("Function information for that model was not saved as a dictionary, so the numpy function "
                           "for plotting can't be retrieved.")
    elif 'func_np' not in model_info['function'].keys():
        raise RuntimeError("That model did not save a numpy function for plotting, so plotting doesn't work.")

    # If data is for a 1D plot, retrieve fit parameters and x- and y-data
    if len(data) == 2:

        param_dict = _retrieve_parameter_dict(analysis_run_id, 2)

        xdata = data[0]
        ydata = data[1]

        axes = _plot_1d(analysis_run_id, data_run_id, xdata, ydata, param_dict)

    elif len(data) == 3:

        # If data is for a 2D plot and setpoints are specified, find xdata, ydata and param_dict to plot a 1d cut
        if setpoints:
            param_dict = _retrieve_parameter_dict(analysis_run_id, 3, **setpoints)
            # Get data at the specified setpoints
            plot_data = data.copy()
            setpoint_data = {}
            for i, item in enumerate(plot_data):
                if item['name'] in setpoints.keys():
                    setpoint_data[item['name']] = item
                    del(plot_data[i])
            if len(plot_data) > 2:
                raise NotImplementedError("Plotting cuts at setpoints only implemented for 1D fits."
                                          f"The data at the specified setpoints is {len(plot_data)-1}D")

            setpoint_indices = []
            for name, value in setpoints.items():
                setpoint_indices.append(np.where(setpoint_data[name]['data'] == value)[0])
            data_indices = setpoint_indices[0]
            for array in setpoint_indices:
                data_indices = np.array([i for i in array if i in data_indices])

            for variable in plot_data:
                variable['data'] = variable['data'][data_indices]

            xdata = plot_data[0]
            ydata = plot_data[1]

            axes = _plot_1d(analysis_run_id, data_run_id, xdata, ydata, param_dict, **setpoints)

        # If no setpoints are specified, plot parameters as a function of setpoints
        else:
            axes = plot_by_id(analysis_run_id)[0]

    else:
        raise NotImplementedError(f'sorry, {len(data)-1} is too many dimensions for now')
        # ToDo: it could still attempt plot_by_id for 2 setpoints, that should work fine
    if save_plot is True:
        _save_plot(axes, analysis_run_id)

    return axes


def _retrieve_basis_dataset(analysis_run_id):
    inferred_from = eval(load_by_id(analysis_run_id).metadata['inferred_from'])
    data_run_id = inferred_from['run_id']
    dept_var = inferred_from['dept_var']

    # Find the data corresponding to the dependent variable
    index = None
    for idx, measured_data in enumerate(get_data_by_id(data_run_id)):
        if measured_data[-1]['name'] == dept_var:
            index = idx
    if index is None:
        raise RuntimeError(f"No data found with dependent variable {dept_var}")
    data = get_data_by_id(data_run_id)[index]

    return data, data_run_id


def _retrieve_parameter_dict(analysis_run_id, data_length, **setpoints):

    analysis_info = load_by_id(analysis_run_id)
    model_info = eval(analysis_info.metadata['model'])

    if data_length == 2:
        # get fit parameters from database
        file = expanduser(qc.config['core']['db_location'])
        conn = connect(file)
        sql = f"SELECT * FROM '{analysis_info.table_name}'"

        c = transaction(conn, sql)
        fit_result = c.fetchall()[0]

        param_dict = {}
        for name, result in zip(fit_result.keys(), tuple(fit_result)):
            if name in [name for name in model_info['parameters'].keys()]:
                param_dict[name] = result

    elif data_length == 3:
        if setpoints:
            param_dict = {}
            fit_res = {}

            # Organize data from fit, store in fit_data
            all_fit_results = get_data_by_id(analysis_run_id)
            for param in all_fit_results:
                for param_info in param:
                    fit_res[param_info['name']] = param_info['data']

            # indices is a list of arrays, with one array per setpoint.
            # Each array specifies the indices in the fit data where the setpoint value matches the one specified
            indices = []
            for name, val in setpoints.items():
                if val not in fit_res[name]:
                    raise RuntimeError(f"The specified {name} setpoint, {val}, was not found in the fit data")
                i = np.where(fit_res[name] == val)[0]
                indices.append(i)

            # Starting with the first array, remove any elements that aren't present in subsequent arrays
            index = indices[0]
            for index_list in indices:
                index = [i for i in index if i in index_list]

            # Confirm that there is only one, and only one, index (and therefore one fit) left
            if len(index) == 0:
                raise RuntimeError("No fit found with the specified combination of setpoints")
            elif len(index) > 1:
                raise RuntimeError(f"That combination of setpoints has {len(index)} fits. Please be more specific.")

            # Make param dict with parameters from the results
            i = index[0]
            for param, param_values in fit_res.items():
                if param not in setpoints.keys():
                    param_dict[param] = param_values[i]

    return param_dict


def _plot_1d(analysis_run_id, data_run_id, xdata, ydata, param_dict, **setpoints):

    analysis_info = load_by_id(analysis_run_id)
    model_info = eval(analysis_info.metadata['model'])
    title = f"Analysis #{analysis_run_id} (measurement #{data_run_id}) \n " \
            f"{analysis_info.exp_name} ({analysis_info.sample_name})"

    # plot for 1D fit or 1D cut of fit
    plt.figure(figsize=(10, 4))
    ax = plt.subplot(111)
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width*0.7, box.height])

    ax.plot(xdata['data'], ydata['data'], marker='.', markersize=5, linestyle='', color='C0')

    # plot fit if successful, define textbox string for fit
    if param_dict is None:
        textstr = '{} \n Unsuccessful fit'.format(model_info['function']['func_str'])
    else:
        param_arg_list = ", ".join([name for name in model_info['parameters'].keys()])
        func = eval(f"lambda x,{param_arg_list}: {model_info['function']['func_np']}")

        x = np.linspace(xdata['data'].min(), xdata['data'].max(), len(xdata['data']) * 10)
        ax.plot(x, func(x=x, **param_dict), color='C1')

        p_label_list = [model_info['function']['func_str']]
        for parameter in param_dict:
            value = param_dict[parameter]
            unit = model_info['parameters'][parameter]['unit']
            label = model_info['parameters'][parameter]['label']
            p_label_list.append(r'{} = {:.3g} {}'
                                .format(label, value, unit))
        for setpoint, value in setpoints.items():
            p_label_list.append(f'{setpoint}: {value}')
            title += f'\n {setpoint}: {value}'
        textstr = '\n'.join(p_label_list)

    # set axes labels, textbox and title
    ax.set_xlabel(f"{xdata['label']} ({xdata['unit']})")
    ax.set_ylabel(f"{ydata['label']} ({ydata['unit']})")

    data_lst = [xdata, ydata]
    _rescale_ticks_and_units(ax, data_lst)

    ax.text(1.05, 0.75, textstr, transform=ax.transAxes, fontsize=14,
            verticalalignment='top', bbox={'ec': 'k', 'fc': 'w'})

    ax.set_title(title)

    return [ax]


def _save_plot(axes, analysis_id):
    """
    Save the plots
    """
    plt.ioff()

    mainfolder = config.user.mainfolder
    experiment_name = load_by_id(analysis_id).exp_name
    sample_name = load_by_id(analysis_id).sample_name

    storage_dir = os.path.join(mainfolder, experiment_name, sample_name)
    os.makedirs(storage_dir, exist_ok=True)

    png_dir = os.path.join(storage_dir, 'png')
    pdf_dir = os.path.join(storage_dir, 'pdf')

    os.makedirs(png_dir, exist_ok=True)
    os.makedirs(pdf_dir, exist_ok=True)

    save_pdf = True
    save_png = True


    for i, ax in enumerate(axes):
        if save_pdf:
            start_name = f'{analysis_id}_{i}.pdf'
            file_name = _make_file_name(pdf_dir, start_name)
            full_path = os.path.join(pdf_dir, file_name)
            ax.figure.savefig(full_path, dpi=500)
        if save_png:
            start_name = f'{analysis_id}_{i}.png'
            file_name = _make_file_name(png_dir, start_name)
            full_path = os.path.join(png_dir, file_name)
            ax.figure.savefig(full_path, dpi=500)

    plt.ion()
    return axes


def _make_file_name(directory, initial_name):
    full_path = os.path.join(directory, initial_name)
    name = initial_name.split('.')[0]
    file_format = initial_name.split('.')[1]
    new_name = name
    i = 1
    while os.path.isfile(full_path):
        new_name = f'{name}_{i}'
        file_path = '.'.join([new_name, file_format])
        full_path = os.path.join(directory, file_path)
        i += 1
    final_name = '.'.join([new_name, file_format])
    return final_name
