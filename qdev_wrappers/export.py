import numpy as np
from qcodes.dataset.data_set import load_by_id
from qcodes.dataset.experiment_container import load_experiment
from qcodes.config.config import Config
import os


def get_export_path(run_id, exp_id):
    '''Get the full path to save the exported data at.'''
    extension = 'txt'
    db_path = Config()['core']['db_location']
    experiment = load_experiment(exp_id)
    db_folder = os.path.dirname(db_path)
    sample_folder_name = '{}_{}'.format(experiment.sample_name, experiment.name)
    sample_folder = os.path.join(db_folder, sample_folder_name)
    os.makedirs(sample_folder, exist_ok=True)
    filename = '{}.{}'.format(run_id, extension)
    plot_path = os.path.join(sample_folder, filename)
    return plot_path

def export_by_id(run_id):
    '''Export CSV files with raw data of a measurement run.'''
    dataset = load_by_id(run_id)
    data = []
    headers = []
    for parameter_name, specs in dataset.paramspecs.items():
        parameter_data = np.ravel(dataset.get_data(parameter_name))
        data.append(parameter_data)
        parameter_header = '{} ({})'.format(specs.label, specs.unit)
        headers.append(parameter_header)
    data = np.vstack(data).T
    header = ' '.join(headers)
    filename = get_export_path(run_id, dataset.exp_id)
    np.savetxt(filename, data, header=header)
