from qcodes.dataset.data_export import load_by_id
from qdev_wrappers.fitting.helpers import organize_exp_data, organize_fit_data
from qcodes.dataset.plotting import _rescale_ticks_and_units, plot_on_a_plain_grid
import json
import warnings
import matplotlib.pyplot as plt
import numpy as np

# TODO: docstrings
# TODO: add initial values?


def plot_least_squares_1d(indept, dept, metadata, title,
                          fit=None, variance=None,
                          initial_values=None,
                          rescale_axes=True,
                          text=None):

    plt.figure(figsize=(10, 4))
    ax = plt.subplot(111)
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.7, box.height])

    # plot data
    ax.plot(indept['data'], dept['data'],
            marker='.', markersize=5, linestyle='', color='C0',
            label='data')

    # plot fit
    if fit is not None:
        fit_paramnames = metadata['fitter']['fit_parameters']
        variance_paramnames = metadata['fitter'].get('variance_parameters')
        initial_value_paramnames = metadata['fitter'].get(
            'initial_value_parameters')
        x = np.linspace(indept['data'].min(), indept['data'].max(),
                        num=len(indept['data']) * 10)
        finalkwargs = {metadata['fitter']['experiment_parameters'][0]: x,
                       'np': np,
                       **{f['name']: f['data'][0] for f in fit.values()}}
        finaly = eval(metadata['fitter']['function']['np'],
                      finalkwargs)
        ax.plot(x, finaly, color='C1', label='fit')
        if initial_values is not None:
            initialkwargs = {}
            for i, name in enumerate(initial_value_paramnames):
                initialkwargs[fit_paramnames[i]] = initial_values[name]['data'][0]
            initialkwargs.update(
                {metadata['fitter']['experiment_parameters'][0]: x,
                 'np': np})
            intialy = eval(metadata['fitter']['function']['np'],
                           initialkwargs)
            ax.plot(x, intialy, color='grey', label='initial fit values')
        plt.legend()
        p_label_list = [text] if text else []
        p_label_list.append(metadata['fitter']['function']['str'])
        for i, fpn in enumerate(fit_paramnames):
            fit_val = fit[fpn]['data'][0]
            if variance is not None:
                variance_val = variance[variance_paramnames[i]]['data'][0]
                standard_dev = np.sqrt(variance_val)
                p_label_list.append('{} = {:.3g} ± {:.3g} {}'.format(
                    fit[fpn]['label'], fit_val,
                    standard_dev, fit[fpn]['unit']))
            else:
                p_label_list.append('{} = {:.3g} {}'.format(
                    fit[fpn]['label'], fit_val, fit[fpn]['unit']))
        textstr = '\n'.join(p_label_list)
    else:
        textstr = '{} \n Unsuccessful fit'.format(
            fitter.metadata['fitter']['function']['str'])

    # add text, axes, labels, title and rescale
    ax.text(1.05, 0.7, textstr, transform=ax.transAxes, fontsize=14,
            verticalalignment='top', bbox={'ec': 'k', 'fc': 'w'})
    ax.set_xlabel(f"{indept['label']} ({indept['unit']})")
    ax.set_ylabel(f"{dept['label']} ({dept['unit']})")
    ax.set_title(title)
    if rescale_axes:
        data_lst = [indept, dept]
        _rescale_ticks_and_units(ax, data_lst)

    return ax


def plot_heat_map(x, y, z, title, rescale_axes=True):
    fig, ax = plt.subplots(1, 1)
    ax, colorbar = plot_on_a_plain_grid(
        x['data'], y['data'], z['data'], ax)
    ax.set_xlabel(f"{x['label']} ({x['unit']})")
    ax.set_ylabel(f"{y['label']} ({y['unit']})")
    colorbar.set_label(f"{z['label']} ({z['unit']})")
    ax.set_title(title)
    if rescale_axes:
        data_lst = [x, y, z]
        _rescale_ticks_and_units(ax, data_lst)
    return ax


def plot_fit_param_1ds(setpoint, fit, metadata, title,
                       variance=None, initial_values=None,
                       rescale_axes=True):
    axes = []
    order = setpoint['data'].argsort()
    xpoints = setpoint['data'][order]
    fit_paramnames = metadata['fitter']['fit_parameters']
    variance_paramnames = metadata['fitter'].get('variance_parameters')
    intial_value_paramnames = metadata['fitter'].get('initial_value_parameters')
    for i, fpn in enumerate(fit_paramnames):
        fig, ax = plt.subplots(1, 1)
        ypoints = fit[fpn]['data'][order]
        if variance is not None:
            var = variance[variance_paramnames[i]]['data'][order]
            standard_dev = np.sqrt(var)
            ax.errorbar(xpoints, ypoints,
                        standard_dev, None, 'g.-')
        else:
            ax.plot(xpoints, ypoints, 'g.-')
        if initial_values is not None:
            ini = initial_values[intial_value_paramnames[i]]['data'][order]
            ax.plot(xpoints, ini, '.-', color='grey', label='initial_guess')
            plt.legend()

        # add text, axes, labels, title and rescale
        xlabel = setpoint['label'] or setpoint['name']
        xlabel += f" ({setpoint['unit']})"
        ax.set_xlabel(xlabel)
        ylabel = fit[fpn]['label'] or fit[fpn]['name']
        ylabel += f" ({fit[fpn]['unit']})"
        ax.set_ylabel(ylabel)
        ax.text(0.05, 0.95, metadata['fitter']['function']['str'],
                transform=ax.transAxes, fontsize=12,
                verticalalignment='top', bbox={'ec': 'k', 'fc': 'w'})
        ax.set_title(title)
        if rescale_axes:
            data_lst = [setpoint, fit[fpn]]
            _rescale_ticks_and_units(ax, data_lst)
        axes.append(ax)
    return axes


def plot_fit_by_id(fit_run_id, rescale_axes=True,
                   show_variance=True, show_initial_values=True,
                   **setpoint_values):

    # load data and sort into dictionaries
    fit_data = load_by_id(fit_run_id)
    try:
        metadata = json.loads(fit_data.metadata['fitting_metadata'])
    except KeyError:
        raise RuntimeError(
            "'fitting_metadata' not found in dataset metadata, are you sure "
            "this is a fitted dataset?")
    dependent_parameter_name = metadata['inferred_from']['dept_var']
    independent_parameter_names = metadata['inferred_from']['indept_vars']
    exp_run_id = metadata['inferred_from']['run_id']
    exp_data = load_by_id(exp_run_id)

    dept, independent, exp_setpoints = organize_exp_data(
        exp_data, dependent_parameter_name, *independent_parameter_names,
        **setpoint_values)
    success, fit, variance, initial_values, fit_setpoints = organize_fit_data(
        fit_data, **setpoint_values)

    if not show_variance or not variance:
        variance = None
    if not show_initial_values or not initial_values:
        initial_values = None

    if len(independent) > 1:
        raise NotImplementedError("Plotting only currently works for "
                                  "fitters with 1 independent variable")
    else:
        indept = independent[independent_parameter_names[0]]
    if len(exp_setpoints) != len(fit_setpoints):
        raise RuntimeError(f'Different number of data and fit setpoints: '
                           f'{len(exp_setpoints)} != {len(fit_setpoints)}')

    # find dimension of plot and generate additional label text
    text_list = []
    if len(fit_setpoints) == 0:
        dimension = 1
    elif all(len(s['data']) == 1 for s in fit_setpoints.values()):
        dimension = 1
        for s in fit_setpoints.values():
            text_list.append(
                '{} = {:.3g} {}'.format(s['name'], s['data'][0], s['unit']))
    elif len([1 for s in fit_setpoints.values() if len(s['data']) > 1]) == 1:
        dimension = 2
        for s in list(fit_setpoints.values()):
            if len(s['data']) == 1:
                text_list.append(
                    '{} = {:.3g} {}'.format(s['name'], s['data'][0], s['unit']))
            else:
                fit_setpoint = s
                exp_setpoint = exp_setpoints[s['name']]
    else:
        raise NotImplementedError(
            "Plotting for more than one setpoint not yet implemented")
    text = '\n'.join(text_list)

    # generate title
    axes = []
    colorbar = None
    title = "Run #{} (#{} fitted), Experiment {} ({})".format(
        fit_run_id,
        metadata['inferred_from']['run_id'],
        metadata['inferred_from']['exp_id'],
        metadata['inferred_from']['sample_name'])

    # make the plots
    if dimension == 1:  # 1D PLOTTING - data + fit 1d plot
        if metadata['fitter']['method'] == 'LeastSquares':
            if not success['data'][0]:
                fit = None
                variance = None
                initial_values = None
            ax = plot_least_squares_1d(indept, dept, metadata, title,
                                       fit=fit, variance=variance,
                                       initial_values=initial_values,
                                       rescale_axes=rescale_axes,
                                       text=text)
            axes.append(ax)
        else:
            warnings.warn(
                'Attempt to plot a 1d plot of a non LeastSquares fit')
    elif dimension == 2:  # 2D PLOTTING: 2d fit heat map plot + fit param plots
        xpoints, ypoints, zpoints = [], [], []
        for i, val in enumerate(fit_setpoint['data']):
            indices = np.argwhere(exp_setpoint['data'] == val).flatten()
            xpoints.append(indept['data'][indices].flatten())
            ypoints.append(exp_setpoint['data'][indices].flatten())
            success_point = success['data'][i]
            if success_point:
                fit_vals = {f['name']: f['data'][i] for f in fit.values()}
                indept_var = metadata['fitter']['experiment_parameters'][0]
                kwargs = {
                    'np': np,
                    indept_var: indept['data'][indices].flatten(),
                    **fit_vals}
                zpoints.append(eval(metadata['fitter']['function']['np'],
                                    kwargs))
            else:
                zpoints.append([None] * len(indept['data'][indices]))
        xpoints = np.array(xpoints).flatten()
        ypoints = np.array(ypoints).flatten()
        zpoints = np.array(zpoints).flatten()
        # Make 2D simulated heatmap plot
        x = {**indept, 'data': xpoints}
        y = {**exp_setpoint, 'data': ypoints}
        z = {**dept, 'data': zpoints, 'label': 'Simulated ' + dept['label']}
        ax = plot_heat_map(x, y, z, title, rescale_axes=rescale_axes)
        axes.append(ax)

        # Make fit parameter vs setpoint plots
        axes += plot_fit_param_1ds(fit_setpoint, fit, metadata, title,
                                   variance=variance, initial_values=initial_values,
                                   rescale_axes=rescale_axes)

    else:  # 3D plot which we can't do :(
        warnings.warn(
            "Plotting for more than one setpoint not yet implemented")
    return axes, colorbar
