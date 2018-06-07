import numpy as np
import matplotlib.pyplot as plt


def plot_fit1d(data, fit1d, fitclass, plottype='scatter'):

    plot = plt.figure()
    axes = plot.add_axes([0.1, 0.1, 0.8, 0.8])
    
    xname = fit1d['inferred_from']['xdata']
    xdata = data[xname]['data']
    xlabel = data[xname]['label']
    xunit = data[xname]['unit']
    axes.set_xlabel('{} [{}]'.format(xlabel, xunit))
        
    yname = fit1d['inferred_from']['ydata']
    ydata = data[yname]['data']
    ylabel = data[yname]['label']
    yunit = data[yname]['unit']
    axes.set_ylabel('{} [{}]'.format(ylabel, yunit))
    
    axes.set_title('{} vs. {}'.format(ylabel, xlabel))
    
    parameters = list(fitclass.p_labels)
    for index, parameter in enumerate(parameters):
        parameters[index] = fit1d['parameters'][parameter]['value']

    x = np.linspace(xdata.min(), xdata.max(), len(xdata)*10)    # Parameters are currently without units!!!
    axes.plot(x, fitclass.fun(x, *parameters), color='C0')

    if plottype == 'line':          
        axes.plot(xdata, ydata, color='C0')
    elif plottype == 'scatter':
        axes.plot(xdata, ydata, marker='.', markersize=5, linestyle='', color='C0')
    else:                              
        raise ValueError('Unknown plottype. Please choose point or line plot.')
        

def plot_fit2d_slice(data, fits2d, fitclass, setvalue, plottype='scatter'):
    
    plot = plt.figure()
    axes = plot.add_axes([0.1, 0.1, 0.8, 0.8])
    axes.set_title('Title')
    
    setpoint = fits2d['inferred_from']['setpoints']
    setname = fits2d['inferred_from'][setpoint]
    setdata = data[setname]['data']
    
    if setvalue not in setdata:
        print('{}: {}'.format(setname, np.unique(setdata)))
        raise RuntimeError('Setvalue not in set points for this fit. Choose from setvalues above.')
    
    if setpoint == 'xdata':
        xname = fits2d['inferred_from']['ydata']
        xdata = data[xname]['data']
        xlabel = data[xname]['label']
        xunit = data[xname]['unit']
        axes.set_xlabel('{} [{}]'.format(xlabel, xunit))
        
    elif setpoint == 'ydata':
        xname = fits2d['inferred_from']['xdata']
        xdata = data[xname]['data']
        xlabel = data[xname]['label']
        xunit = data[xname]['unit']
        axes.set_xlabel('{} [{}]'.format(xlabel, xunit))
        
    yname = fits2d['inferred_from']['zdata']
    ydata = data[yname]['data']
    ylabel = data[yname]['label']
    yunit = data[yname]['unit']
    axes.set_ylabel('{} [{}]'.format(ylabel, yunit))
    
    axes.set_title('{} vs. {}'.format(ylabel, xlabel))
    
    x_dat = []
    y_dat = []
    for xpoint, ypoint, setpoint in zip(xdata, ydata, setdata):
        if setpoint == setvalue:
            x_dat.append(xpoint)
            y_dat.append(ypoint)
    xdata = np.array(x_dat)
    ydata = np.array(y_dat)
            
    parameters = list(fitclass.p_labels)
    for index, parameter in enumerate(parameters):  # Parameters are currently without units!!!
        parameters[index] = fits2d[setvalue]['parameters'][parameter]['value']
    
    x = np.linspace(xdata.min(), xdata.max(), len(xdata)*10)
    axes.plot(x, fitclass.fun(x, *parameters), color='C0')
        
    if plottype == 'line':          
        axes.plot(xdata, ydata, color='C0')
    elif plottype == 'scatter':
        axes.plot(xdata, ydata, marker='.', markersize=5, linestyle='', color='C0')
    else:                              
        raise ValueError('Unknown plottype. Please choose point or line plot.')