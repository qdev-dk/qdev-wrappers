from qcodes.instrument.base import Instrument
from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qcodes.instrument.parameter import Parameter, MultiParameter
import yaml
import qcodes as qc
import os

scriptfolder = qc.config["user"]["scriptfolder"]
default_settingsfile = qc.config["user"]["settingsfile"]

class SettingsChannel(InstrumentChannel):
    """
    An InstrumentChannel intended to belong to a SettingsInstrument
    which has a function for saving values of it's parameters to a dictionary
    and attempting to call the same function on submodules.
    """

    def _to_saveable_value(self):
        dict_to_save = {}
        for name, param in self.parameters.items():
            dict_to_save[name] = param._to_saveable_value()
        for name, submodule in self.submodules.items():
            dict_to_save[name] = submodule._to_saveable_value()
        return dict_to_save


class SettingsParameter(Parameter):
    """
    A Parameter which has the bells and whistles of:
    - can be saved in a dictionary via '_to_saveable_value'
    - can set another 'delegate' parameter to mirror it's value
    """

    def __init__(self, name,
                 settings_instr,
                 delegate_parameter,
                 instrument=None,
                 initial_value=None):
        self._delegate_parameter = delegate_parameter
        self._settings_instr = settings_instr
        super().__init__(name=name,
                         instrument=instrument,
                         get_cmd=None)
        if initial_value is None:
            def to_saveable_value():
                return {'parameter': self._delegate_parameter.full_name}
            def set_delegate_param(*args):
                raise RuntimeError(f'Trying to set unsettable parameter {self.name}')
        else:
            self._save_val(initial_value)
            def to_saveable_value():
                return {'value': self._latest['value'],
                        'parameter': self._delegate_parameter.full_name}
            def set_delegate_param(val):
                val = self._latest['value'] if val is None else val
                if self._delegate_parameter._latest['value'] != val:
                    self._delegate_parameter(val)
        self._to_saveable_value = to_saveable_value
        self._set_delegate_parameter = set_delegate_param
            
    def set_raw(self, val):
        self._set_delegate_parameter(val)
        self._save_val(val)
        self._settings_instr._save_to_file()
    
    def get_raw(self):
        self._delegate_parameter.get()



class SettingsInstrument(Instrument):
    """
    An Instrument which is meant to store the 'ideal' settings of various
    Parameters and save them in a human readable way (.yaml file). It
    required a file to load from and a station full of real instruments which
    match those specified in the file to load from to be paired with settings
    parameters. A file to save to is option otherwise the file to load
    will be overwritten every time a SettingsParameter is set.
    """

    def __init__(self, name,
                 station,
                 filename=None):
        self._file_to_save = filename or default_settingsfile
        filepath = os.path.join(scriptfolder, self._file_to_save)
        with open(filepath) as f:
            initial_settings = yaml.safe_load(f)
        self._station = station
        super().__init__(name)
        params_dict = self._get_station_parameters()
        self._dic_to_parameters_dic(initial_settings, params_dict)

    def _dic_to_parameters_dic(self, settings_dic, params_dict, instr=None):
        """
        Based on the dictionary provided builds the sumbodule tree structure
        necessary and populates the leaves with Qcodes Parameters with initial
        values matching those specified and delegate parameters found in the
        station.
        """
        instr = instr or self
        for k, v in settings_dic.items():
            if 'parameter' in v.keys():
                param_name = k
                param_value = v.get('value', None)
                delegate_parameter_name = v['parameter']
                delegate_parameter = params_dict[delegate_parameter_name]
                instr.add_parameter(name=param_name,
                                    settings_instr=self,
                                    initial_value=param_value,
                                    delegate_parameter=delegate_parameter,
                                    parameter_class=SettingsParameter)
            else:
                ch = SettingsChannel(instr, k)
                instr.add_submodule(k, ch)
                self._dic_to_parameters_dic(v, params_dict, instr=ch)

    def _get_instr_parameters(self, instr, params_dict):
        """
        Gets the Parameters of an instrument and puts them in a dictionary,
        does the same with any submodules.
        """
        try:
            params_dict.update({param.full_name: param for param in instr.parameters.values()})
            for submodule in instr.submodules.values():
                if isinstance(submodule, ChannelList):
                    for ch in submodule:
                        self._get_instr_parameters(ch, params_dict)
                else:
                    self._get_instr_parameters(submodule, params_dict)
        except AttributeError:
            pass

    def _get_station_parameters(self):
        """
        Gets the Parameters of all the instruments registered in the station as
        a dictionary.
        """
        params_dict = {}
        for name, instr in self._station.components.items():
            if isinstance(instr, (Parameter, MultiParameter)):
                params_dict[instr.full_name] = instr
            else:
                self._get_instr_parameters(instr, params_dict)
        return params_dict

    def _generate_dict(self):
        """
        Gathers the SettingsParameters and all those in
        the sumbodules (and their submodules etc) into a dictionary to save
        from which the instrument could be reloaded.
        """
        dict_to_save = {}
        for name, param in self.parameters.items():
            if name != 'IDN':
                dict_to_save[name] = param._to_saveable_value()
        for name, submodule in self.submodules.items():
            dict_to_save[name] = submodule._to_saveable_value()
        return dict_to_save

    def _save_to_file(self, filename=None):
        """
        Generates dictionary representing the instrument in its current state
        and saves it to a yaml file.
        """
        if filename is not None:
            self._file_to_save = filename
        settings_to_save = self._generate_dict()
        filepath = os.path.join(scriptfolder, self._file_to_save)
        with open(filepath, 'w+') as f:
            yaml.dump(settings_to_save, f, default_flow_style=False)
