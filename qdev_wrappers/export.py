import numpy as np
from qcodes.dataset.data_set import load_by_id
from qcodes.dataset.experiment_container import (load_last_experiment,
                                                 load_experiment)
from qcodes.config.config import Config
import os


def get_export_path(run_id):
    '''Get the full path to save the exported data at.'''
    extension = 'txt'
    db_path = Config()['core']['db_location']
    db_folder = os.path.dirname(db_path)
    export_folder_name = 'export/OneDrive'
    export_folder = os.path.join(db_folder, export_folder_name)
    os.makedirs(export_folder, exist_ok=True)
    filename = '{}.{}'.format(run_id, extension)
    plot_path = os.path.join(export_folder, filename)
    return plot_path


def export_by_id(run_id):
    '''Export CSV files with raw data of a measurement run.'''
    dataset = load_by_id(run_id)
    # experiment = load_experiment(dataset.exp_id)
    data = []
    headers = []
    for parameter_name, specs in dataset.paramspecs.items():
        parameter_data = np.ravel(dataset.get_data(parameter_name))
        data.append(parameter_data)
        parameter_header = '{} ({})'.format(specs.label, specs.unit)
        headers.append(parameter_header)
    data = np.vstack(data).T
    header = ', '.join(headers)
    filename = get_export_path(run_id)
    np.savetxt(filename, data)
