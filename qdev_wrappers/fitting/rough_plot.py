# take least_squares_fitter or baysian_analyzer, and data
#output plot of both
import matplotlib.pyplot as plt
import numpy as np


def plot_1d(xdata, ydata, instrument, rescale_axes=True):

    fig, ax = plt.subplots(1, 1)

    params = instrument.model.modelparam_names
    parameter_values = [instrument.get(param) for param in params]
    #parameter_variance = [instrument.param.variance]

    title = "Run #{} fitted, Experiment {} ({}) \n {} results".format('No run_id', #self.experiment_info['run_id'],
                                                                      'No exp_id',#self.experiment_info['exp_id'],
                                                                      'No sample',#self.experiment_info['sample_name'],
                                                        instrument.name)
    ax.set_title(title)

    # plot data
    ax.plot(xdata['data'], ydata['data'], marker='.', markersize=5, linestyle='', color='C0')

    # plot model
    x = np.linspace(xdata['data'].min(), xdata['data'].max(), len(xdata['data']) * 10)
    ax.plot(x, instrument.model.func(x, *parameter_values), color='C1')

    # set axes labels and title
    ax.set_xlabel(f"{xdata['label']} ({xdata['unit']})")
    ax.set_ylabel(f"{ydata['label']} ({ydata['unit']})")
    if rescale_axes:
        pass
        #data_lst = [xdata, ydata]
        #_rescale_ticks_and_units(ax, data_lst)

    # add fit result summary box
    p_label_list = [instrument.model.func_str]
    for param in params:
        value = instrument.get(param)
        unit = instrument.model.model_parameters[param]['unit']
        p_label_list.append(r'{} = {:.3g} {}'
                                .format(param, value, unit))
        #standard_dev = np.sqrt(parameter_variance[parameter])
        #p_label_list.append(r'{} = {:.3g} +/- {:.3g} {}'
        #                        .format(parameter, value, standard_dev, unit))
        textstr = '\n'.join(p_label_list)

    ax.text(1.05, 0.7, textstr, transform=ax.transAxes, fontsize=14,
            verticalalignment='top', bbox={'ec': 'k', 'fc': 'w'})