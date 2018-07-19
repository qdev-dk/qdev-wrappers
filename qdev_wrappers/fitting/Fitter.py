import qcodes as qc
import numpy as np
import dill

from qdev_wrappers.fitting.Converter import SQL_Converter, Legacy_Converter
from qdev_wrappers.fitting.Fitclasses import T1, T2
from scipy.optimize import curve_fit


def fit_data(data, fitclass, fun_inputs, fun_output, setpoint_params=None, p0=None, **kwargs):

    check_input_matches_fitclass(fitclass, fun_inputs, fun_output, setpoint_params, p0)

    fun_dim = len(fitclass.fun_vars)
    num_inputs = len(fun_inputs)
    if setpoint_params is not None:
        num_setpoints = len(setpoint_params)
    else: num_setpoints = 0


    if fun_dim == 1 and num_inputs == 1 and num_setpoints == 0:
        fitter = Fitter1D(data, fitclass, fun_output)
    elif fun_dim == 1 and num_inputs == 1 and num_setpoints == 1:
        fitter =Fitter_2Ddata_1Dfunction(data, fitclass, fun_output)    #what does the fitter actually need??

    fit = fitter.find_fit(data, fitclass, fun_inputs, fun_output, setpoint_params, p0, **kwargs)

    dill_fitclass = dill.dumps(fitclass)
    dill_fitter = dill.dumps(fitter)

    fit['inferred_from']['estimator']['dill'] = {'fitclass' : dill_fitclass, 'fitter' : dill_fitter}

    return fit

def check_input_matches_fitclass(fitclass, inputs, output, setpoints, p0):

    # check input and output are given, and that input, output and setpoints are in correct format
    if (type(inputs) != dict or type(output) != dict):
        raise RuntimeError('''Please specify both input and output variables for the function you wish to fit in
    #                    the format fun_inputs = {'x':'name', 'y':'other_name'}, fun_output = {z: 'another_name'} ''')
    if (setpoints is not None) and (type(setpoints) != list):
        raise RuntimeError('''Please specify setpoints as a list ['setpoint_name', ...], even if there is only one.''')

    # check inputs specified match inputs function takes
    if len(inputs) != len(fitclass.fun_vars):
        raise RuntimeError('''The function you are fitting to takes {} variables, 
                        and you have specified {}'''.format(len(fitclass.fun_vars), len(inputs)))
    for variable in inputs.keys():
        if variable not in fitclass.fun_vars:
            raise RuntimeError('''You have specified a variable {}. 
                                The fit function takes variables {}'''.format(variable, fitclass.fun_vars))
    for variable in output.keys():
        if variable not in fitclass.fun_output:
            raise RuntimeError('''You have specified a variable {}. 
                                The fit function returns variables {}'''.format(variable, fitclass.fun_output))

    # check that if a guess p0 is specified, the number of parameters is correct for the fit function
    if (p0 is not None) and (len(p0) != len(fitclass.p_labels)):
        raise RuntimeError('''You have specified {} start parameters for the fit function: {}. The function takes 
                        {} start parameters: {}'''.format(len(p0), p0, len(fitclass.p_labels), fitclass.p_labels))

class Fitter:

    """ The fitter has a method, 'find_fit', which takes the fitclass, data, function inputs, function outputs,
     setpoints when relevant, and optionally, guess parameters, and returns a fit dictionary. It does this by
     using all the other methods in the Fitter to fit a particular function (as defined in a LeastSquaresFit
     class) to the specified data.

     Much of the fitting is generic and does not depend on the number of inputs, outputs or setpoints in the
     specified LeastSquaresFit class; however, depending on the dimensionality of the function to be fitted
     and the measured data, the function 'perform_fit' varies """

    def __init__(self, data, fitclass, output):

        self.fitclass = fitclass    #'UNNECESSARY??'
        self.fun_dim = len(fitclass.fun_vars) #'UNNECESSARY??'
        self.data_dim = 'undefined'
        self.input_vars = []
        self.output_var = []
        self.all_datanames = []
        self.full_parameter_dict = 'undefined'
        self.output_dataname = []

        self.input_dataname = []
        self.setpoint_params = []

        self.input_data = []
        self.output_data = []

    def find_fit(self, data, fitclass, fun_inputs, fun_output, setpoint_params=None, p0=None, **kwargs):

        data_dict, label_dict, name_dict, unit_dict = self.organize_data(data, fun_inputs, fun_output, setpoint_params)

        fit = self.perform_fit(data_dict, data, fitclass, setpoint_params, p0, **kwargs)

        fit['parameter units']= self.find_parameter_units(fitclass, unit_dict)

        fit['estimate'] = self.estimate_function_values(fitclass, data, data_dict)

        fit['inferred_from'] = {'inputs': fun_inputs,
                                'output': fun_output,
                                'setpoints': setpoint_params,
                                'run_id': data['run_id'],
                                'exp_id': data['exp_id'],
                                'dependencies': data['dependencies'],
                                'data_dimensions': self.data_dim,
                                'estimator' : {'method': 'Least squared fit',
                                                'type': fitclass.name,
                                                'function used': str(fitclass.fun_np),
                                                }
                                }

        return fit

    def organize_data(self, data, inputs, output, setpoints):

        all_vars = [dataname for dataname in inputs.values()]
        for dataname in output.values():
            all_vars.append(dataname)
        if setpoints is not None:
            for dataname in setpoints:
                all_vars.append(dataname)
        # confirm all variables involved are in the dataset
        for dataname in all_vars:
            if dataname not in data.keys():
                raise RuntimeError('''Variable {} not found in data dictionary. Data dictionary contains 
                                                        variables: {}'''.format(dataname, data['variables']))
        self.all_datanames = all_vars
        self.data_dim = len(self.all_datanames) - 1

        data_dict = {}
        label_dict = {}
        name_dict = {}
        unit_dict = {}

        for variable, name in inputs.items():
            data_dict[variable] = data[name]['data']
            label_dict[variable] = data[name]['label']
            name_dict[variable]  = data[name]['name']
            unit_dict[variable]  = data[name]['unit']

        for variable, name in output.items():
            data_dict[variable] = data[name]['data']
            label_dict[variable] = data[name]['label']
            name_dict[variable] = data[name]['name']
            unit_dict[variable] = data[name]['unit']

        self.input_vars = [variable for variable in inputs.keys()]
        self.output_var = [variable for variable in output.keys()]
        self.input_dataname = [dataname for dataname in inputs.values()]
        self.output_dataname = [dataname for dataname in output.values()]

        return data_dict, label_dict, name_dict, unit_dict

    def find_start_parameters(self, fitclass, p0, data_dict):

        if (p0 == None and hasattr(fitclass, 'guess')):
            p0 = getattr(fitclass, 'guess')(**data_dict)
            return p0
        elif p0 != None:
            p0 = p0
            return p0
        else:
            return "Could not find guess parameters for fit."

    def find_parameter_units(self, fitclass, unit_dict):

        unit_templates = fitclass.p_units
        unit_labels = fitclass.p_labels
        param_units = {}

        for template, label in zip(unit_templates, unit_labels):
            template = list(template)
            for i in range(len(template)):
                for variable in unit_dict.keys():
                    if template[i] == variable:
                        template[i] = unit_dict[variable]
            unit = "".join(template)
            param_units[label] = unit

        return param_units

    def perform_fit(self, data_dict, data, fitclass, setpoints, p0, **kwargs):

        raise NotImplementedError("A generic fitter function for the Fitter base class has yet to be implemented.")

    def estimate_function_values(self, fitclass, data, data_dict):

        estimate = {}

        input_data = data_dict
        for variable in self.output_var:
                del input_data[variable]

        input_parameters = self.full_parameter_dict

        # Calculate estimated values for output based on function and store in estimate['values']
        estimate['values'] = fitclass.fun(**input_data, **input_parameters)

        # Save estimate
        estimate['name'] = '{}_estimate'.format(self.output_dataname[0])
        estimate['label'] = '{} estimate'.format(data[self.output_dataname[0]]['label'])
        estimate['unit'] = data[self.output_dataname[0]]['unit']
        estimate['parameters'] = self.full_parameter_dict   #not sure this is used for anything

        return estimate


class Fitter1D(Fitter):

    def perform_fit(self, data_dict, data, fitclass, setpoints, p0, **kwargs):

        fit = {}
        fit['parameters'] = {}
        fit['start_params'] = {}

        xdata = data_dict[self.input_vars[0]]
        ydata = data_dict[self.output_var[0]]

        p_guess = self.find_start_parameters(fitclass, p0, data_dict)
        popt, pcov = curve_fit(fitclass.fun, xdata, ydata, p0=p_guess, **kwargs)

        for parameter in fitclass.p_labels:
            fit['parameters'][parameter] = {'value': popt[fitclass.p_labels.index(parameter)]}
            fit['parameters'][parameter]['cov'] = pcov[fitclass.p_labels.index(parameter)]
            fit['start_params'][parameter] = p_guess[fitclass.p_labels.index(parameter)]

        # make an dictionary containing arrays of each parameter value with same dimension as data (for estimate)
        all_params = {}
        for parameter in fitclass.p_labels:
            all_params[parameter] = []
            for datapoint in xdata:
                all_params[parameter].append(fit['parameters'][parameter]['value'])
            all_params[parameter] = np.array(all_params[parameter])
        self.full_parameter_dict = all_params

        return fit


class Fitter_2Ddata_1Dfunction(Fitter):

    def perform_fit(self, data_dict, data, fitclass, setpoints, p0, **kwargs):

        #Retrieve data
        xarray = data_dict[self.input_vars[0]]
        yarray = data_dict[self.output_var[0]]
        setpoint_array = data[setpoints[0]]['data']

        # Reorganize data by setpoint
        unique_setpoints = np.unique(setpoint_array)

        xdata_lst = []
        ydata_lst = []

        for set_point in unique_setpoints:
            x_dat = []
            y_dat = []
            for setpoint, x, y in zip(setpoint_array, xarray, yarray):
                if setpoint == set_point:
                    x_dat.append(x)
                    y_dat.append(y)
            xdata_lst.append(np.array(x_dat))
            ydata_lst.append(np.array(y_dat))

        xdata = np.array(xdata_lst)
        ydata = np.array(ydata_lst)

        #perform 1D fit for cross section at each setpoint and save to fit dictionary
        fit = {}
        fit['start_params'] = {}

        for set_value, xdata_1d, ydata_1d in zip(unique_setpoints, xdata, ydata):

            data_dict_1d = {self.input_vars[0]:xdata_1d, self.output_var[0]:ydata_1d}

            p_guess = self.find_start_parameters(fitclass, p0, data_dict_1d)
            popt, pcov = curve_fit(fitclass.fun, xdata_1d, ydata_1d, p0=p_guess, **kwargs)

            fit[set_value] = {}
            fit[set_value]['parameters'] = {}
            fit['start_params'][set_value] = {}

            for parameter in fitclass.p_labels:  # parameters currently missing units, use fitclass.p_units
                fit[set_value]['parameters'][parameter] = {'value': popt[fitclass.p_labels.index(parameter)]}
                fit[set_value]['parameters'][parameter]['cov'] = pcov[fitclass.p_labels.index(parameter)]
                fit['start_params'][set_value][parameter] = p_guess[fitclass.p_labels.index(parameter)]



        # Make an array of parameters, specified in the same order as the original setpoint array, before data
        # was rearranged to do the fit. This is for running through the estimation function later.
        all_params = {}
        for parameter in fitclass.p_labels:
            all_params[parameter] = []
            for setpoint in setpoint_array:
                all_params[parameter].append(fit[setpoint]['parameters'][parameter]['value'])
            all_params[parameter] = np.array(all_params[parameter])
        self.full_parameter_dict = all_params

        return fit




    #def fit_2d_function_to_2d_data(self):
     #   print('This does not work yet.')


    #is data_dict helpful? What are all theses things I've defined now, and how many of them are just reworks
    #the same stuff?