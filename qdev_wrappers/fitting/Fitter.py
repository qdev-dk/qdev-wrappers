import qcodes as qc
import numpy as np
import dill

from qdev_wrappers.fitting.Converter import SQL_Converter, Legacy_Converter
from qdev_wrappers.fitting.Fitclasses import T1, T2
from scipy.optimize import curve_fit


        

def do_fit(data, fitclass, x=None, y=None, z=None, cut='horizontal', p0=None,**kwargs):

    def find_start_parameters(fitclass, p0, xdata, ydata):

        if (p0 == None and hasattr(fitclass, 'guess')):
            p0 = getattr(fitclass, 'guess')(xdata, ydata)
            return p0
        elif p0 != None:
            p0 = p0
            return p0
        else:
            return "Could not find guess parameters for fit."


    if type(fitclass) == type:
        #Maybe I'm just an idiot, and this isn't necessary for the world-at-large, but
        #I spent about 45 minutes trying to figure out what I broke before I realized
        #that I just forgot the parentheses after the fitclass. So this is here for now.
        raise RuntimeError('It looks like there is something wrong with your fitclass(). Possibly you forgot the parentheses?')
        
    if (x==None or y==None):
        raise RuntimeError('Please specify data for x, y (and optionally z)')

    for dataname in [x, y, z]:
        if (dataname not in data['variables']) and (dataname is not None):
            raise RuntimeError('The specified variable "{}" is not found in the variables for this data dictionary. Variables are {}'.format(dataname, data['variables']))

    # specify x, y and z
    x_dict = data[x]
    y_dict = data[y]
    dimensions = 1

    if z != None:
        z_dict = data[z]
        dimensions = 2

    # find parameter units
    if dimensions == 1:
        cut = 'horizontal'  # Must be horizontal for 1D plots for units to work. Now you can't mess it up.
    unit_template = fitclass.p_units
    param_units = []
    x = x_dict['unit']
    y = y_dict['unit']
    if dimensions == 2:
        z = z_dict['unit']

    for item in unit_template:
        template = list(item)
        if cut == 'horizontal':
            for i in range(len(template)):
                if template[i] == 'x':
                    template[i] = x
                if template[i] == 'y':
                    template[i] = y
                if template[i] == 'z':
                    template[i] = z
        elif cut == 'vertical':
            for i in range(len(template)):
                if template[i] == 'x':
                    template[i] = y
                if template[i] == 'y':
                    template[i] = x
                if template[i] == 'z':
                    template[i] = z
        unit = "".join(template)
        param_units.append(unit)

    #Do fit for 1D data
    if dimensions == 1:

        xdata = x_dict['data']
        ydata = y_dict['data']

        fit = {}
        fit['parameters'] = {}
        fit['start_params'] = {}

        guess = find_start_parameters(fitclass, p0, xdata, ydata)
        popt, pcov = curve_fit(fitclass.fun, xdata, ydata, p0=guess, **kwargs)

        for parameter in fitclass.p_labels:
            fit['parameters'][parameter] = {'value': popt[fitclass.p_labels.index(parameter)]}
            fit['parameters'][parameter]['cov'] = pcov[fitclass.p_labels.index(parameter)]
            fit['parameters'][parameter]['unit'] = param_units[fitclass.p_labels.index(parameter)]
            fit['start_params'][parameter] = guess[fitclass.p_labels.index(parameter)]


        fit['inferred_from'] = {'xdata': x_dict['name'],
                                        'ydata': y_dict['name'],
                                        'dataset': data['run_id'],
                                        'dependencies': data['dependencies']} #missing sample name




    #Do fit for 2D data
    if dimensions == 2:

        xdata = x_dict['data']
        ydata = y_dict['data']
        zdata = z_dict['data']

        fit = {}

        if cut == 'horizontal':
            setarray = ydata
            xarray = xdata

        if cut == 'vertical':
            setarray = xdata
            xarray = ydata

        setpoints = np.unique(setarray)
        yarray = zdata

        #reformats as array of set points, with a y-array and z-array corresponding to each set point

        xdata_lst = []
        ydata_lst = []

        for set_point in setpoints:
            x_dat = []
            y_dat = []
            for setpoint, x, y in zip(setarray, xarray, yarray):
                if setpoint == set_point:
                    x_dat.append(x)
                    y_dat.append(y)
            xdata_lst.append(np.array(x_dat))
            ydata_lst.append(np.array(y_dat))


        xdata = np.array(xdata_lst)
        ydata = np.array(ydata_lst)


        #fitting as a sequence of 1D plots for different set_values

        for set_value, xdata_1d, ydata_1d in zip(setpoints, xdata, ydata):

            guess = find_start_parameters(fitclass, p0, xdata_1d, ydata_1d)
            popt, pcov = curve_fit(fitclass.fun, xdata_1d, ydata_1d, p0=guess, **kwargs)

            fit[set_value] = {}
            fit[set_value]['parameters'] = {}
            fit[set_value]['start_params'] = {}

            for parameter in fitclass.p_labels:            #parameters currently missing units, use fitclass.p_units
                fit[set_value]['parameters'][parameter] = {'value': popt[fitclass.p_labels.index(parameter)]}
                fit[set_value]['parameters'][parameter]['cov'] = pcov[fitclass.p_labels.index(parameter)]
                fit[set_value]['parameters'][parameter]['unit'] = param_units[fitclass.p_labels.index(parameter)]
                fit[set_value]['start_params'][parameter] = guess[fitclass.p_labels.index(parameter)]


        #does this needs to be moved so that it specifies which cut the individual sets of parameters are inferred from?
        fit['inferred_from'] = {'xdata': x_dict['name'],
                                        'ydata': y_dict['name'],
                                        'zdata': z_dict['name'],
                                        'dataset': data['run_id'],
                                        'dependencies': data['dependencies']} #missing sample name

        if cut == 'horizontal':
            fit['inferred_from']['setpoints'] = 'ydata'

        if cut == 'vertical':
            fit['inferred_from']['setpoints'] = 'xdata'


    dill_obj = dill.dumps(fitclass)
    fit['estimator'] = {'method': 'Least squared fit',
                        'type': fitclass.name,
                        'function used': str(fitclass.fun_np),
                        'dill': dill_obj}

    return fit
        

