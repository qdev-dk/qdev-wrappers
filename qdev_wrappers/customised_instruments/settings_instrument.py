
from qcodes.instrument.base import Instrument
from qcodes import Parameter
import yaml
from functools import partial
import copy
# TODO: docstrings
# TODO: write something for the instrument mapping?
# TODO: how should saving and loading be done?


class ImmutableDotDict(dict):
    __locked = False

    def __init__(self, initial_dict):
        for key in initial_dict:
            self.__setitem__(key, initial_dict[key])

    def lock(self):
        self.__locked = True
        for k, v in self.items():
            if isinstance(v, ImmutableDotDict):
                v.lock()

    def __setitem__(self, key, value):
        if self.__locked:
            raise RuntimeError('Setting not allowed')
        if isinstance(value, dict) and not isinstance(value, ImmutableDotDict):
            value = ImmutableDotDict(value)
        dict.__setitem__(self, key, value)

    def __getitem__(self, key):
        if '.' not in key:
            return dict.__getitem__(self, key)
        myKey, restOfKey = key.split('.', 1)
        target = dict.__getitem__(self, myKey)
        return target[restOfKey]

    def __contains__(self, key):
        if '.' not in key:
            return dict.__contains__(self, key)
        myKey, restOfKey = key.split('.', 1)
        target = dict.__getitem__(self, myKey)
        return restOfKey in target

    def __deepcopy__(self, memo):
        return copy.deepcopy(dict(self))

    def __setattr__(self, attr, value):
        if attr in ['_ImmutableDotDict__locked', 'unlock', 'lock']:
            print('attr allowed')
            object.__setattr__(self, attr, value)
        elif self.__locked:
            raise RuntimeError('Setting not allowed')
        else:
            object.__setattr__(self, attr, value)

    __getattr__ = __getitem__


class SettingsParameter(Parameter):
    def __init__(self, name,
                 file_save_fn,
                 initial_value=None,
                 derived_from=None,
                 instrument=None,
                 **kwargs):
        self._file_save_fn = file_save_fn
        self.derived_from = derived_from
        super().__init__(name=name,
                         instrument=instrument,
                         initial_value=initial_value,
                         get_cmd=None,
                         set_cmd=self._set_and_save,
                         **kwargs)

    def _set_and_save(self, val, derived_from=None):
        self.derived_from = derived_from
        self._save_val(val)
        self._file_save_fn()

    def __deepcopy__(self, memo):
        return self._latest['value']


class SettingsInstrument(Instrument):
    def __init__(self, name, file_to_load, qubit_num=None, file_to_save=None):
        with open(file_to_load) as f:
            initial_settings = yaml.safe_load(f)
        self._file_to_save = file_to_save or file_to_load
        super().__init__(name)
        self.settings = ImmutableDotDict(initial_settings)
        for _ in self._dic_to_parameters_dic(self.settings):
            pass
        self.settings.lock()
        self._save_to_file(file_to_save)

    def _generate_dict(self):
        return copy.deepcopy(self.settings)

    def _dic_to_parameters_dic(self, dic, path=None):
        for k, v in dic.items():
            local_path = '_'.join(filter(None, [path, k]))
            if isinstance(v, dict):
                for j in self._dic_to_parameters_dic(v, local_path):
                    yield local_path, j
            else:
                self.add_parameter(
                    name=local_path,
                    parameter_class=SettingsParameter,
                    file_save_fn=partial(
                        self._save_to_file, self._file_to_save),
                    initial_value=v)
                dic[k] = self.parameters[local_path]

    def _save_to_file(self, filename=None):
        if filename is not None:
            self._file_to_save = filename
        settings_to_save = self._generate_dict()
        with open(self._file_to_save, 'w+') as f:
            yaml.dump(settings_to_save, f, default_flow_style=False)
