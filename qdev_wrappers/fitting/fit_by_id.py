import qcodes as qc
import numpy as np
import json
from itertools import product
import warnings
from qcodes.dataset.measurements import Measurement
from qcodes.dataset.data_export import get_data_by_id
from fitter import LeastSquaresFitter
from plotting import plot_fit, save_image
from helpers import get_run_info, select_relevant_data
from qdev_wrappers.dataset.doNd import save_image

# TODO: docstrings
# TODO change paramspecs to parameters if metadata is ok


def fit_by_id(data_run_id, fitter,
              dependent_parameter_name: str,
              *independent_parameter_names: str,
              save=True, plot=True,
              rescale_axes=True,
              show_variance=True, **kwargs):

    data_run_info = get_run_info(data_run_id)
    dependent, independent, setpoints = select_relevant_data(
        data_run_id, dependent_parameter_name, independent_parameter_name)
    setpoint_paramnames = [setpoint['name'] for s in setpoints]

    fit_params = []

    # register setpoints
    meas = Measurement()
    setpoint_paramspecs = []
    for setpoint in setpoints:
        setpoint_param = Parameter(name=setpoint['name'],
                                   label=setpoint['label'],
                                   unit=setpoint['unit'])
        meas.register_parameter(setpoint_param)
        setpoint_params.append(setpoint_param)

    # register fit parameters
    for param in fitter.fit_parameters.parameters.values():
        meas.register_parameter(param, setpoints=setpoint_params)
        fit_params.append(param)

    # register success param
    meas.register_parameter(fitter.success, setpoints=setpoint_params)
    fit_params.append(fitter.success)

    # register fit information parameters if LSF
    if isinstance(fitter, LeastSquaresFitter):
        for param in fitter.variance_parameters.parameters.values():
            meas.register_parameter(param, setpoints=setpoint_params)
            fit_params.append(param)
        for param in fitter.initial_values_parameters.parameters.values():
            meas.register_parameter(param, setpoints=setpoint_params)
            fit_params.append(param)

    # set up dataset with metadata
    metadata = {'fitter': fitter.metadata,
                'inferred_from': {'run_id': data_run_info['run_id'],
                                  'exp_id': data_run_info['exp_id'],
                                  'dept_var': dependent_parameter_name,
                                  'indept_vars': independent_parameter_names,
                                  'setpoints': setpoint_paramnames}}
    # run fit for data
    with meas.run() as datasaver:
        json_metadata = json.dumps(metadata)
        datasaver._dataset.add_metadata('fitting_metadata', json_metadata)
        fit_run_id = datasaver.run_id
        if len(setpoints) > 0:
            # find all possible combinations of setpoint values
            setpoint_combinations = product(
                *[set(v['data']) for v in setpoints])
            for setpoint_combination in setpoint_combinations:
                # find indices where where setpoint combination is satisfied
                indices = set(np.argwhere(
                    setpoints[0]['data'] == setpoint_combination[0]).flatten())
                for i in range(1, len(setpoints)):
                    new_indices = np.argwhere(
                        setpoints[i]['data'] == setpoint_combination[i]).flatten()
                    indices = indices.intersection(new_indices)
                indices = list(indices)
                dependent_data = dependent['data'][indices]
                independent_data = [i['data'][indices] for i in independent]
                fitter.fit(dependent_data, *independent_data, **kwargs)
                result = list(zip(setpoint_paramnames, setpoint_combination))
                for fit_param in fit_params:
                    result.append((fit_param.name, fit_param()))
                datasaver.add_result(*resul)
        else:
            fitter.fit(dependent['data'], *[i['data'] for i in independent], **kwargs)
            result = [(fit_param.name, fit_param()) for fit_param in fit_params]
            datasaver.add_result(*result)
    # plot
    if plot:
        fit_data = get_data_by_id(fit_run_id)
        axes, colorbar = plot_fit(
            dependent, independent, setpoints, fit_data, metadata,
            fit_run_id, rescale_axes=rescale_axes,
            show_variance=show_variance)
        data_run_info['run_id'] = fit_run_id
        save_image(axes, **data_run_info)
    else:
        axes, colorbar = [], None

    return plot_fit, axes, colorbar
