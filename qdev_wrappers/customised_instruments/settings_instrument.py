
from qcodes.instrument.base import Instrument
from qcodes.instrument.channel import InstrumentChannel
from qcodes import Parameter
import yaml


class SettingsChannel(InstrumentChannel):
    def _to_saveable_value(self):
        dict_to_save = {}
        for name, param in self.parameters.items():
            dict_to_save[name] = param._to_saveable_value()
        for name, submodule in self.submodule.items():
            dict_to_save[name] = submodule._to_saveable_value()
        return dict_to_save


class SettingsParameter(Parameter):
    def __init__(self, name,
                 settings_instr,
                 delegate_parameter,
                 instrument=None,
                 default_value=None):
        self._delegate_parameter = delegate_parameter
        self._settings_instr = settings_instr
        super().__init__(name=name,
                         instrument=instrument,
                         initial_value=default_value,
                         get_cmd=None,
                         set_cmd=self._set_and_save)

    def _set_and_save(self, val):
        self._save_val(val)
        self._settings_instr._save_to_file()

    def set_delegate_parameter(self):
        self.delegate_parameter(self._latest['value'])

    def _to_saveable_value(self):
        return {'default_value': self._latest['value'],
                'parameter': self._delegate_parameter.name}


class SettingsInstrument(Instrument):
    def __init__(self, name,
                 default_settings_file,
                 station,
                 file_to_save=None):
        with open(default_settings_file) as f:
            initial_settings = yaml.safe_load(f)
        if file_to_save is not None:
            with open(file_to_save, 'w+') as f:
                yaml.dump(initial_settings, f, default_flow_style=False)
            self._file_to_save = file_to_save
        else:
            self._file_to_save = default_settings_file
        self._station = station
        super().__init__(name)
        params_dict = self._get_station_parameters()
        _dic_to_parameters_dic(initial_settings, params_dict)

    def _dic_to_parameters_dic(self, settings_dic, params_dict, instr=None):
        instr = instr or self
        for k, v in settings_dic.items():
            if sorted(list(v.keys())) == ['default_value', 'parameter']:
                param_name = k
                param_value = v['default_value']
                delegate_parameter_name = v['parameter']
                delegate_parameter = self.station_parameters[delegate_parameter_name]
                instr.add_parameter(name=param_name,
                                    settings_instr=self,
                                    instruent=instr,
                                    initial_value=param_value,
                                    delegate_parameter=delegate_parameter,
                                    parameter_class=SettingsParameter)
            else:
                ch = self._add_submodule_to_instr(k, instr)
                self._dic_to_parameters_dic(v, ch)

    def _add_submodule_to_instr(self, name, instr_to_add_to):
        ch = SettingsChannel(instr_to_add_to, name)
        instr_to_add_to.add_submodule(name)
        return ch

    def _get_instr_parameters(self, instr, params_dict):
        params_dict.update(instr.parameters)
        for submodule in instr.submodules.values():
            self._get_instr_parameters(self, submodule, params_dict)

    def _get_station_parameters(self):
        params_dict = {}
        for instr in self._station.components:
            if isinstance(instr, Parameter):
                params_dict[instr.name] = instr
            else:
                self._get_instr_parameters(instr, params_dict)
        return params_dict

    def _generate_dict(self):
        dict_to_save = {}
        for name, param in self.parameters.items():
            dict_to_save[name] = param._to_saveable_value()
        for name, submodule in self.submodules.items():
            dict_to_save[name] = submodule._to_saveable_value()
        return dict_to_save

    def _save_to_file(self, filename=None):
        if filename is not None:
            self._file_to_save = filename
        settings_to_save = self._generate_dict()
        with open(self._file_to_save, 'w+') as f:
            yaml.dump(settings_to_save, f, default_flow_style=False)
