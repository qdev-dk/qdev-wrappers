import numpy as np
import json
from itertools import product
from qcodes.dataset.measurements import Measurement
from qcodes.dataset.data_export import load_by_id
from qcodes.instrument.parameter import Parameter
from qdev_wrappers.fitting.fitters import LeastSquaresFitter
from qdev_wrappers.fitting.plotting import plot_fit_by_id
from qdev_wrappers.fitting.helpers import organize_exp_data, make_json_metadata

# TODO: docstrings


def fit_by_id(data_run_id, fitter,
              dependent_parameter_name: str,
              *independent_parameter_names: str,
              plot=True,
              save_plots=True,
              show_variance=True,
              show_initial_values=True,
              **kwargs):
    exp_data = load_by_id(data_run_id)
    dependent, independent, setpoints = organize_exp_data(
        exp_data, dependent_parameter_name, *independent_parameter_names)
    setpoint_paramnames = list(setpoints.keys())

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
    for param in fitter.all_parameters:
        meas.register_parameter(param,
                                setpoints=setpoint_params or None)

    # set up dataset metadata
    metadata = make_json_metadata(
        exp_data, fitter, dependent_parameter_name,
        *independent_parameter_names)

    # run fit for data
    with meas.run() as datasaver:
        datasaver._dataset.add_metadata(*metadata)
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
                for fit_param in fitter.all_parameters:
                    result.append((fit_param.name, fit_param()))
                datasaver.add_result(*result)
        else:
            dependent_data = dependent['data']
            independent_data = [d['data'] for d in independent.values()]
            fitter.fit(dependent_data, *independent_data, **kwargs)
            result = [(p.name, p()) for p in fitter.all_parameters]
            datasaver.add_result(*result)
    # plot
    if plot:
        axes, colorbar = plot_fit_by_id(fit_run_id,
                                        show_variance=show_variance,
                                        show_initial_values=show_initial_values,
                                        save_plots=save_plots)
    else:
        axes, colorbar = [], None

    return fit_run_id, axes, colorbar
