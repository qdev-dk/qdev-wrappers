import numpy as np
import json
from itertools import product
from qcodes.dataset.measurements import Measurement
from qcodes.dataset.data_export import load_by_id
from qcodes.instrument.parameter import Parameter
from qdev_wrappers.fitting.fitter import LeastSquaresFitter
from qdev_wrappers.fitting.plotting import plot_fit_by_id
from qdev_wrappers.fitting.helpers import organize_exp_data
from qdev_wrappers.dataset.doNd import save_image

# TODO: docstrings


def fit_by_id(data_run_id, fitter,
              dependent_parameter_name: str,
              *independent_parameter_names: str,
              save=True, plot=True,
              rescale_axes=True,
              show_variance=True,
              show_initial_values=True,
              **kwargs):
    exp_data = load_by_id(data_run_id)
    dependent, independent, setpoints = organize_exp_data(
        exp_data, dependent_parameter_name, *independent_parameter_names)
    setpoint_paramnames = list(setpoints.keys())
    fit_save_params = []

    # register setpoints
    meas = Measurement()
    setpoint_params = []
    for setpoint in setpoints.values():
        setpoint_param = Parameter(name=setpoint['name'],
                                   label=setpoint['label'],
                                   unit=setpoint['unit'])
        meas.register_parameter(setpoint_param)
        setpoint_params.append(setpoint_param)

    # register fit parameters
    for param in fitter.fit_parameters.parameters.values():
        meas.register_parameter(param, setpoints=setpoint_params or None)
        fit_save_params.append(param)

    # register success param
    meas.register_parameter(fitter.success, setpoints=setpoint_params or None)
    fit_save_params.append(fitter.success)

    # register fit information parameters if LSF
    if isinstance(fitter, LeastSquaresFitter):
        for param in fitter.variance_parameters.parameters.values():
            meas.register_parameter(param, setpoints=setpoint_params or None)
            fit_save_params.append(param)
        for param in fitter.initial_value_parameters.parameters.values():
            meas.register_parameter(param, setpoints=setpoint_params or None)
            fit_save_params.append(param)

    # set up dataset with metadata
    exp_metadata = {'run_id': exp_data.run_id,
                    'exp_id': exp_data.exp_id,
                    'exp_name': exp_data.exp_name,
                    'sample_name': exp_data.sample_name}
    metadata = {'fitter': fitter.metadata,
                'inferred_from': {'dept_var': dependent_parameter_name,
                                  'indept_vars': independent_parameter_names,
                                  **exp_metadata}}
    # run fit for data
    with meas.run() as datasaver:
        json_metadata = json.dumps(metadata)
        datasaver._dataset.add_metadata('fitting_metadata', json_metadata)
        fit_run_id = datasaver.run_id
        if len(setpoints) > 0:
            # find all possible combinations of setpoint values
            setpoint_combinations = product(
                *[set(v['data']) for v in setpoints.values()])
            for setpoint_combination in setpoint_combinations:
                # find indices where where setpoint combination is satisfied
                indices = []
                for i, setpoint in enumerate(setpoints.values()):
                    indices.append(
                        set(np.argwhere(setpoint['data'] ==
                                        setpoint_combination[i]).flatten()))
                u = None
                if len(indices) > 0:
                    u = list(set.intersection(*indices))
                dependent_data = dependent['data'][u].flatten()
                independent_data = [d['data'][u].flatten()
                                    for d in independent.values()]
                fitter.fit(dependent_data, *independent_data, **kwargs)
                result = list(zip(setpoint_paramnames, setpoint_combination))
                for fit_param in fit_save_params:
                    result.append((fit_param.name, fit_param()))
                datasaver.add_result(*result)
        else:
            dependent_data = dependent['data']
            independent_data = [d['data'] for d in independent.values()]
            fitter.fit(dependent_data, *independent_data, **kwargs)
            result = [(p.name, p()) for p in fit_save_params]
            datasaver.add_result(*result)
    # plot
    if plot:
        axes, colorbar = plot_fit_by_id(fit_run_id, rescale_axes=rescale_axes,
                                        show_variance=show_variance, show_initial_values=show_initial_values)
        save_image(axes, name_extension='fit', **exp_metadata)
    else:
        axes, colorbar = [], None

    return fit_run_id, axes, colorbar
