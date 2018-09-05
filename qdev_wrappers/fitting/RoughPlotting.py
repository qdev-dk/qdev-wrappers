import numpy as np
import matplotlib.pyplot as plt


def plot_fit1d(data, fit1d, fitclass, plottype='scatter'):

    plot = plt.figure()
    axes = plot.add_axes([0.1, 0.1, 0.8, 0.8])

    # get data, label and units for the two axes, and set appropriate axis labels
    xname = fit1d['inferred_from']['inputs'][fitclass.fun_vars[0]]
    xdata = data[xname]['data']
    xlabel = data[xname]['label']
    xunit = data[xname]['unit']
    axes.set_xlabel('{} [{}]'.format(xlabel, xunit))

    yname = fit1d['inferred_from']['output'][fitclass.fun_output[0]]
    ydata = data[yname]['data']
    ylabel = data[yname]['label']
    yunit = data[yname]['unit']
    axes.set_ylabel('{} [{}]'.format(ylabel, yunit))

    # set plot title
    axes.set_title('{} vs. {}'.format(ylabel, xlabel))

    # make list of fitted parameter values in the order the fitclass method 'fun' takes them
    parameters = list(fitclass.p_labels)
    for index, parameter in enumerate(parameters):
        parameters[index] = fit1d['parameters'][parameter]['value']

    # add the fit to the plot, using the fitted parameter list to find points on the fit
    x = np.linspace(xdata.min(), xdata.max(), len(xdata) * 10)
    axes.plot(x, fitclass.fun(x, *parameters), color='C0')

    # plot the data
    if plottype == 'line':
        axes.plot(xdata, ydata, color='C0')
    elif plottype == 'scatter':
        axes.plot(xdata, ydata, marker='.',
                  markersize=5, linestyle='', color='C0')
    else:
        raise ValueError('Unknown plottype. Please choose point or line plot.')


def plot_fit2d_slice(data, fits2d, fitclass, setvalue, plottype='scatter'):
    """ Takes a 2D dataset and fit, and plots a 1D cross-section of the data at the setpoint specified by
        'setvalue', along with the fit at that setpoint. """

    plot = plt.figure()
    axes = plot.add_axes([0.1, 0.1, 0.8, 0.8])

    # get setpoint name and data
    setpoint = fits2d['inferred_from']['setpoints'][0]
    setdata = data[setpoint]['data']

    # confirm tha the setvalue tha the cross-section should be taken at is in fact one of the setpoints from the data
    if setvalue not in setdata:
        print('{}: {}'.format(setname, np.unique(setdata)))
        raise RuntimeError(
            'Setvalue not in set points for this fit. Choose from setvalues above.')

    # get data, label and units for the two axes, and set appropriate axis labels
    xname = fits2d['inferred_from']['inputs'][fitclass.fun_vars[0]]
    xdata = data[xname]['data']
    xlabel = data[xname]['label']
    xunit = data[xname]['unit']
    axes.set_xlabel('{} [{}]'.format(xlabel, xunit))

    yname = fits2d['inferred_from']['output'][fitclass.fun_output[0]]
    ydata = data[yname]['data']
    ylabel = data[yname]['label']
    yunit = data[yname]['unit']
    axes.set_ylabel('{} [{}]'.format(ylabel, yunit))

    # set plot title
    axes.set_title('{} vs. {} at {}={}'.format(
        ylabel, xlabel, setpoint, setvalue))

    # select, from the full data for the two axes, only the data that corresponds to the chosen setpoint
    x_dat = []
    y_dat = []
    for xpoint, ypoint, setpoint in zip(xdata, ydata, setdata):
        if setpoint == setvalue:
            x_dat.append(xpoint)
            y_dat.append(ypoint)
    xdata = np.array(x_dat)
    ydata = np.array(y_dat)

    # make list of fitted parameter values in the order the fitclass method 'fun' takes them
    parameters = list(fitclass.p_labels)
    for index, parameter in enumerate(parameters):
        parameters[index] = fits2d[setvalue]['parameters'][parameter]['value']

    # add the fit to the plot, using the fitted parameter list to find points on the fit
    x = np.linspace(xdata.min(), xdata.max(), len(xdata) * 10)
    axes.plot(x, fitclass.fun(x, *parameters), color='C0')

    # plot the data
    if plottype == 'line':
        axes.plot(xdata, ydata, color='C0')
    elif plottype == 'scatter':
        axes.plot(xdata, ydata, marker='.',
                  markersize=5, linestyle='', color='C0')
    else:
        raise ValueError('Unknown plottype. Please choose point or line plot.')
