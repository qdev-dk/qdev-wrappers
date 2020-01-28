import qcodes as qc
from qcodes.dataset.data_export import load_by_id
from qdev_wrappers.fitting.helpers import organize_exp_data, organize_fit_data, load_json_metadata
from qcodes.dataset.plotting import _rescale_ticks_and_units, plot_on_a_plain_grid
import json
import warnings
import matplotlib.pyplot as plt
import numpy as np
from qdev_wrappers.dataset.doNd import save_image


def plot_least_squares_1d(indept, dept, metadata, title,
                          fit=None, variance=None,
                          initial_values=None,
                          text=None):
    """
    Plots a 1d plot of the data against the fit result (if provided) with the
    initial fit values result also plotted (optionally) and text about the
    fit values, fit function and (optionally) the variance.

    Args:
        indept (dict): data dictionary with keys 'data', 'label', 'unit',
            'name' for x axis
        dept (dict): data dictionary with keys 'data', 'label', 'unit', 'name'
            for y axis
        metadata (dict): fit metadata dictionary
        title (str)
        fit (dict) (optional): dictionary with a key for each fit_parameter
            and with data dictionaries as values
        variance (dict) (optional): dictionary with a key for each
            variance_parameter which if fit then also prints standard deviation
            on fit parameters
        initial_values (dict) (optional): dictionary with a key for each
            initial_value_parameter which if fit then also plots the fit result
            using the initial values used in fitting
        text (str) (optional): string to be prepended to the fit parameter
            values information text box

    Returns:
        matplotlib ax
    """
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
        finalkwargs = {'x': x,
                       'np': np,
                       **{f['name']: f['data'][0] for f in fit.values()}}
        finaly = eval(metadata['fitter']['function']['np'],
                      finalkwargs)
        ax.plot(x, finaly, color='C1', label='fit')
        if initial_values is not None:
            initialkwargs = {}
            for i, name in enumerate(initial_value_paramnames):
                initialkwargs[fit_paramnames[i]
                              ] = initial_values[name]['data'][0]
            initialkwargs.update(
                {'x': x,
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
    data_lst = [indept, dept]
    _rescale_ticks_and_units(ax, data_lst)

    return ax


def plot_heat_map(x, y, z, title):
    """
    Plots a 2d heatmap of the x, y and z data provided

    Args:
        x (dict): data dictionary with keys 'data', 'label', 'unit', 'name'
            for x axis (data should be 1d - length n)
        y (dict): data dictionary with keys 'data', 'label', 'unit', 'name'
            for y axis (data should be 1d - length m)
        z (dict): data dictionary with keys 'data', 'label', 'unit', 'name'
            for z axis (data should be 2d - shape n * m)
        title (str)

    Returns:
        matplotlib ax
        matplotlib colorbar
    """
    fig, ax = plt.subplots(1, 1)
    ax, colorbar = plot_on_a_plain_grid(
        x['data'], y['data'], z['data'], ax,
        cmap=qc.config.plotting.default_color_map)
    ax.set_xlabel(f"{x['label']} ({x['unit']})")
    ax.set_ylabel(f"{y['label']} ({y['unit']})")
    colorbar.set_label(f"{z['label']} ({z['unit']})")
    ax.set_title(title)
    data_lst = [x, y, z]
    _rescale_ticks_and_units(ax, data_lst)
    return ax, colorbar


def plot_fit_param_1ds(setpoint, fit, metadata, title,
                       variance=None, initial_values=None):
    """
    Plots a 1d plot for each fit parameter against the setpoint.

    Args:
        setpoint (dict): data dictionary with keys 'data', 'label', 'unit',
            'name' for x axes
        fit (dict): dictionary with a key for each fit_parameter and with data
            dictionaries as values
        metadata (dict): fit metadata dictionary
        title (str)
        variance (dict) (optional): dictionary with a key for each
            variance_parameter which if fit then also adds error bars
        initial_values (dict) (optional): dictionary with a key for each
            initial_value_parameter which if fit then also plots these against
            the setpoint

    Returns:
        list of matplotlib axes
    """
    axes = []
    order = setpoint['data'].argsort()
    xpoints = setpoint['data'][order]
    fit_paramnames = metadata['fitter']['fit_parameters']
    variance_paramnames = metadata['fitter'].get('variance_parameters')
    intial_value_paramnames = metadata['fitter'].get(
        'initial_value_parameters')
    for i, fpn in enumerate(fit_paramnames):
        fig, ax = plt.subplots(1, 1)
        ypoints = fit[fpn]['data'][order]
        if variance is not None:
            var = variance[variance_paramnames[i]]['data'][order]
            standard_dev = np.sqrt(var)
            ax.errorbar(xpoints, ypoints,
                        standard_dev, None, 'g.-', label='fitted value')
        else:
            ax.plot(xpoints, ypoints, 'g.-', label='fitted value')
        ax.text(0.05, 0.95, metadata['fitter']['function']['str'],
                transform=ax.transAxes, fontsize=12,
                verticalalignment='top', bbox={'ec': 'k', 'fc': 'w'})
        if initial_values is not None:
            ini = initial_values[intial_value_paramnames[i]]['data'][order]
            ax.plot(xpoints, ini, '.-', color='grey', label='initial guess')
            plt.legend()

        # add axes, labels, title and rescale
        xlabel = setpoint['label'] or setpoint['name']
        xlabel += f" ({setpoint['unit']})"
        ax.set_xlabel(xlabel)
        ylabel = fit[fpn]['label'] or fit[fpn]['name']
        ylabel += f" ({fit[fpn]['unit']})"
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        data_lst = [setpoint, fit[fpn]]
        _rescale_ticks_and_units(ax, data_lst)
        axes.append(ax)
    return axes


def plot_fit_by_id(fit_run_id,
                   show_variance=True,
                   show_initial_values=False,
                   save_plots=True,
                   source_conn=None,
                   **setpoint_values):
    """
    Plots the result of a fit (against the data where possible) and
    optionallt saves the plots

    For a 1d plots the fit result against the data if the fitter method
    is 'LeastSquares'. For a 2d plots a 1d for each fit parameter against the
    setpoint variable unless a specific value of the setpoint variable
    is provided (in which case it plots a 1d of the fit result against the
    data at this point if the fitter method is 'LeastSquares'). In the case
    of a 'LeastSquares' fitter also plots the 2d fit result as a heatmap
    (if setpoint_values not provided).

    Args:
        fit_run_id (int): run id of fit dataset
        show_variance (bool) (default True)
        show_initial_values (bool) (default False)
        save_plots (bool) (default True)
        **setpoint_values: key, value pairs of names of the setpoints and the
            value at which the cut should be taken. This is only relevant if
            the fit has been performed at multiple values of some 'setpoint'
            variable

    Returns
        list of matplotlib axes
        matplotlib colorbar of the 2d heatmap (None if not generated)
    """

    # load data and metadata and sort into dictionaries based on metadata and
    # setpoint_values
    fit_data = load_by_id(fit_run_id)
    metadata = load_json_metadata(fit_data)
    dependent_parameter_name = metadata['inferred_from']['dept_var']
    independent_parameter_names = metadata['inferred_from']['indept_vars']
    exp_run_id = metadata['inferred_from']['run_id']
    exp_data = load_by_id(exp_run_id, source_conn)

    dept, independent, exp_setpoints = organize_exp_data(
        exp_data, dependent_parameter_name, *independent_parameter_names,
        **setpoint_values)
    success, fit, variance, initial_values, fit_setpoints, point_vals = organize_fit_data(
        fit_data, **setpoint_values)

    # implement variance and setpoint plotting choices
    if not show_variance or not variance:
        variance = None
    if not show_initial_values or not initial_values:
        initial_values = None

    # check for unplottable fit options
    if len(independent) > 1:
        raise NotImplementedError("Plotting only currently works for "
                                  "fitters with 1 independent variable")
    else:
        indept = independent[independent_parameter_names[0]]
    if len(exp_setpoints) != len(fit_setpoints):
        raise RuntimeError(f'Different number of data and fit setpoints: '
                           f'{len(exp_setpoints)} != {len(fit_setpoints)}')

    # generate additional label text and filename text
    text_list = []
    extra_save_text_list = []
    for i, s in enumerate(setpoint_values.keys()):
        pspec = fit_data.paramspecs[s]
        val = point_vals[i]
        text_list.append(
            '{} = {:.3g} {}'.format(pspec.label, val, pspec.unit))
        extra_save_text_list.append(
            '{}_{:.3g}'.format(pspec.name, val).replace('.', 'p'))
    text = '\n'.join(text_list)
    extra_save_text = '_'.join(extra_save_text_list)

    # generate title
    axes = []
    colorbar = None
    title = "Run #{} (#{} fitted), Experiment {} ({})".format(
        fit_run_id,
        metadata['inferred_from']['run_id'],
        metadata['inferred_from']['exp_id'],
        metadata['inferred_from']['sample_name'])

    # calculate data dimension
    dimension = len(fit_setpoints) + 1
    if dimension == 2:
        fit_setpoint = next(f for f in fit_setpoints.values())
        exp_setpoint = next(e for e in exp_setpoints.values())
    if dimension > 2:
        raise RuntimeError('Cannot make 3D plot. Try specifying a cut')

    # make the plots
    # 1D PLOTTING - data + fit 1d plot
    if dimension == 1:
        if metadata['fitter']['method'] == 'LeastSquares':
            if not success['data'][0]:
                fit = None
                variance = None
                initial_values = None
            ax = plot_least_squares_1d(indept, dept, metadata, title,
                                       fit=fit, variance=variance,
                                       initial_values=initial_values,
                                       text=text)
            axes.append(ax)
        else:
            warnings.warn(
                'Attempt to plot a 1d plot of a non LeastSquares fit')
    # 2D PLOTTING: 2d fit heat map plot + fit param plots
    elif dimension == 2:
        xpoints, ypoints, zpoints = [], [], []
        if metadata['fitter']['method'] == 'LeastSquares':
            for i, val in enumerate(fit_setpoint['data']):
                indices = np.argwhere(exp_setpoint['data'] == val).flatten()
                xpoints.append(indept['data'][indices].flatten())
                ypoints.append(exp_setpoint['data'][indices].flatten())
                success_point = success['data'][i]
                if success_point:
                    fit_vals = {f['name']: f['data'][i] for f in fit.values()}
                    kwargs = {
                        'np': np,
                        'x': indept['data'][indices].flatten(),
                        **fit_vals}
                    zpoints.append(eval(metadata['fitter']['function']['np'],
                                        kwargs))
                else:
                    zpoints.append([None] * len(indept['data'][indices]))
            xpoints = np.array(xpoints).flatten()
            ypoints = np.array(ypoints).flatten()
            zpoints = np.array(zpoints).flatten()
            # 2D simulated heatmap plot
            x = {**indept, 'data': xpoints}
            y = {**exp_setpoint, 'data': ypoints}
            z = {**dept, 'data': zpoints, 'label': 'Simulated ' + dept['label']}
            ax, colorbar = plot_heat_map(x, y, z, title)
            axes.append(ax)

        # 1D fit parameter vs setpoint plots
        axes += plot_fit_param_1ds(fit_setpoint, fit, metadata, title,
                                   variance=variance,
                                   initial_values=initial_values)
    # 3D PLOTTING: nope
    else:
        warnings.warn(
            "Plotting for more than one setpoint not yet implemented")

    # saving
    if save_plots:
        kwargs = {'run_id': fit_data.run_id,
                  'exp_id': fit_data.exp_id,
                  'exp_name': fit_data.exp_name,
                  'sample_name': fit_data.sample_name}
        name_extension = '_'.join(['fit'] + [extra_save_text])
        save_image(axes, name_extension=name_extension, **kwargs)
    return axes, colorbar
