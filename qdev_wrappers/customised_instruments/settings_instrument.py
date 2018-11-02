from qcodes.instrument.base import Instrument
from qcodes.instrument.channel import InstrumentChannel
from qcodes import Parameter
import yaml


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
        for name, submodule in self.submodule.items():
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
                 default_value=None):
        self._delegate_parameter = delegate_parameter
        self._settings_instr = settings_instr
        super().__init__(name=name,
                         instrument=instrument,
                         get_cmd=None,
                         set_cmd=self._set_and_save)
        self._save_val(default_value)

    def _set_and_save(self, val):
        self._set_delegate_parameter(val)
        self._save_val(val)
        self._settings_instr._save_to_file()

    def _set_delegate_parameter(self, val=None):
        val = self._latest['value'] if val is None else val
        if self.delegate_parameter._latest['value'] != val:
            self.delegate_parameter(val)

    def _to_saveable_value(self):
        return {'default_value': self._latest['value'],
                'parameter': self._delegate_parameter.name}


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
                ch = SettingsChannel(instr, k)
                instr.add_submodule(k, ch)
                self._dic_to_parameters_dic(v, ch)

    def _get_instr_parameters(self, instr, params_dict):
        """
        Gets the Parameters of an instrument and puts them in a dictionary,
        does the same with any submodules.
        """
        params_dict.update(instr.parameters)
        for submodule in instr.submodules.values():
            self._get_instr_parameters(self, submodule, params_dict)

    def _get_station_parameters(self):
        """
        Gets the Parameters of all the instruments registered in the station as
        a dictionary.
        """
        params_dict = {}
        for instr in self._station.components:
            if isinstance(instr, Parameter):
                params_dict[instr.name] = instr
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
        with open(self._file_to_save, 'w+') as f:
            yaml.dump(settings_to_save, f, default_flow_style=False)

