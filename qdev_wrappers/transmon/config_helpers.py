import pprint
from qdev_wrappers.file_setup import CURRENT_EXPERIMENT
from qdev_wrappers.configreader import Config
import os
import pickle
# import copy
# from os.path import sep
import logging
# import numpy as np
from shutil import copyfile
from . import get_qubit_count, get_config_file, get_current_qubit, \
    get_local_config_file, get_local_scripts_location

# TODO: docstrings

################################
# Calibration File
################################

log = logging.getLogger(__name__)


def make_local_config_file(cfg_name: str, source=None):
    if source is None:
        cfg_file = get_config_file(cfg_name)
        try:
            cfg_type = CURRENT_EXPERIMENT["{}_config".format(cfg_name)]
        except KeyError:
            raise RuntimeError(
                '{}_config is not in CURRENT_EXPERIMENT, check if '
                '_set_up_config_file was run in init and that file exists in '
                'scriptsfolder or local_scripts_subfolder'.format(cfg_name))
        if cfg_type == 'local':
            raise RuntimeError('{}_config is already using local config at '
                               '{}'.format(cfg_name, cfg_file))
    elif not os.path.isfile(source):
        raise FileNotFoundError('{} file does not exist'.format(source))
    else:
        cfg_file = source
    local_cfg_file = get_local_config_file(cfg_name)
    copyfile(cfg_file, local_cfg_file)
    if cfg_name == 'calib':
        qubit_count = get_qubit_count()
        if qubit_count is not None:
            cfg = Config(local_cfg_file, isdefault=False)
            for s in cfg.sections():
                initial_vals = cfg.get(s)
                for k, v in initial_vals.items():
                    new_val_list = " ".join([str(v)] * qubit_count)
                    cfg.set(s, k, new_val_list)
    else:
        cfg = Config(local_cfg_file, isdefault=True)
    CURRENT_EXPERIMENT["{}_config".format(cfg_name)] = 'local'


def get_config(cfg_name: str):
    if "{}_config".format(cfg_name) in CURRENT_EXPERIMENT:
        file = get_config_file(cfg_name)
        if cfg_name == 'instr':
            return Config(file, isdefault=False)
        else:
            return Config(file, isdefault=True)
    else:
        raise RuntimeError(
            "{}_config not in CURRENT_EXPERIMENT".format(cfg_name))


def get_general_config(cfg_name: str):
    cfg_file = "{}{}.config".format(CURRENT_EXPERIMENT['scriptfolder'],
                                    cfg_name)
    cfg = Config(cfg_file, isdefault=False)
    return cfg


def get_allowed_keys(cfg_name: str, section=None):
    cfg_file = get_config(cfg_name=cfg_name)
    if section is not None:
        return list(cfg_file.get(section).keys())
    else:
        d = []
        for s in cfg_file.sections():
            d.extend(list(cfg_file.get(s).keys()))
        d.sort()
        return d


def _get_section_of_key(cfg, key):
    sections = []
    for s in cfg.sections():
        if key in cfg.get(s):
            sections.append(s)
    if len(sections) > 1:
        raise RuntimeError('multiple sections have same key name:'
                           'sections {} have key {}'.format(sections, key))
    elif len(sections) == 0:
        raise RuntimeError('key "{}" not in config file'.format(key))
    else:
        return sections[0]


def check_calibration_config():
    qubit_count = get_qubit_count() or 1
    cfg = get_config('calib')
    errors = {}
    for s in cfg.sections():
        for k, v in cfg.get(s).items():
            values_array = v.split(" ")
            if len(values_array) not in [1, qubit_count]:
                errors[k] = len(values_array)
    if errors:
        log.error('calib.config in use has value list with lenth '
                  'not equal to 1 or qubit_count: "key: list_length" as '
                  'follows {}'.format(errors))
    else:
        return True


def set_calibration_array(key, array):
    qubit_count = get_qubit_count()
    if qubit_count is None:
        raise RuntimeError('qubit count was not set on initalisation so '
                           'qubits cannot be indexed; only one calibration '
                           'value per key set by "set_calibration_val"')
    elif len(array) != qubit_count:
        raise Exception('array given must be the same length as the number'
                        ' of qubits: {}'.fromat(qubit_count))
    cfg = get_config('calib')
    str_array = " ".join([str(a) for a in array])
    section = _get_section_of_key(cfg, key)
    cfg.set(section, key, str_array)


def set_calibration_val(key, qubit_value, qubit_index: int=None):
    cfg = get_config('calib')
    section = _get_section_of_key(cfg, key)
    qubit_index = qubit_index or get_current_qubit()
    qubit_count = get_qubit_count()
    if qubit_index is not None and qubit_count is not None:
        if qubit_index >= qubit_count:
            raise RuntimeError('qubit_index {} >= qubit_count {}'
                               ''.format(qubit_index, qubit_count))
    if qubit_count in [None, 1]:
        if qubit_index not in [None, 0]:
            raise RuntimeError(
                'qubit count is 1 or unset so qubits_index must '
                'be unset or 0; only one calibration '
                'value per key')
        str_value = str(qubit_value)
    elif CURRENT_EXPERIMENT['calib_config'] == 'local':
        values_array = cfg.get(section, key).split(" ")
        val_ar_l = len(values_array)
        if val_ar_l not in [1, qubit_count]:
            raise RuntimeError(
                'local config calib in use and values list for key "{}" has '
                'length {} but qubit_count is {}'.format(
                    key, val_ar_l, qubit_count))
        elif val_ar_l == 1:
            str_value = str(qubit_value)
        elif qubit_index is None:
            raise RuntimeError(
                'local config calib in use and values list for key "{}" has '
                'length {} so qubit_index must be set via kwargs or '
                'set_current_qubit'.format(key, val_ar_l))
        else:
            values_array[qubit_index] = str(qubit_value)
            str_value = " ".join(values_array)
    if CURRENT_EXPERIMENT['calib_config'] == 'general':
        log.info('changing general config file value for '
                 '"{}" to "{}"'.format(key, str_value))
    cfg.set(section, key, str_value)


def get_calibration_val(key, qubit_index=None):
    cfg = get_config('calib')
    section = _get_section_of_key(cfg, key)
    values_array = cfg.get(section, key).split(" ")
    if len(values_array) == 1:
        if qubit_index is not None:
            log.info(
                'qubit_index specified in get_calibration_val but values list'
                ' for key "{}"  has length 1, will get this value'.format(key))
        val = values_array[0]
    else:
        qubit_index = (get_current_qubit()
                       if qubit_index is None else qubit_index)
        if qubit_index is None:
            raise RuntimeError(
                'qubit_index not specified but values list for '
                'key "{}"  has length {}'.format(key, len(values_array)))
        try:
            val = values_array[qubit_index]
        except IndexError:
            raise IndexError(
                'qubit_index {} out of range of values list, check '
                'calib.config {} list length'.format(qubit_index, key))
    return _cast_to_float_or_None(val)


def get_calibration_array(key):
    cfg = get_config('calib')
    section = _get_section_of_key(cfg, key)
    values_array = cfg.get(section, key).split(" ")
    if len(values_array) == 1:
        qubit_count = get_qubit_count()
        return [_cast_to_float_or_None(values_array[0])] * qubit_count
    else:
        return [_cast_to_float_or_None(v) for v in values_array]


def _cast_to_float_or_None(val):
    try:
        return float(val)
    except ValueError:
        if val == 'None':
            return None
        else:
            raise ValueError("val {} not None or possible to cast"
                             " to float".format(val))


def get_calibration_dict():
    cfg = get_config('calib')
    calib_dict = {}
    for s in cfg.sections():
        for k, v in cfg.get(s).items():
            val_array = [_cast_to_float_or_None(st) for st in v.split(" ")]
            calib_dict[k] = val_array
    return calib_dict


def print_pulse_settings():
    """
    Pretty prints pulse settings
    """
    pulse_dict = get_config().get('Pulse')
    pprint.pprint(pulse_dict, width=1)


#########################################
# Metadata List
#########################################

def _make_metadata_list(filename):
    metadata_list = []
    pickle.dump(metadata_list, open(filename, 'wb'))


def get_metadata_list():
    filename = get_local_scripts_location() + 'metadata_list.p'
    try:
        metadata_list = pickle.load(open(filename, "rb"))
    except FileNotFoundError:
        log.warning(
            'metadata list not found, making one at {}'.format(filename))
        metadata_list = _make_metadata_list(filename)
    return metadata_list


def add_to_metadata_list(*args):
    """
    Args:
        qcodes parameters to be added to metadata_list.p
        which flags them as parameters of interest. The values of these are
        printed when a dataset is loaded.
    """
    metadata_list = get_metadata_list()
    for param in args:
        inst_param_tuple = (param._instrument.name, param.name)
        if inst_param_tuple not in metadata_list:
            metadata_list.append(inst_param_tuple)
    _set_metadata_list(metadata_list)


def add_to_metadata_list_manual(instr_name, param_name):
    """
    Args:
        intr_name (str): name of instrument which param belongs to
        param_name (str): name of param
    """
    metadata_list = get_metadata_list()
    inst_param_tuple = (instr_name, param_name)
    if inst_param_tuple not in metadata_list:
        metadata_list.append(inst_param_tuple)
    _set_metadata_list(metadata_list)


def _set_metadata_list(updated_list):
    """
    Finction which creates 'metadata_list.p' in get_temp_dict_location
    and dumps picled list there (overwrites and existing list)

    Args:
        list to write
    """
    path = get_local_scripts_location()
    file_name = 'metadata_list.p'
    pickle.dump(updated_list, open(path + file_name, 'wb'))


def remove_from_metadata_list(instr):
    """
    Function which removes the instr_param_tuples from the matadata_list.p
    if they belong to this instrument

    Args:
        qcodes instrument or instrument name
    """
    metadata_list = get_metadata_list()
    if type(instr) is str:
        name = instr
    else:
        name = instr.name
    for inst_param_tuple in metadata_list:
        if inst_param_tuple[0] == name:
            metadata_list.remove(inst_param_tuple)
    _set_metadata_list(metadata_list)
