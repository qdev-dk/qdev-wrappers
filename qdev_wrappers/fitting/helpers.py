from qcodes.dataset.data_export import get_data_by_id, load_by_id


def get_run_info(run_id):
    exp_data = load_by_id(run_id)
    return {'exp_name': exp_data.exp_name,
            'exp_id': exp_data.exp_id,
            'run_id': exp_data.run_id,
            'sample_name': exp_data.sample_name}


def select_relevant_data(run_id, dependent_parameter_name,
                         *independent_parameter_names, **setpoint_values):
    """
    This function goes through the all the data retrieved by
    get_data_by_id(run_id), and returns the data that contains
    the dependent variable, or throws an error if no matching
    data is found.

    Calling get_data_by_id(run_id) returns data as a list of lists
    of dictionaries:
        [one element per dependent parameter:
            [one dictionary per independent parameter
             plus one with the the dependent parameter
            ]]

    Returns:
        independent_data: list
        dependent_data: dict
        setpoint_data: list

    """
    # Find the data corresponding to the dependent variable
    index = None
    data = get_data_by_id(run_id)
    for idx, measured_data in enumerate(data):
        if measured_data[-1]['name'] == dependent_parameter_name:
            index = idx
            dependent = measured_data[-1]
    if index is None:
        raise RuntimeError(
            f"No data found with dependent variable {dependent_parameter_name}. "
             "Dataset contains variables: {load_by_id(run_id).parameters}")
    measurement_data = data[index]

    # sort into independent, dependent and setpoints
    independent = []
    setpoints = []
    for d in measurement_data:
        if d['name'] in independent_parameter_names:
            independent.append(d)
        elif name != dependent_parameter_name:
            setpoints.append(d)
    if len(independent) == 0:
        raise RuntimeError(
            f"No data with independent {independent_parameter_name}. "
            "Dataset contains variables: {load_by_id(run_id).parameters}")

    # filter data with required setpoint values
    indices = []
    for s in setpoints:
        if s['name'] in setpoint_values:
            indices.append(set(np.argwhere(s['data'] == setpoint_values[s['name']]).flatten()))
    if len(indices) > 0:
        u = set.intersection(*indices)
        dependent['data'] = dependent['data'][list(u)]
        independent['data'] = independent['data'][list(u)]
        for s in setpoints:
            s['data'] = s['data'][list(u)]

    return dependent, independent, setpoints
