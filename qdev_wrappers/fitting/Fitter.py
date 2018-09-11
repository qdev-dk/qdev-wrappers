import qcodes as qc
import numpy as np
from scipy.optimize import curve_fit
from itertools import product
from qdev_wrappers.fitting.least_squares_fit import LeastSquaresFit
from typing import Dict

import matplotlib.pyplot as plt
from qcodes.dataset.data_set import load_by_id
from qcodes.dataset.data_export import get_data_by_id
from qcodes.dataset.data_export import (datatype_from_setpoints_1d,
                          datatype_from_setpoints_2d, reshape_2D_data)
from qcodes.dataset.plotting import _rescale_ticks_and_units



class Fitter:
    """
    Class which performs fit for data based on data, fitclass and names of

    Args:
        data (dict)
        fitclass (currently limited to LeastSquaresFit)
        indept_var (str): name of parameter in data dict to be used as
            independent variable in fit procedure. eg 'pulse_readout_delay'
        dept_var (str): name of parameter in data dict which represents
            dependent variable for fitting. eg 'cavity_magnitude_result'
    """

    def __init__(self, data: Dict, fitclass: LeastSquaresFit,
                  indept_var: str, dept_var: str):
        self.fitclass = fitclass
        self.experiment_info = {'exp_id': data['exp_id'],
                                'run_id': data['run_id'],
                                'sample_name': data['sample_name']}
        self.indept_var = data[indept_var]
        self.dept_var = data[dept_var]
        self.setpoints = {k: data[k] for k in data.keys() if
                          (k not in [indept_var, dept_var]) and (k in data['variables'])}
        self.fit_parameters = {
            fitclass.param_names[i]:
            {'name': fitclass.param_names[i],
             'label': fitclass.param_labels[i],
             'unit': fitclass.param_units[i]} for
            i in range(len(fitclass.param_names))}
        self.estimator = {'method': 'LSF',
                          'type': fitclass.name,
                          'fit_function_str': fitclass.fun_str}  # TODO: add dill here
        self.fit_results = self._do_fitting_procedure(data)

    def _do_fitting_procedure(self, data):
        """
        Populates fit_results list with one dictionary per combination
        of setpoints.

        eg
        for self.setpoints = {'frequency':
                                {'label': '',
                                 'unit': 'Hz',
                                 'data': [1e9, 2e9, 3e9]},
                              'power':
                                {'label': '',
                                 'unit': 'dBm',
                                 'data': [-10, -30]}}

        will make 6 dictionaries of the form
        {
            'setpoint_names': ['frequency', 'power'],
            'setpoint_labels': {'frequency': '' , 'power': ''},
            'setpoint_units': {'frequency': 'Hz' , 'power': 'dBm'},
            'setpoint_values': {'frequency': 1e9 , 'power': -10},
            'param_names': ['a', 'b'],
            'param_labels': {'a': 'T1', 'b': 'b'},
            'param_units': {'a': 's', 'b': ''},
            'param_start_values': {'a': 3, 'b': 10},
            'param_values': {'a': 2.5, 'b': 11},
            'param_variance': {'a': 0.1, 'b': 2},
            'indept_var_name': 'pulse_readout_delay',
            'indept_var_label': 'Pulse Readout Delay',
            'indept_var_unit': 's',
            'indept_var_values': [0.1, 0.2, 0.3, 0.4],
            'dept_var_name': 'cavity_magnitude_response',
            'dept_var_label': 'Cavity Response',
            'dept_var_unit': '',
            'dept_var_values': [1.15, 1.26, 1.34, 1.23],
            'estimate_values' [1.1, 1.2, 1.3, 1.4]
        }
        """
        fit_results = []
        # if setpoints then perform fit for all
        if len(self.setpoints) > 0:
#            raise RuntimeError('many setpoints is currently broken, apologies')
            # find all possible combinations of setpoint values
            setpoint_combinations = product(
                *[set(v['data']) for v in self.setpoints.values()])
            setpoint_names = list(self.setpoints.keys())
            setpoint_labels = [v['label'] for v in self.setpoints.values()]
            setpoint_units = [v['unit'] for v in self.setpoints.values()]
            for setpoint_combination in setpoint_combinations:
                # find indices where where setpoint combination is satisfied
                indices = set(np.argwhere(
                    data[setpoint_names[0]]['data'] == setpoint_combination[0]).flatten())
                for i in range(1, len(setpoint_names)):
                    new_indices = np.argwhere(
                            data[setpoint_names[0]]['data'] == setpoint_combination[0]).flatten()
                    indices = indices.intesection(new_indices)
                indices = list(indices)
                input_data_array = data[self.indept_var['name']
                                        ]['data'][indices]
                output_data_array = data[self.dept_var['name']
                                         ]['data'][indices]
                param_dict = self._perform_fit(input_data_array,
                                               output_data_array)
                result = param_dict.copy()
                result.update(
                    {'setpoint_names': setpoint_names,
                     'setpoint_labels': dict(zip(setpoint_names,
                                                 setpoint_labels)),
                     'setpoint_units': dict(zip(setpoint_names,
                                                setpoint_units)),
                     'setpoint_values': dict(zip(setpoint_names,
                                                 setpoint_combination)),
                     'indept_var_values': input_data_array,
                     'dept_var_values': output_data_array,
                     'indept_var_name': self.indept_var['name'],
                     'dept_var_name': self.dept_var['name'],
                     'indept_var_label': self.indept_var['label'],
                     'dept_var_label': self.dept_var['label'],
                     'indept_var_unit': self.indept_var['unit'],
                     'dept_var_unit': self.dept_var['unit'],
                     'estimate_values':
                        self._find_estimate(input_data_array,
                                           param_dict['param_values'])})
                fit_results.append(result)
#                except Exception:  # TODO: what kind of exception
#                    print('no data for setpoint combination ', dict(
#                        zip(self.setpoints.keys(), setpoint_combination)))
        else:
            input_data_array = data[self.indept_var['name']]['data']
            output_data_array = data[self.dept_var['name']]['data']
            param_dict = self._perform_fit(input_data_array,
                                       output_data_array)
            result = param_dict.copy()
            result.update(
                {'setpoint_names': [],
                 'indept_var_values': input_data_array,
                 'dept_var_values': output_data_array,
                 'indept_var_name': self.indept_var['name'],
                 'dept_var_name': self.dept_var['name'],
                 'indept_var_label': data[self.indept_var['name']]['label'],
                 'dept_var_label': data[self.dept_var['name']]['label'],
                 'indept_var_unit': data[self.indept_var['name']]['unit'],
                 'dept_var_unit': data[self.dept_var['name']]['unit'],
                 'estimate_values':
                    self._find_estimate(input_data_array,
                                               param_dict['param_values'])})
            fit_results.append(result)
        return fit_results

    def get_result(**setpoint_values):
        """
        Args:
            kwargs for each setpoints
                eg 'frequency=1e9, power=-10'
        Returns:
            dict for fit where these conditions are satisfiedxw
        """
        if len(setpoint_values) != len(self.setpoints):
            raise RuntimeError('Must specify a value for each setpoint')
        elif len(self.setpoints) == 0:
            return self.fit_results[0]
        else:
            return next(res for res in self.fit_results if
                        all(res[setpoint] == value for
                            setpoint, value in setpoint_values.items()))

    def _perform_fit(self, input_data_array, output_data_array):

        # make fit params dictionary
        params_dict = {'param_names': [], 'param_labels': {},
                       'param_units': {}, 'param_start_values': {},
                       'param_variance': {}, 'param_values': {}}
        for i, param_name in enumerate(self.fitclass.param_names):
            params_dict['param_names'].append(param_name)
            params_dict['param_labels'][param_name] = self.fitclass.param_labels[i]
            params_dict['param_units'][param_name] = self.fitclass.param_units[i]

        # find start parameters, run curve_fit function to perform fit
        p_guess = self.fitclass.guess(input_data_array, output_data_array)
        popt, pcov = curve_fit(self.fitclass.fun,
                               input_data_array,
                               output_data_array,
                               p0=p_guess)

        # add guess and fit results to dict
        for i, param_name in enumerate(self.fitclass.param_names):
            params_dict['param_start_values'][param_name] = p_guess[i]
            params_dict['param_values'][param_name] = popt[i]
            params_dict['param_variance'][param_name] = pcov[i, i]

        return params_dict

    def _find_estimate(self, input_data_array, params_values_dict):
        return self.fitclass.fun(input_data_array, **params_values_dict)

    def plot(self, rescale_axes: bool=True):

        run_id = self.experiment_info['run_id']

        data_info = load_by_id(run_id)
        experiment_name = data_info.exp_name
        sample_name = data_info.sample_name
        title = f"Run #{run_id} fitted, Experiment {experiment_name} ({sample_name})"

        alldata = get_data_by_id(run_id)
        data = alldata[0]
        # ToDo: fix so that this always accesses the data that matches the dependent and independent variables

        fig, ax = plt.subplots(1, 1)
        axes = [ax]

        if len(self.setpoints) == 0:  # 1D PLOTTING

            parameter_values = self.fit_results[0]['param_values']

            # sort data for plotting
            order = self.indept_var['data'].argsort()
            xpoints = self.indept_var['data'][order]
            ypoints = self.dept_var['data'][order]

            # returns 'point' if all xpoints are identical, otherwise returns 'line'
            plottype = datatype_from_setpoints_1d(xpoints)

            if plottype == 'line':
            # or maybe it should just always be a scatter plot anyway? Thorvald's is a scatter plot with a fit line.
                ax.plot(xpoints, ypoints, marker='.',markersize=5,linestyle='',color='C0')

                x = np.linspace(xpoints.min(), xpoints.max(), len(xpoints) * 10)
                ax.plot(x, self.fitclass.fun(x, **parameter_values), color='C1')

            elif plottype == 'point':
                # ToDo: does this even make sense? Would we ever do a fit of this type for a scatter plot? What even would that be?
                x = xpoints[0]
                ax.scatter(xpoints, ypoints)
                ax.scatter(x, fitclass.fun(x, **parameter_values))
            else:
                raise ValueError('Unknown plottype. Something is way wrong.')

            # axes labels and title
            ax.set_xlabel(f"{self.indept_var['label']} ({self.indept_var['unit']})")
            ax.set_ylabel(f"{self.dept_var['label']} ({self.dept_var['unit']})")

            if rescale_axes:
                data_lst = [self.indept_var, self.dept_var]
                _rescale_ticks_and_units(ax, data_lst)

            ax.set_title(title)

            # fit result box
            p_label_list = [self.fitclass.fun_str]
            for parameter in parameter_values:
                value = parameter_values[parameter]
                unit = self.fit_results[0]['param_units'][parameter]
                p_label_list.append('{} = {:.3g} {}'.format(parameter, value, unit))
            textstr = '\n'.join(p_label_list)

            ax.text(1.05, 0.7, textstr, transform=ax.transAxes, fontsize=14,
                    verticalalignment='top', bbox={'ec':'k','fc':'w'})
            # Todo: scaling for fit result numbers and units

        elif len(self.setpoints) == 1: # 2D PLOTTING

            xdata = self.indept_var
            ydata = self.setpoints
            zdata = self.dept_var

            # Don't understand this fully. Seems to make color scale-bar for 2D plots.
            colorbars = len(axes) * [None]  # ToDo: what does this do?
            new_colorbars: List[matplotlib.colorbar.Colorbar] = []  # ToDo: what does this do?

            raise NotImplementedError

        elif len(self.setpoints) > 1: # Are we even going to do this?
            raise NotImplementedError




