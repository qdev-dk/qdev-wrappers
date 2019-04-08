import matplotlib.pyplot as plt
from qcodes.dataset.plotting import _rescale_ticks_and_units, plot_on_a_plain_grid
from helpers import select_relevant_data, get_run_info


# TODO: test rescale axis


def plot_least_squares_1d(xdata, ydata, fit_result, metadata,
                          show_variance=True, rescale_axes=True,
                          text=None):

    # plot data, and fit if successful
    plt.figure(figsize=(10, 4))
    ax = plt.subplot(111)
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.7, box.height])

    ax.plot(xdata['data'], ydata['data'],
            marker='.', markersize=5, linestyle='', color='C0')

    if fit_result is not None:
        fit_param_names = metadata['fitter']['fit_parameters']
        order = [fit_result.index(i)
                 for i in fit_result if i['name'] in fit_param_names]
        fit_param_units = [fit_result[i]['unit'] for i in order]
        fit_values = [fit_result[i]['data'][0] for i in order]
        variance_param_names = metadata['fitter']['variance_parameters']
        order = [fit_result.index(
            i) for i in fit_result if i['name'] in variance_param_names]
        variance_values = [fit_result[i]['data'][0] for i in order]
    else:
        fit_values = None

    if fit_values is not None:
        x = np.linspace(xdata['data'].min(), xdata['data'].max(),
                        num=len(xdata['data']) * 10)
        kwargs = dict(zip(fit_param_names, fit_values))
        y = eval(metadata['function']['np'], kwargs)
        ax.plot(x, y, color='C1')
        p_label_list = []
        if text is not None:
            p_label_list .append(text)
        p_label_list.append(metadata['function']['str'])
        for i, fit_val in enumerate(fit_values):
            if show_variance:
                standard_dev = np.sqrt(fit_variances[i])
                p_label_list.append('{} = {:.3g} ± {:.3g} {}'.format(
                    fit_param_names[i], fit_val, standard_dev, fit_param_units[i]))
            else:
                p_label_list.append('{} = {:.3g} {}'.format(
                    fit_param_names[i], fit_val, fit_param_units[i]))
        textstr = '\n'.join(p_label_list)
    else:
        textstr = '{} \n Unsuccessful fit'.format(
            fitter.metadata['function']['str'])

    ax.text(1.05, 0.7, textstr, transform=ax.transAxes, fontsize=14,
            verticalalignment='top', bbox={'ec': 'k', 'fc': 'w'})

    # set axes labels and title
    ax.set_xlabel(f"{xdata['label']} ({xdata['unit']})")
    ax.set_ylabel(f"{ydata['label']} ({ydata['unit']})")

    if rescale_axes:
        data_lst = [xdata, ydata]
        _rescale_ticks_and_units(ax, data_lst)

    return ax


def plot_heat_map(xpoints, ypoints, zpoints,
                  xlabel, ylabel, zlabel,
                  xunit, yunit, zunit):
    fig, ax = plt.subplots(1, 1)
    ax, colorbar = plot_on_a_plain_grid(
        xpoints, ypoints, zpoints, ax, colorbar)
    ax.set_xlabel(f"{xlabel} ({xunit})")
    ax.set_ylabel(f"{ylabel} ({yunit})")
    ax.set_title(title)
    colorbar.set_label(f"Simulated {zlabel} ({zunit})")
    return ax


def plot_fit_param_1ds(setpoint, fit_params, var_params):
    axes = []
    order = setpoint_dict['data'].argsort()
    xpoints = setpoint_dict['data'][order]
    for i, d in enumerate(fit_params):
        fig, ax = plt.subplots(1, 1)
        ypoints = d['data'][order]
        if var_params:
            var = var_params[i]['data'][order]
            standard_dev = np.sqrt(var)
            ax.errorbar(xpoints, ypoints,
                        standard_dev, None, 'g.-')
        else:
            ax.plot(xpoints, ypoints, 'g.-')
        ax.set_title(title)
        xlabel = setpoint['label'] or setpoint['name']
        xlabel += f' ({setpoint['unit']})' if setpoint['unit'] else ''
        ax.set_xlabel(xlabel)
        ylabel = d['label'] or d['name']
        ylabel += f' ({d['unit']})' if d['unit'] else ''
        ax.set_ylabel(ylabel)
        if rescale_axes:
            data_lst = [setpoint_dict, d]
            _rescale_ticks_and_units(ax, data_lst)
        axes.append(ax)
    return axes


def plot_fit(dependent, independent, setpoints, fit, metadata, run_id,
             rescale_axes=True, show_variance=False):

    if len(independent) > 1:
        raise NotImplementedError("Plotting only currently works for "
                                  "fitters with 1 independent variable")
    indept = independent[0]
    dept = dependent

    axes = []
    colorbar = None
    title = "Run #{} (#{} fitted), Experiment {} ({})".format(
        run_id,
        metadata['inferred_from']['run_id'],
        metadata['inferred_from']['exp_id'],
        metadata['inferred_from']['sample_name'])

    # find dimension of plot and generate additional label text
    text = None
    if len(setpoints) == 0:
        dimension = 1
    elif all(len(s['data'] == 1) for s in setpoints):
        dimension = 1
        text_list = []
        for s in setpoints:
            text_list.append(
                '{} = {:.3g} {}'.format(s['name'], s['data'][0], s['unit']))
            text = '\n'.join(text_list)
    elif len([1 for s in setpoints if len(s['data'] > 1)]) == 1:
        dimension = 2
        text_list = []
        new_setpoints = []
        for s in setpoints:
            if len(s['data']) == 1:
                text_list.append(
                    '{} = {:.3g} {}'.format(s['name'], s['data'][0], s['unit']))
                text = '\n'.join(text_list)
            else:
                new_setpoints.append(s)
            setpoints = s
    elif len(setpoints) == 1:
        dimension = 2
    else:
        raise NotImplementedError(
            "Plotting for more than one setpoint not yet implemented")

    # make the plots
    if dimension == 1:  # 1D PLOTTING - data + fit 1d plot
        if metadata['fitter']['method'] == 'LeastSquares':
            ax = plot_least_squares_1d(indept, dept, fit[0], metadata,
                                       show_variance=show_variance,
                                       rescale_axes=rescale_axes,
                                       text=text)
            ax.set_title(title)
            axes.append(ax)
        else:
            warning.warn('Attempt to plot a 1d plot of a non LeastSquares fit')
    elif dimension == 2:  # 2D PLOTTING: 2d fit heat map plot + fit param plots
        setpoint = setpoints[0]
        x, y, z = [], [], []
        fit_dicts = []
        variance_dicts = {}
        setpoint_dict = next(
            f for f in fit[0] if f['name'] == setpoint['name'])
        success_dict = next(f for f in fit[0] if f['name'] == 'success')
        fit_param_dicts = []
        var_param_dicts = []
        for fit_param in metadata['fitter']['fit_parameters']:
            d = next(f for f in fit[0] if f['name'] == fit_param)
            fit_param_dicts.append(d)
            if show_variance and 'variance_parameters' in metadata['fitter']:
                for var_param in metadata['fitter']['variance_parameters']:
                    d = next(f for f in fit[0] if f['name'] == var_param)
                    fit_param_dicts.append(d)
                    var_param_dicts = f
        for i, val in enumerate(setpoint_dict['data']):
            indices = np.argwhere(setpoint['data'] == val)
            x.append(indept['data'][indices])
            y.append(setpoint['data'][indices])
            success = success_dict['data'][i]
            if success:
                fit_vals = {d['name']: d['data'][i] for d in fit_param_dicts}
                z.append(fitter.evaluate(indept['data'], **fit_vals))
            else:
                z.append([None] * len(indept['data'][indices]))
        xpoints = np.array(x).flatten()
        ypoints = np.array(y).flatten()
        zpoints = np.array(z).flatten()

        # Make 2D heatmap plot
        ax = plot_heat_map(xpoints, ypoints, zpoints,
                           indept['label'], setpoint['label'], dept['label'],
                           indept['unit'], setpoint['unit'], dept['unit'])
        if rescale_axes:
            data_lst = [indept, setpoint, dept]
            _rescale_ticks_and_units(ax, data_lst, colorbar)
        axes.append(ax)

        # Make fit parameter vs setpoint plots
        axes += plot_fit_param_1ds(setpoint, fit_param_dicts, var_param_dicts)

    else:  # 3D plot which we can't do :(
        warning.warn("Plotting for more than one setpoint not yet implemented")
    return axes, colorbar
