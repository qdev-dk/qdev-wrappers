import os
from os.path import sep
import re
from qdev_wrappers.file_setup import CURRENT_EXPERIMENT


def get_qubit_count():
    if not getattr(CURRENT_EXPERIMENT, "init", True):
        raise RuntimeError("Experiment not initalized")
    try:
        return CURRENT_EXPERIMENT["qubit_count"]
    except KeyError:
        return None


def get_current_qubit():
    if not getattr(CURRENT_EXPERIMENT, "init", True):
        raise RuntimeError("Experiment not initalized")
    try:
        return CURRENT_EXPERIMENT['current_qubit']
    except KeyError:
        return None


def set_current_qubit(val: int):
    if not getattr(CURRENT_EXPERIMENT, "init", True):
        raise RuntimeError("Experiment not initalized")
    qubit_count = get_qubit_count()
    if qubit_count is None:
        raise RuntimeError('Cannot set current qubit if the qubit count has '
                           'not been set')
    if val >= qubit_count:
        raise ValueError('Expects qubit index less than qubit count: {}. '
                         'Received {}'.format(qubit_count, val))
    CURRENT_EXPERIMENT['current_qubit'] = val


def get_sample_name():
    if not getattr(CURRENT_EXPERIMENT, "init", True):
        raise RuntimeError("Experiment not initalized")
    return CURRENT_EXPERIMENT["sample_name"]


def get_data_location():
    if not getattr(CURRENT_EXPERIMENT, "init", True):
        raise RuntimeError("Experiment not initalized")
    return CURRENT_EXPERIMENT["exp_folder"]


def get_subfolder_location(subfolder_name: str):
    if not getattr(CURRENT_EXPERIMENT, "init", True):
        raise RuntimeError("Experiment not initalized")
    return sep.join([CURRENT_EXPERIMENT["mainfolder"],
                     CURRENT_EXPERIMENT["sample_name"],
                     CURRENT_EXPERIMENT["{}_subfolder".format(subfolder_name)],
                     ""])


def get_logfile():
    if not getattr(CURRENT_EXPERIMENT, "init", True):
        raise RuntimeError("Experiment not initalized")
    if not getattr(CURRENT_EXPERIMENT, "logging_enabled"):
        raise RuntimeError("Logging not enabled")
    return CURRENT_EXPERIMENT['logfile']


def get_analysis_location():
    return get_subfolder_location('analysis')


def get_pulse_location():
    return get_subfolder_location('waveforms')


def get_local_scripts_location():
    return get_subfolder_location('local_scripts')


def get_general_config_file(cfg_name):
    script_folder = CURRENT_EXPERIMENT['scriptfolder']
    return sep.join([script_folder, "{}.config".format(cfg_name)])


def get_local_config_file(cfg_name):
    script_folder = get_subfolder_location('local_scripts')
    return "{}{}.config".format(script_folder, cfg_name)


def get_config_file(cfg_name):
    if not getattr(CURRENT_EXPERIMENT, "init", True):
        raise RuntimeError("Experiment not initalized")
    try:
        cfg_type = CURRENT_EXPERIMENT["{}_config".format(cfg_name)]
    except KeyError:
        raise KeyError("{}_config not found in CURRENT_EXPERIMENT, "
                       "check that _set_up_config_file has been run in the"
                       "init function".format(cfg_name))
    if cfg_type is 'general':
        return get_general_config_file(cfg_name)
    elif cfg_type is 'local':
        return get_local_config_file(cfg_name)
    else:
        raise RuntimeError('Unexpected cfg_type: expected "local" or "general"'
                           ', got "{}"'.format(cfg_type))


def get_latest_counter(path=None):
    if path is None:
        path = get_data_location()
    try:
        file_names = [re.sub("[^0-9]", "", f) for f in os.listdir(path)]
    except OSError as e:
        raise OSError('Error looking for numbered files in {}:'
                      ''.format(path, e))
    file_ints = [int(f) for f in file_names if f]
    if not file_ints:
        raise OSError('No numbered files in ' + path)
    return max(file_ints)


def get_title(counter):
    if counter is None:
        return get_sample_name()
    else:
        str_counter = '{0:03d}'.format(counter)
        return "{counter}_{sample_name}".format(
            sample_name=get_sample_name(),
            counter=str_counter)
