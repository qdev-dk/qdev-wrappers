from qcodes.dataset.data_export import get_data_by_id, load_by_id
from plotting import plot_fit
from fit_by_id import select_relevant_data
import json
import numpy as np
from qdev_wrappers.dataset.doNd import save_image


def plot_fit_by_id(fit_run_id, rescale_axes=True,
                   show_variance=True, **setpoint_values):
    try:
        metadata = json.loads(load_by_id(
            fit_run_id).metadata['fitting_metadata'])
    except KeyError:
        raise RuntimeError(
            "'fitting_metadata' not found in dataset metadata, are you sure "
            "this is a fitted dataset?")
    data_run_id = metadata['inferred_from']['run_id']
    dependent_parameter_name = metadata['inferred_from']['dept_var']
    independent_parameter_name = metadata['inferred_from']['indept_var']
    dependent, independent, setpoints = select_relevant_data(
        data_run_id, dependent_parameter_name, independent_parameter_name,
        **setpoint_values)
    fit_data = get_data_by_id(fit_run_id)
    indices = []
    for f in fit_data:
        if f['name'] in setpoint_values:
            indices.append(set(np.argwhere(f['data'] == setpoint_values[f['name']]).flatten()))
    if len(indices) > 0:
        u = set.intersection(*indices)
        for f in fit_data:
            f['data'] = f['data'][list(u)]
    axes, colorbar = plot_fit(
        dependent, independent, setpoints, fit_data, metadata,
        fit_run_id, rescale_axes=rescale_axes,
        show_variance=show_variance)
