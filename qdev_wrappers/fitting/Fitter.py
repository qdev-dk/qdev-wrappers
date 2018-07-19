import qcodes as qc
import numpy as np
import dill

from qdev_wrappers.fitting.Fitclasses import T1, T2
from scipy.optimize import curve_fit


def fit_data(data, fitclass, fun_inputs, fun_output, setpoint_params=None, p0=None, **kwargs):

    """ This takes as arguments the data dictionary, the desired fit class as a LeastSquaresFit
        class (which defines the function to be fitted to the data), function inputs and outputs
        as a dictionary of the form {'x' : 'variable_name'}, and optionally setpoint parameters as
        a list.

        It returns a dictionary containing the fitted parameters and an array of "estimated"
        outputs given the fit (i.e. what this fit and parameters predict the measurement would have
        given at each point), as well as some metadata about the fit.

        It first checks that the arguments given for setpoints, inputs and outputs matches the input
        needed for fitting to the specified fit class. Then it creates an instance of the appropriate
        fitter class, and calls the 'find_fit' method of the fitter, saving it in the variable 'fit'.
        This method creates a dictionary with the fit.

        Finally, it preserves the fitter and fitclass used to perform the fit by pickling them via the
        dill module, and adds the binary to the fit dictionary."""

    check_input_matches_fitclass(fitclass, fun_inputs, fun_output, setpoint_params, p0)

    # this is used to decide which fitter class to create an instance of. If they are combined, this won't be needed.
    fun_dim = len(fitclass.fun_vars)
    num_inputs = len(fun_inputs)
    if setpoint_params is not None:
        num_setpoints = len(setpoint_params)
    else: num_setpoints = 0

    # creates an instance of the relevant fitter based on the number of setpoints and inputs and the dimensionality
    # of the function to be fitted. If there were just one fitter class, the if statements wouldn't be needed.
    if fun_dim == 1 and num_inputs == 1 and num_setpoints == 0:
        fitter = Fitter1D(data, fun_inputs, fun_output)
    elif fun_dim == 1 and num_inputs == 1 and num_setpoints == 1:
        fitter =Fitter_2Ddata_1Dfunction(data, fun_inputs, fun_output)    #what does the fitter actually need??
    else:
        raise NotImplementedError('''You have specified a {}-dimensional function, {} function inputs, and 
        {} setpoints. This process is currently so specific that your only options are to fit to 1D functions,
        provide 1 input, and have either 0 or 1 setpoint types. Sorry.'''.format(fun_dim, num_inputs, num_setpoints))

    # the fitter performs the fit and saves a dictionary containing the results in variable 'fit'
    fit = fitter.find_fit(data, fitclass, fun_inputs, fun_output, setpoint_params, p0, **kwargs)

    # the fitter and fit class used for the fit are preserved via dill and added to the fit dictionary
    dill_fitclass = dill.dumps(fitclass)
    dill_fitter = dill.dumps(fitter)

    fit['inferred_from']['estimator']['dill'] = {'fitclass' : dill_fitclass, 'fitter' : dill_fitter}

    return fit

def check_input_matches_fitclass(fitclass, inputs, output, setpoints, p0=None):

    """ This function takes the same arguments as the 'fit_data' function, and confirms that the
        given arguments are in the correct format for the 'fit_data' function to proceed, and that
        they match the expected inputs for the specified fit class.

        Each fit class describes a mathematical function to be fitted to, with a set of attributes,
        including which variables the function has as inputs, and what outputs it has. This function
        makes sure that the correct inputs and outputs are specified compared to what inputs and
        outputs the mathematical function has, and that they are specified in the correct format. It
        also checks that setpoints are given in the correct format (a list). If guess parameters are
        specified, it checks that the length of the parameter list is the expected number of
        parameters for the function chosen. """

    # check input and output are given, and that input, output and setpoints are in correct format
    if (type(inputs) != dict or type(output) != dict):
        raise RuntimeError('''Please specify both input and output variables for the function you wish to fit in
    #                    the format fun_inputs = {'x':'name', 'y':'other_name'}, fun_output = {z: 'another_name'} ''')
    if (setpoints is not None) and (type(setpoints) != list):
        raise RuntimeError('''Please specify setpoints as a list ['setpoint_name', ...], even if there is only one.''')

    # check inputs/outputs specified match inputs/outputs function takes
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
        setpoints when relevant, and optionally, guess parameters, and returns a fit dictionary. The fit class is
        a LeastSqauresFit class describing a mathematical function that can be fitted to data, while the Fitter
        class performs the fitting. All other methods in the fitter are com

        Much of the fitting is generic and does not depend on the number of inputs, outputs or setpoints in the
        specified LeastSquaresFit class; however, depending on the dimensionality of the function to be fitted
        and the measured data, the function 'perform_fit' varies.

        Currently, Fitter is a parent class with no 'perform_fit' method of its own, and two child classes inherit
        from it: a class for 1D fits to 1D data (i.e. one variable, one output and no setpoints) and a class for
        1D fits to 2D data (i.e. one variable, one setpoint and one output). """

    #TODO: perform_fit and find_fit are two different functions with deceptively similar names. This could be improved.
    #TODO: I think with some changes, perform_fit could be made generic, so only one Fitter class was needed

    def __init__(self, data, inputs, output):

        self.input_vars = [variable for variable in inputs.keys()]
        self.output_var = [variable for variable in output.keys()]
        self.output_dataname = [dataname for dataname in output.values()]
        self.all_datanames = []
        self.full_parameter_dict = {}

        self.setpoint_params = []

    def find_fit(self, data, fitclass, fun_inputs, fun_output, setpoint_params=None, p0=None, **kwargs):

        """ find_fit combines other Fitter methods to organize the data, find fitted parameters and save
        them to a fit dictionary. It then adds parameter units to the fit dictionary, uses the fitted
        parameters and the given data to calculate estimated outputs given the fitten function, and adds
        metadata about the data and the fit to fit['inferred_from']

        As arguments, it takes the data dictionary produced by the Converter, a LeastSquaresFit class
        that defines the mathematical function to be fitted to the data, the inputs and outputs for the
        mathematical function in the format {'x' : 'dataname', ...}. Optionally, it also takes a list of
        setpoint parameters if any in the format ['dataname1', ... ], and a list of guess parameters if
        they are being specified manually instead of estimated by the LeastSquaresFit 'guess' function."""

        # organize data in a format needed later (see 'organize_data' function)
        data_kwargs, unit_dict = self.organize_data(data, fun_inputs, fun_output, setpoint_params)

        # fit parameters via SciPy curve_fit and save to fit dictionary
        fit = self.perform_fit(data_kwargs, data, fitclass, setpoint_params, p0, **kwargs)

        # find parameter units and save to fit dictionary
        fit['parameter units']= self.find_parameter_units(fitclass, unit_dict)

        # use fitted parameters and data to find the estimated output of the fitted function
        fit['estimate'] = self.estimate_function_values(fitclass, data, data_kwargs)

        # save metadata
        fit['inferred_from'] = {'inputs': fun_inputs,
                                'output': fun_output,
                                'setpoints': setpoint_params,
                                'run_id': data['run_id'],
                                'exp_id': data['exp_id'],
                                'dependencies': data['dependencies'],
                                'estimator' : {'method': 'Least squared fit',
                                                'type': fitclass.name,
                                                'function used': str(fitclass.fun_np),
                                                }
                                }

        return fit

    def organize_data(self, data, inputs, output, setpoints):

        """ This function organizes the data based on the inputs, outputs and setpoints specified.

            First, it makes a list of all data names from inputs, outputs and setpoints, and confirms
            that those data names are all present in the actual data dictionary. That is, it makes
            sure that if you have said that inputs are {'x': 'frequency'}, that 'frequency' is among
            the variables present in the data. It makes a list of all variables that will be used, and
            saves them as Fitter attribute self.all_datanames

            Second, it makes and returns two dictionaries, for units and for data arrays:
                data_kwargs = {'x': np.array, 'y': np.array ...} and
                unit_dict = {'x': 'unit', 'y': 'unit' ...}.

            The data_kwargs dict will be used later as **kwargs in a variety of functions that need
            inputs like 'x = np.array'. The unit dictionary specifies the unit for each input variable
            of the mathematical function being fitted, and will be used to find the parameter units
            in find_parameter_units. """

        # make a list of all datanames specefied by the inputs, outputs and setpoints
        all_vars = [dataname for dataname in inputs.values()]
        for dataname in output.values():
            all_vars.append(dataname)
        if setpoints is not None:
            for dataname in setpoints:
                all_vars.append(dataname)
        # confirm all variables involved are in the data dictionary
        for dataname in all_vars:
            if dataname not in data.keys():
                raise RuntimeError('''Variable {} not found in data dictionary. Data dictionary contains 
                                                        variables: {}'''.format(dataname, data['variables']))
        self.all_datanames = all_vars

        # make a dictionary of data arrays and units in format {'x' : np.array...} and {'x' : 'unit', ...}
        data_kwargs = {}
        unit_dict = {}

        for variable, name in inputs.items():
            data_kwargs[variable] = data[name]['data']
            unit_dict[variable]  = data[name]['unit']

        for variable, name in output.items():
            data_kwargs[variable] = data[name]['data']
            unit_dict[variable] = data[name]['unit']

        return data_kwargs, unit_dict

    def find_start_parameters(self, fitclass, p0, data_kwargs):

        """ Takes as arguments the fit class, the guess parameters if any, and the "data_kwargs",
            which is not the data as originally given, but the data arrays organized by variables
            by the organize_data function. It has the format {"x": np.array, ...}, so that it can
            unpacked as keyword arguments for the mathematical functions.

            If no guess parameters are specified, the guess function from the fit class is given
            key word arguments from the unpacked data_kwargs, and returns a set of guess parameters.
            If guess parameters have been specified explicitly, then those are used instead. """

        if (p0 is None and hasattr(fitclass, 'guess')):
            p0 = getattr(fitclass, 'guess')(**data_kwargs)
            return p0
        elif p0 is not None:
            p0 = p0
            return p0
        else:
            return "Could not find guess parameters for fit."

    def find_parameter_units(self, fitclass, unit_dict):

        """ This uses the relationship between the units stored in the fitclass attribute 'p_units' and
            the unit labels for the data to determine the unit labels for each parameter.

            For example: according to the p_units attribute, the unit for the first parameter in the list
            is 1/y. Based on the data that has been organized by organize_data and stored in the unit_dict,
            the unit for y are 'S', so this function concludes that the units for the first parameter are 1/S
            (it does not know that this is Hz, its not that clever).

            It returns a dictionary in the format {"p1" : unit, "p2" : unit ...} of all function parameters,
            where the key is the parameters as specified in the fitclass attribute p_labels. """

        # unit labels could fx. be [a, T, w, p, c], and unit templates could be ['y', 'x', '1/x', '', 'y']
        unit_templates = fitclass.p_units
        unit_labels = fitclass.p_labels
        param_units = {}

        # zip the two lists together and take the elements one at a time
        for template, label in zip(unit_templates, unit_labels):
            # for each element, make the template a list. 'y' --> ['y'], '1/x' --> ['1', '/', 'x']
            template = list(template)
            # go through each element of the template list, and compare to the variables in the unit_dict
            for i in range(len(template)):
                for variable in unit_dict.keys():
                    # if the i'th element of the template is one of the variables in unit_dict, replace with the unit
                    # f.x., if {'x': 'S', ...}, ['x', ...] --> ['S', ...]
                    if template[i] == variable:
                        template[i] = unit_dict[variable]
            # join the list again, fx. ['1', '/', 'S'] --> '1/S'
            unit = "".join(template)
            #add the unit to the param_units dictionary
            param_units[label] = unit

        return param_units

    def perform_fit(self, data_kwargs, data, fitclass, setpoints, p0, **kwargs):

        """ A suitably generic version of this function isn't implemented yet. See specific versions in
        child classes.

        The purpose of this function is to find the fitted values of the parameters via SciPy's curve_fit
        function. The complication in making it generic lies in the need to sort the data by setpoints and
        then do multiple fits to subsets of the data if the fitted function is of lower dimensionality than
        the measurement.

        It does two things:

            1. It sets the Fitter attribute self.full_parameter_dict, which is a dictionary that contains all
               of the parameters as keys, and for each key, the value is an array with the same dimension as
               the original data, with the parameter's value for each datapoint in the original data. For
               example, if parameter 1 were found to be 2.5 for the first 5 datapoints, and then the measurement
               was moved to a new setpoint, and the next 5 datapoints had p1 = 3.5, you would have

               self.full_parameter_dict = {"p1" : [[2.5, 2.5, 2.5, 2.5, 2.5, 3.5, 3.5, 3.5 ... ]],
                                                "p2" : [[ ... ]],
                                                ... }

               Thereby saving all the parameters with indicies matching their corresponding datapoints, which
               will be needed for calculating the estimated measurement based on the fit.

            2. It returns a fit dictionary containing the start_params (initial guess), and the value and cov
               matrix for each fitted parameter (organized by setpoint if there were setpoints). """

        raise NotImplementedError("A generic fitter function for the Fitter base class has yet to be implemented.")

    def estimate_function_values(self, fitclass, data, data_kwargs):

        """ Takes fitclass and data, as well as the data_kwargs produced by organize_data, and references the
        Fitter attribute self.full_parameter_dict created by perform_fit. It uses the numpy function saved
        in the LeastSquaresFit class attribute 'fun', giving it the input data and input parameters as numpy
        arrays. It returns a numpy array of 'estimates', i.e. what the predicted output of the fitted function
        would be given the parameter values found by perform_fit and function inputs.

        It returns an estimate dictionary containing the estimate numpy array and information about labels,
        units and parameters used. The parameter array and estimate array are what will be saved in the SQL
        table later."""

        estimate = {}

        # obtain a dictionary containing only input variables in format {"x": np.array, ...}, for **kwargs
        input_data = data_kwargs
        for variable in self.output_var:
                del input_data[variable]

        #obtain parameters, also in the format {"p1" : np.array, ...} for **kwargs
        input_parameters = self.full_parameter_dict

        # Calculate estimated values for output based on function and store in estimate['values']
        estimate['values'] = fitclass.fun(**input_data, **input_parameters)
        # FIXME : PyCharm says this duplicate ** expression is incompatible with versions < 3.5. Is that a problem?

        # Save other info about the estimate
        estimate['name'] = '{}_estimate'.format(self.output_dataname[0])
        estimate['label'] = '{} estimate'.format(data[self.output_dataname[0]]['label'])
        estimate['unit'] = data[self.output_dataname[0]]['unit']
        estimate['parameters'] = self.full_parameter_dict

        return estimate


class Fitter1D(Fitter):

    def perform_fit(self, data_kwargs, data, fitclass, setpoints, p0, **kwargs):

        #make fit dictionary
        fit = { 'parameters': {}, 'start_params': {} }

        #define data arrays
        xdata = data_kwargs[self.input_vars[0]]
        ydata = data_kwargs[self.output_var[0]]

        #find guess for start parameters, run curve_fit function to perform SciPy least squares fit
        p_guess = self.find_start_parameters(fitclass, p0, data_kwargs)
        popt, pcov = curve_fit(fitclass.fun, xdata, ydata, p0=p_guess, **kwargs)

        # save fit information
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

    def perform_fit(self, data_kwargs, data, fitclass, setpoints, p0, **kwargs):

        #Retrieve data
        xarray = data_kwargs[self.input_vars[0]]
        yarray = data_kwargs[self.output_var[0]]
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

        #perform 1D fit for cross section at each setpoint and save to fit dictionary (as in Fitter1D)
        fit = { 'start_params' : {} }

        for set_value, xdata_1d, ydata_1d in zip(unique_setpoints, xdata, ydata):

            data_dict_1d = {self.input_vars[0]:xdata_1d, self.output_var[0]:ydata_1d}

            p_guess = self.find_start_parameters(fitclass, p0, data_dict_1d)
            popt, pcov = curve_fit(fitclass.fun, xdata_1d, ydata_1d, p0=p_guess, **kwargs)

            fit[set_value] = {}
            fit[set_value]['parameters'] = {}
            fit['start_params'][set_value] = {}

            for parameter in fitclass.p_labels:
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
