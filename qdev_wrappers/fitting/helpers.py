import numpy as np
import json

# TODO: docstrings


def make_json_metadata(dataset, fitter, dependent_parameter_name,
                       *independent_parameter_names):
    exp_metadata = {'run_id': dataset.run_id,
                    'exp_id': dataset.exp_id,
                    'exp_name': dataset.exp_name,
                    'sample_name': dataset.sample_name}
    metadata = {'fitter': fitter.metadata,
                'inferred_from': {'dept_var': dependent_parameter_name,
                                  'indept_vars': independent_parameter_names,
                                  **exp_metadata}}
    return 'fitting_metadata', json.dumps(metadata)


def load_json_metadata(dataset):
    try:
        return json.loads(dataset.metadata['fitting_metadata'])
    except KeyError:
        raise RuntimeError(
            "'fitting_metadata' not found in dataset metadata, are you sure "
            "this is a fitted dataset?")


def organize_exp_data(data, dependent_parameter_name,
                      *independent_parameter_names, **setpoint_values):
    parameters = data.parameters.split(',')
    if not all(v in parameters for v in setpoint_values.keys()):
        raise RuntimeError(f'{list(setpoint_values.keys())} not all found '
                           f'in dataset. Parameters present are {parameters}')

    indices = []
    for setpoint, value in setpoint_values.items():
        d = np.array(data.get_data(setpoint)).flatten()
        nearest_val = value + np.amin(d - value)
        indices.append(set(np.argwhere(d == nearest_val).flatten()))
    if len(indices) > 0:
        u = list(set.intersection(*indices))
    else:
        u = None

    setpoints = {}
    for p in parameters:
        depends_on = data.paramspecs[p].depends_on.split(', ')
        for d in depends_on:
            non_vals = list(setpoint_values.keys()) + \
                [''] + list(independent_parameter_names)
            if d not in non_vals:
                setpoints[d] = None
    dependent = None
    independent = {}
    for name in parameters:
        if name == dependent_parameter_name:
            dependent = {
                'name': name,
                'label': data.paramspecs[name].label,
                'unit': data.paramspecs[name].unit,
                'data': np.array(data.get_data(name)).flatten()[u].flatten()}
        elif name in independent_parameter_names:
            independent[name] = {
                'name': name,
                'label': data.paramspecs[name].label,
                'unit': data.paramspecs[name].unit,
                'data': np.array(data.get_data(name)).flatten()[u].flatten()}
        elif name in setpoints:
            setpoints[name] = {
                'name': name,
                'label': data.paramspecs[name].label,
                'unit': data.paramspecs[name].unit,
                'data': np.array(data.get_data(name)).flatten()[u].flatten()}
    if dependent is None:
        raise RuntimeError(f'{dependent_parameter_name} not found in dataset. '
                           f'Parameters present are {parameters}')
    if len(independent) != len(independent_parameter_names):
        raise RuntimeError(f'{independent_parameter_names} not all found '
                           f'in dataset. Parameters present are {parameters}')
    return dependent, independent, setpoints


def organize_fit_data(data, **setpoint_values):
    """
    Takes a dataset and optionally spcific setpoint values and returns
    dictionaries for the success, fit, variance and setpoints

    Returns:
        success (dict) with keys 'name', 'unit', 'label', data'
    """

    # extract metadata and parameters present
    metadata = load_json_metadata(data)
    parameters = data.parameters.split(',')

    # check fit parameters and setpoint parameters are present
    if 'success' not in parameters:
        raise RuntimeError(
            f"'success' parameter found "
            "in dataset. Parameters present are {parameters}")
    if not all(v in parameters for v in metadata['fitter']['fit_parameters']):
        raise RuntimeError(
            f"{metadata['fitter']['fit_parameters']} not all found "
            "in dataset. Parameters present are {parameters}")
    if not all(v in parameters for v in setpoint_values.keys()):
        raise RuntimeError(
            f"{list(setpoint_values.keys())} not all found "
            "in dataset. Parameters present are {parameters}")

    # find indices for specified setpoint_values
    indices = []
    point_values = []
    for setpoint, value in setpoint_values.items():
        d = np.array(data.get_data(setpoint)).flatten()
        nearest_val = value + np.amin(d - value)
        indices.append(set(np.argwhere(d == nearest_val).flatten()))
        point_values.append(nearest_val)
    if len(indices) > 0:
        u = list(set.intersection(*indices))
    else:
        u = None

    # populate dictionaries
    setpoints = {}
    for p in parameters:
        depends_on = data.paramspecs[p].depends_on.split(', ')
        for d in depends_on:
            non_vals = list(setpoint_values.keys()) + ['']
            if d not in non_vals:
                setpoints[d] = None
    fit = {}
    variance = {}
    initial_values = {}
    for name in parameters:
        if name == 'success':
            success = {
                'name': name,
                'label': data.paramspecs[name].label,
                'unit': data.paramspecs[name].unit,
                'data': np.array(data.get_data(name)).flatten()[u].flatten()}
        elif name in metadata['fitter']['fit_parameters']:
            fit[name] = {
                'name': name,
                'label': data.paramspecs[name].label,
                'unit': data.paramspecs[name].unit,
                'data': np.array(data.get_data(name)).flatten()[u].flatten()}
        elif name in metadata['fitter'].get('variance_parameters', []):
            variance[name] = {
                'name': name,
                'label': data.paramspecs[name].label,
                'unit': data.paramspecs[name].unit,
                'data': np.array(data.get_data(name)).flatten()[u].flatten()}
        elif name in metadata['fitter'].get('initial_value_parameters', []):
            initial_values[name] = {
                'name': name,
                'label': data.paramspecs[name].label,
                'unit': data.paramspecs[name].unit,
                'data': np.array(data.get_data(name)).flatten()[u].flatten()}
        elif name in setpoints:
            setpoints[name] = {
                'name': name,
                'label': data.paramspecs[name].label,
                'unit': data.paramspecs[name].unit,
                'data': np.array(data.get_data(name)).flatten()[u].flatten()}

    return success, fit, variance, initial_values, setpoints, point_values
