
from qcodes.instrument.base import Instrument
from qcodes import Parameter
from qcodes.utils import validators as vals
from qcodes.instrument.channel import InstrumentChannel, ChannelList
import yaml
import os

# TODO: docstrings
# TODO: write something for the instrument mapping?
# TODO: make the saving safer
# TODO: is there a better way to do the saving?
# TODO: update pulse building to use this instead of keeping context on pwa
#   what to do for home made ones? generate_context?


class SettingsParameter(Parameter):
    def __init__(self, name, file_save_fn,
                 instrument=None, initial_value=None, **kwargs):
        self._file_save_fn = file_save_fn
        super().__init__(name=name, instrument=instrument,
                         get_cmd=None, set_cmd=self._set_and_save,
                         initial_value=initial_value, **kwargs)

    def _set_and_save(self, val):
        self._save_val(val)
        self._file_save_fn()


class SettingsInstrument(Instrument):
    def __init__(self, name, file_to_load, qubit_num=None, file_to_save=None):
        with open(file_to_load) as f:
            initial_settings = yaml.safe_load(f)
        is_default = initial_settings.pop('is_default')
        if is_default:
            if file_to_save is None:
                raise RuntimeError(
                    'Must specify file_to_save if file_to_load is default')
            if qubit_num is None:
                raise RuntimeError(
                    'Must specify qubit_num if file_to_load is default')
            initial_settings['qubits'] = [initial_settings['qubits']
                                         for _ in range(qubit_num)]
        else:
            if (qubit_num is not None and
                    (len(initial_settings['qubit']) != qubit_num)):
                raise RuntimeError(
                    '{} qubits found in {} but qubit_num specified as {}'
                    ''.format(len(initial_settings['qubit']),
                              file_to_load, qubit_num))
            if file_to_save is None:
                file_to_save = file_to_load
        self._file_to_save = file_to_save
        super().__init__(name)
        general_channel = InstrumentChannel(self, 'general')
        self.add_submodule('general', general_channel)

        qubit_channels = ChannelList(
            self, "qubits", InstrumentChannel)
        self.add_submodule('qubits', qubit_channels)

        for param, param_dict in initial_settings['sample'].items():
            self.general.add_parameter(
                name=param,
                parameter_class=SettingsParameter,
                file_save_fn=self.save_to_file,
                initial_value=param_dict.get('value', None),
                label=param_dict.get('label', None),
                unit=param_dict.get('unit', None))

        for i, qubit_dict in enumerate(initial_settings['qubits']):
            qubit_channel = InstrumentChannel(self, f'qubit_{i}')
            for param, param_dict in qubit_dict.items():
                qubit_channel.add_parameter(
                    name=param,
                    parameter_class=SettingsParameter,
                    file_save_fn=self.save_to_file,
                    initial_value=param_dict.get('value', None),
                    label=param_dict.get('label', None),
                    unit=param_dict.get('unit', None))
            qubit_channels.append(qubit_channel)
        qubit_channels.lock()

    def save_to_file(self, filename: str=None):
        if filename is not None:
            self._file_to_save = filename
        params_dict = self.generate_dict()
        with open(self._file_to_save, 'w+') as f:
            yaml.dump(params_dict, f, default_flow_style=False)

    def generate_dict(self):
        params_dict = {'is_default': False,
                       'sample': {},
                       'qubits': []}
        for param_name in self.general.parameters:
            parm = getattr(self.general, param_name)
            params_dict['sample'][param_name] = {'label': parm.label,
                                                 'unit': parm.unit,
                                                 'value': parm.get()}
        for qubit in self.qubits:
            qubit_params_dict = {}
            for param_name in qubit.parameters:
                parm = getattr(qubit, param_name)
                qubit_params_dict[param_name] = {'label': parm.label,
                                                 'unit': parm.unit,
                                                 'value': parm.get()}
            params_dict['qubits'].append(qubit_params_dict)
        return params_dict
