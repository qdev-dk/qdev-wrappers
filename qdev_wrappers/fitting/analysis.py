import numpy as np
import os
import matplotlib.pyplot as plt
from qcodes import config
from qcodes.dataset.data_export import get_data_by_id, load_by_id
from qcodes.dataset.plotting import _rescale_ticks_and_units, plot_on_a_plain_grid
from qcodes import ParamSpec, new_experiment, new_data_set
from qcodes.dataset.database import initialise_database


class Analysis:

    def __init__(self, run_id, dept_var: str, model, **function_variables):

        self.experiment_info = {'exp_name': load_by_id(run_id).exp_name,
                                'exp_id': load_by_id(run_id).exp_id,
                                'run_id': run_id,
                                'sample_name': load_by_id(run_id).sample_name}

        # retrieve data based on run id and dependent variable, organize
        all_data = self._select_relevant_data(run_id, dept_var, **function_variables)
        self.function_vars = all_data[0]
        self.dept_var = all_data[1]
        self.setpoints = all_data[2]
        self.all_data = all_data[3]
        self.model = model

        self.metadata = {}
        self.fit_results = {}

    def _select_relevant_data(self, run_id, dept_var, **function_variables):
        """
        This function goes through the all the data retrieved by
        get_data_by_id(run_id), and returns the data that contains
        the dependent variable, or throws an error if no matching
        data is found.

        Calling get_data_by_id(run_id) returns data as a list of lists
        of dictionaries:

            [
              # each element in this list refers
              # to one dependent (aka measured) parameter
                [
                  # each element in this list is a dictionary referring
                  # to one independent (aka setpoint) parameter
                  # that the dependent parameter depends on;
                  # a dictionary with the data and metadata of the dependent
                  # parameter is in the *last* element in this list

                ]
            ]
        """
        # Find the data corresponding to the dependent variable
        index = None
        for idx, measured_data in enumerate(get_data_by_id(run_id)):
            if measured_data[-1]['name'] == dept_var:
                index = idx
        if index is None:
            raise RuntimeError(f"No data found with dependent variable {dept_var}. "
                               f"Dataset contains variables: {load_by_id(run_id).parameters}")
        all_data = get_data_by_id(run_id)[index]

        # organize into dependent, independent and setpoints
        if not function_variables:
            raise RuntimeError("Please specify at least one variable! "
                               f"Dataset contains variables: {load_by_id(run_id).parameters}")
        for var, name in function_variables.items():
            if name not in load_by_id(run_id).parameters.split(','):
                raise RuntimeError(f"The variable {name} was not found in the data! "
                                   f"Dataset contains variables: {load_by_id(run_id).parameters}")
            function_variables.update({var: data for data in all_data if data['name'] == name})

        dependent_variable = [data for data in all_data if data['name'] == dept_var][0]
        setpoints = {data['name']: data for data in all_data if
                     data['name'] != dept_var and
                     data not in function_variables.values()}

        return [function_variables, dependent_variable, setpoints, all_data]

    def get_result(self, **setpoint_values):
        """
        Keyword arguments:
            setpoint values, i.e. frequency=1e9, power=-10
        Returns:
            dict for fit where these conditions are satisfied
        """

        if len(self.setpoints) == 0:
            return self.fit_results[0]
        elif setpoint_values is None or len(setpoint_values) != len(self.setpoints):
                raise RuntimeError('Please specify a value for each setpoint')
        else:
            return next(res for res in self.fit_results if
                        all(res['setpoints'][setpoint_name] == value for
                            setpoint_name, value in setpoint_values.items()))

    def _plot_1d(self, xdata, ydata, parameter_values, param_variance, rescale_axes=True):

        # plot data, and fit if successful
        plt.figure(figsize=(10, 4))
        ax = plt.subplot(111)
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.7, box.height])
        
        ax.plot(xdata['data'], ydata['data'], marker='.', markersize=5, linestyle='', color='C0')
        if parameter_values is None:
            pass
        else:
            x = np.linspace(xdata['data'].min(), xdata['data'].max(), len(xdata['data']) * 10)
            param_args = [value for value in parameter_values.values()]
            ax.plot(x, self.model.evaluate(x, *param_args), color='C1')

        # set axes labels and title
        ax.set_xlabel(f"{xdata['label']} ({xdata['unit']})")
        ax.set_ylabel(f"{ydata['label']} ({ydata['unit']})")

        if rescale_axes:
            data_lst = [xdata, ydata]
            _rescale_ticks_and_units(ax, data_lst)

        # add fit result summary box
        if parameter_values is None:
            textstr = '{} \n Unsuccessful fit'.format(self.model.func_str)
        else:
            p_label_list = [self.model.func_str]
            for parameter in parameter_values:
                value = parameter_values[parameter]
                unit = self.metadata['parameters'][parameter]['unit']
                if param_variance is not None:
                    standard_dev = np.sqrt(param_variance[parameter])
                    p_label_list.append(r'{} = {:.3g} ± {:.3g} {}'.format(parameter, value, standard_dev, unit))
                else:
                    p_label_list.append(r'{} = {:.3g} {}'.format(parameter, value, unit))
            textstr = '\n'.join(p_label_list)

        ax.text(1.05, 0.7, textstr, transform=ax.transAxes, fontsize=14,
                verticalalignment='top', bbox={'ec': 'k', 'fc': 'w'})

        return ax

    def plot(self, rescale_axes: bool = True, show_variance=False, save_plot=False):

        if len(self.function_vars) > 1:
            raise NotImplementedError("Sorry, you have specified multiple function variables, and plotting only "
                                      "works for 1D functions right now")
        else:
            indept_var = [data_dict for data_dict in self.function_vars.values()][0]
            axes = []
            colorbar = None
            title = "Run #{} fitted, Experiment {} ({})".format(self.experiment_info['run_id'],
                                                                self.experiment_info['exp_id'],
                                                                self.experiment_info['sample_name'])
        if len(self.setpoints) == 0:  # 1D PLOTTING

            parameter_values = self.fit_results[0]['param_values']
            if show_variance:
                param_variance = self.fit_results[0]['variance']
            else:
                param_variance = None
            ax = self._plot_1d(indept_var, self.dept_var, parameter_values, param_variance, rescale_axes)
            ax.set_title(title)
            axes.append(ax)

        elif len(self.setpoints) == 1:  # 2D PLOTTING: 2D heat-map + params plots

            # get setpoint info for plot labels
            setpoint_name = [key for key in self.setpoints][0]
            setpoint_unit = self.setpoints[setpoint_name]['unit']
            setpoint_label = self.setpoints[setpoint_name]['label']

            # organize all data for plotting
            x, y, z = [], [], []
            params = {'param_setpoints': []}
            for param_name in [name for name in self.metadata['parameters'].keys()]:
                params[param_name] = []
                if show_variance:
                    params[param_name + '_variance'] = []

            for result in self.fit_results.copy():

                setpoint_value = result['setpoints'][setpoint_name]
                data_length = len(indept_var['data'])
                x.append(list(indept_var['data']))
                y.append([setpoint_value] * data_length)
                if result['param_values'] is not None:
                    param_args = [value for value in result['param_values'].values()]
                    z.append(list(self.model.evaluate(indept_var['data'], *param_args)))
                    params['param_setpoints'].append(setpoint_value)
                    for parameter in result['param_values']:
                        params[parameter].append(result['param_values'][parameter])
                        if show_variance:
                            params[parameter + '_variance'].append(result['variance'][parameter])
                else:
                    z.append([None]*len(indept_var['data']))

            xpoints = np.array(x).flatten()
            ypoints = np.array(y).flatten()
            zpoints = np.array(z).flatten()
            for item in params:
                params[item] = np.array(params[item])

            # Make 2D heatmap plot
            fig, ax = plt.subplots(1, 1)
            ax, colorbar = plot_on_a_plain_grid(xpoints, ypoints, zpoints, ax, colorbar)

            ax.set_xlabel(f"{indept_var['label']} ({indept_var['unit']})")
            ax.set_ylabel(f"{setpoint_label} ({setpoint_unit})")
            ax.set_title(title)
            colorbar.set_label(f"{self.dept_var['label']} ({self.dept_var['unit']})")

            if rescale_axes:
                data_lst = [indept_var, self.setpoints[setpoint_name], self.dept_var]
                _rescale_ticks_and_units(ax, data_lst, colorbar)

            axes.append(ax)

            # Make parameter vs setpoint plots
            order = params['param_setpoints'].argsort()
            xdata = self.setpoints[setpoint_name]
            xpoints = params['param_setpoints'][order]

            for param in self.model.parameters.keys():
                fig, ax = plt.subplots(1, 1)
                ydata = self.model.parameters[param].copy()
                ydata['data'] = params[param][order]
                if show_variance:
                    param_variance = params[param + '_variance'][order]
                    param_standard_dev = np.array([np.sqrt(variance) for variance in param_variance])
                    ax.errorbar(xpoints, ydata['data'], param_standard_dev, None, 'g.-')
                else:
                    ax.plot(xpoints, ydata['data'], 'g.-')
                ax.set_title(title)
                ax.set_xlabel(f"{xdata['label']} ({xdata['unit']})")
                ax.set_ylabel(f"{ydata['label']} ({ydata['unit']})")
                if rescale_axes:
                    data_lst = [xdata, ydata]
                    _rescale_ticks_and_units(ax, data_lst)
                axes.append(ax)

        elif len(self.setpoints) > 1:
                raise NotImplementedError(f'Sorry, the fit has {len(self.setpoints)} setpoints ({self.setpoints}), '
                                          f'and this plotting function can currently deal with 1. Try saving the fit '
                                          f'and plotting from the saved fit result.')
        if save_plot is True:
            self._save_image(axes)
        return axes, colorbar

    def save(self, save_plots=False):
        # Todo: save dill (model only? model and fitter?)

        # Save plots to folder
        if save_plots:
            axes, colorbars = self.plot()
            self._save_image(axes)

        # Save fit data to database
        paramspecs = []

        setpoint_paramspecs = {}
        for setpoint, setpoint_dict in self.setpoints.items():
            paramspec = ParamSpec(setpoint, 'numeric',
                                  label=setpoint_dict['label'],
                                  unit=setpoint_dict['unit'])
            setpoint_paramspecs[setpoint] = paramspec
            paramspecs.append(paramspec)

        for param, param_dict in self.model.parameters.items():
            paramspec = ParamSpec(
                param, 'numeric',
                label=param_dict['label'],
                unit=param_dict['unit'],
                depends_on=list(
                    setpoint_paramspecs.values()) or None)
            paramspecs.append(paramspec)

            # if the fit returned other info than the parameter values, fx. variance, create paramspecs for them
            for param_info_name, metadata in self.model.data_saving_info.items():
                if 'unit' in metadata.keys():
                    unit = metadata['unit']
                else:
                    unit = param_dict['unit']
                paramspec = ParamSpec(
                    "_".join([param, param_info_name]),
                    metadata['type'],
                    label=param_dict['label'] + metadata['label'],
                    unit=unit)
                paramspecs.append(paramspec)
            # Todo: What if, in some model, there is extra fit data that isn't associated with a particular parameter?
            # Currently it won't be saved, but maybe there should be an option to add it to metadata?

        if self.experiment_info['exp_id'] is None:
            initialise_database()
            exp = new_experiment(self.experiment_info['sample_name'],
                                 sample_name=self.experiment_info['sample_name'])
            self.experiment_info['exp_id'] = exp.exp_id
        all_metadata = {'model': self.metadata,
                        'inferred_from': {'run_id': self.experiment_info['run_id'],
                                          'exp_id': self.experiment_info['exp_id'],
                                          'dept_var': self.dept_var['name']}}
        dataset = new_data_set('analysis',
                               specs=paramspecs,
                               metadata=all_metadata)

        results = []
        for r in self.fit_results:
            if r['param_values'] is not None:
                result = {}
                for param_name in self.model.parameters:
                    result.update({param_name: r['param_values'][param_name]})
                    # add any additional info about parameter, fx. variance
                    for param_info_name in self.model.data_saving_info.keys():
                        result.update({"_".join([param_name, param_info_name]): r[param_info_name][param_name]})
                if 'setpoints' in r.keys():
                    for setpoint_name in r['setpoints'].keys():
                        result[setpoint_name] = r['setpoints'][setpoint_name]
                results.append(result)
        dataset.add_results(results)
        dataset.mark_complete()
        print(f"\n Analysis saved with run id {dataset.run_id}")
        return dataset

    def _save_image(self, axes):
        """
        Save the plots as pdf and png
        """
        plt.ioff()

        mainfolder = config.user.mainfolder
        experiment_name = self.experiment_info['exp_name']
        sample_name = self.experiment_info['sample_name']
        meas_run_id = self.experiment_info['run_id']

        storage_dir = os.path.join(mainfolder, experiment_name, sample_name)
        os.makedirs(storage_dir, exist_ok=True)

        png_dir = os.path.join(storage_dir, 'png')
        pdf_dir = os.path.join(storage_dir, 'pdf')

        os.makedirs(png_dir, exist_ok=True)
        os.makedirs(pdf_dir, exist_ok=True)

        save_pdf = True
        save_png = True

        for i, ax in enumerate(axes):
            if save_pdf:
                start_name = f'{meas_run_id}_fitted_{i}.pdf'
                file_name = self._make_file_name(pdf_dir, start_name)
                full_path = os.path.join(pdf_dir, file_name)
                ax.figure.savefig(full_path, dpi=500)
            if save_png:
                start_name = f'{meas_run_id}_fitted_{i}.png'
                file_name = self._make_file_name(png_dir, start_name)
                full_path = os.path.join(png_dir, file_name)
                ax.figure.savefig(full_path, dpi=500)
        plt.ion()
        return axes

    def _make_file_name(self, directory, initial_name):
        full_path = os.path.join(directory, initial_name)
        name = initial_name.split('.')[0]
        file_format = initial_name.split('.')[1]
        new_name = name
        i = 1
        while os.path.isfile(full_path):
            new_name = f'{name}_{i}'
            file_path = '.'.join([new_name, file_format])
            full_path = os.path.join(directory, file_path)
            i += 1
        final_name = '.'.join([new_name, file_format])
        return final_name
