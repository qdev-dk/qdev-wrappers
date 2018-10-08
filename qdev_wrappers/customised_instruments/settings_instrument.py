
from qcodes.instrument.base import Instrument
from qcodes import Parameter
from qcodes.utils import validators as vals
from qcodes.instrument.channel import InstrumentChannel, ChannelList
import yaml
import os
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
        return DotDict(copy.deepcopy(dict(self)))

    def __setattr__(self, attr, value):
        if self.__locked:
            raise RuntimeError('Setting not allowed')
        elif attr != '_ImmutableDotDict__locked':
            raise RuntimeError('Setting not allowed')
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


class SettingsInstrument(Instrument):
    def __init__(self, name, file_to_load, qubit_num=None, file_to_save=None):
        with open(file_to_load) as f:
            initial_settings = yaml.safe_load(f)

        self._file_to_save = file_to_save or file_to_load
        super().__init__(name)
        def traverse(self, dic, path=None):
            for k, v in dic.items():
                local_path = '_'.join(filter(None, [path, k]))
                if isinstance(v, dict):
                    for j in traverse(self, v, local_path):
                        yield local_path, j
                else:
                    self.add_parameter(
                        name=local_path,
                        parameter_class=SettingsParameter,
                        file_save_fn=partial(self._save_to_file, self._file_to_save),
                        initial_value=v)
                    dic[k] = self.parameters[local_path]
                    yield local_path, v
        for _ in traverse(self, initial_settings): pass
        self.settings = ImmutableDotDict(initial_settings)

    #     is_default=initial_settings.pop('is_default')
    #     if is_default:
    #         if file_to_save is None:
    #             raise RuntimeError(
    #                 'Must specify file_to_save if file_to_load is default')
    #         if qubit_num is None:
    #             raise RuntimeError(
    #                 'Must specify qubit_num if file_to_load is default')
    #         for i in range(qubit_num):
    #             initial_settings['qubits'][f'Q{i}']=initial_settings['qubits']['Q0']
    #     else:
    #         if (qubit_num is not None and
    #                 (len(initial_settings['qubit']) != qubit_num)):
    #             raise RuntimeError(
    #                 '{} qubits found in {} but qubit_num specified as {}'
    #                 ''.format(len(initial_settings['qubit']),
    #                           file_to_load, qubit_num))
    #         if file_to_save is None:
    #             file_to_save=file_to_load
    #     self._file_to_save=file_to_save
    #     super().__init__(name)
    #     general_channels=ChannelList(self, "general", InstrumentChannel)
    #     self.add_submodule('general', general_channels)
    #     qubit_channels=ChannelList(
    #         self, "qubits", InstrumentChannel)
    #     self.add_submodule('qubits', qubit_channels)

    #     # load general settings parameters
    #     for param, param_dict in initial_settings['general'].items():
    #         self.general.add_parameter(
    #             name=param,
    #             parameter_class=SettingsParameter,
    #             file_save_fn=self.save_to_file,
    #             initial_value=param_dict.get('value', None),
    #             label=param_dict.get('label', None),
    #             unit=param_dict.get('unit', None))

    #     # load qubit settings parameters
    #     for i, qubit_dict in enumerate(initial_settings['qubits']):
    #         qubit_channel=InstrumentChannel(self, f'qubit_{i}')
    #         for param, param_dict in qubit_dict.items():
    #             qubit_channel.add_parameter(
    #                 name=param,
    #                 parameter_class=SettingsParameter,
    #                 file_save_fn=self.save_to_file,
    #                 initial_value=param_dict.get('value', None),
    #                 label=param_dict.get('label', None),
    #                 unit=param_dict.get('unit', None))
    #         qubit_channels.append(qubit_channel)
    #     qubit_channels.lock()

    def save_to_file(self, filename: str=None):
        if filename is not None:
            self._file_to_save = filename
        params_dict = self.generate_dict()
        with open(self._file_to_save, 'w+') as f:
            yaml.dump(params_dict, f, default_flow_style=False)

    # def generate_dict(self):
    #     params_dict={'is_default': False,
    #                    'general': {},
    #                    'qubits': []}
    #     for param_name in self.general.parameters:
    #         parm=getattr(self.general, param_name)
    #         params_dict['sample'][param_name]={'label': parm.label,
    #                                              'unit': parm.unit,
    #                                              'value': parm.get()}
    #     for qubit in self.qubits:
    #         qubit_params_dict={}
    #         for param_name in qubit.parameters:
    #             parm=getattr(qubit, param_name)
    #             qubit_params_dict[param_name]={'label': parm.label,
    #                                              'unit': parm.unit,
    #                                              'value': parm.get()}
    #         params_dict['qubits'].append(qubit_params_dict)
    #     return params_dict
