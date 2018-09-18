from qcodes import ParamSpec, new_data_set, new_experiment
from qdev_wrappers.fitting.fitter import Fitter
from qcodes.dataset.database import initialise_database
from qcodes.dataset.data_set import load_by_id


def save_fit_result(fitter: Fitter):
    paramspecs = []
    setpoint_paramspecs = {}
    for setpoint, setpoint_dict in fitter.setpoints.items():
        paramspec = ParamSpec(setpoint, 'numeric',
                              label=setpoint_dict['label'],
                              unit=setpoint_dict['unit'])
        setpoint_paramspecs[setpoint] = paramspec
        paramspecs.append(paramspec)
    indept_var_paramspec = ParamSpec(
        fitter.indept_var['name'],
        'numeric',
        label=fitter.indept_var['label'],
        unit=fitter.indept_var['unit'],
        depends_on=list(setpoint_paramspecs.values()) or None)
    paramspecs.append(indept_var_paramspec)
    dept_var_paramspec = ParamSpec(
        fitter.dept_var['name'],
        'numeric',
        label=fitter.dept_var['label'],
        unit=fitter.dept_var['unit'],
        depends_on=[indept_var_paramspec]+list(setpoint_paramspecs.values()))
    paramspecs.append(dept_var_paramspec)
    for param, param_dict in fitter.fit_parameters.items():
        paramspec = ParamSpec(
            param, 'numeric',
            label=param_dict['label'],
            unit=param_dict['unit'],
            depends_on=list(setpoint_paramspecs.values()) or None)  # TODO: should also have inferred from, depends on?
        paramspec_initial_val = ParamSpec(
            param + '_initial_val', 'numeric',
            label=param_dict['label'] + ' Initial Value',
            unit=param_dict['unit'])
        paramspec_variance = ParamSpec(
            param + '_variance', 'numeric',
            label=param_dict['label'] + ' Variance')  # TODO: should also have inferred from, depends on?
        paramspecs.extend(
            [paramspec, paramspec_initial_val, paramspec_variance])
    estimate_paramspec = ParamSpec(
            fitter.dept_var['name'] + '_estimate',
            'numeric',
            label = fitter.dept_var['label'] + ' Fit Estimate',
            unit = fitter.dept_var['unit'],
            depends_on=[indept_var_paramspec]+list(setpoint_paramspecs.values()))
    paramspecs.append(estimate_paramspec)
    if fitter.experiment_info['exp_id'] is None:
        initialise_database()
        exp = new_experiment(fitter.experiment_info['sample_name'],
                             sample_name=fitter.experiment_info['sample_name'])
        fitter.experiment_info['exp_id'] = exp.exp_id
    metadata = {'estimator': fitter.estimator,
                'dept_var': fitter.dept_var['name'],
                'indept_var': fitter.indept_var['name'],
                'inferred_from': fitter.experiment_info['run_id']}
    dataset = new_data_set('analysis',
#                           exp_id=fitter.experiment_info['exp_id'],
                           specs=paramspecs)
#                           metadata=metadata)
    results = []
    for r in fitter.fit_results:
        result = {}
        for setpoint_name in r['setpoint_names']:
            result[setpoint_name] = r['setpoint_values'][setpoint_name]
        for param_name in r['param_names']:
            if r['param_values'] is not None:
                result.update(
                    {param_name: r['param_values'][param_name],
                    param_name + '_initial_val': r['param_start_values'][param_name],
                    param_name + '_variance': r['param_variance'][param_name]})
        for j in range(len(r['indept_var_values'])):
            result = result.copy()
            result.update(
                {r['indept_var_name']: r['indept_var_values'][j],
                 r['dept_var_name']: r['dept_var_values'][j],
                 r['dept_var_name'] + '_estimate': r['estimate_values'][j]})
            results.append(result)
    dataset.add_results(results)
    dataset.mark_complete()
    return dataset
