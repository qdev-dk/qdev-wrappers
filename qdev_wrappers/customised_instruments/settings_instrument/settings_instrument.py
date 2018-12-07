from qcodes.instrument.base import Instrument
from qcodes.instrument.channel import InstrumentChannel, ChannelList, MultiChannelInstrumentParameter
from qcodes.instrument.parameter import Parameter, MultiParameter, ArrayParameter
from qdev_wrappers.customised_instruments.settings_instrument.settings_parameters import SettingsMultiChannelParameter, SettingsMultiParameter, SettingsArrayParameter, SettingsParameter
import yaml
import qcodes as qc
import os
import logging

logger = logging.getLogger(__name__)

scriptfolder = qc.config["user"]["scriptfolder"]
default_settingsfile = qc.config["user"]["settingsfile"]


class SettingsInstrumentChannel(InstrumentChannel):
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


class SettingsInstrument(Instrument):
    """
    An Instrument which is meant to store the 'ideal' settings of various
    Parameters and save them in a human readable way (.yaml file). It
    required a file to load from and a station full of real instruments which
    match those specified in the file to load from to be paired with settings
    parameters. A file to save to is option otherwise the file to load
    will be overwritten every time a SettingsParameter is set.
    """
    # TODO make instances accessible from class so that we dont need to pass them in

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

    def set_up_parameter(self, name, initial_value,
                         delegate_parameter, instrument):
        if isinstance(delegate_parameter,
                      (SettingsMultiChannelParameter,
                       MultiChannelInstrumentParameter)):
            chan_list = delegate_parameter._channels
            param_to_add = SettingsMultiChannelParameter(
                name, instrument, chan_list, delegate_parameter.name)
        elif isinstance(delegate_parameter, MultiParameter):
            param_to_add = SettingsMultiParameter(
                name, instrument, delegate_parameter)
        elif isinstance(delegate_parameter, ArrayParameter):
            param_to_add = SettingsArrayParameter(
                name, instrument, delegate_parameter)
        else:
            param_to_add = SettingsParameter(
                name, self, instrument, delegate_parameter, initial_value)
        instrument.parameters[name] = param_to_add

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
                try:
                    delegate_parameter = params_dict[delegate_parameter_name]
                    self.set_up_parameter(
                        name=param_name,
                        initial_value=param_value,
                        delegate_parameter=delegate_parameter,
                        instrument=instr)
                except KeyError:
                    logger.warning(
                        f'Could not find {delegate_parameter_name}'
                        ' in station parameters to set up SettingsInstrument')
            else:
                ch = SettingsInstrumentChannel(instr, k)
                instr.add_submodule(k, ch)
                self._dic_to_parameters_dic(v, params_dict, instr=ch)

    def _get_instr_parameters(self, instr, params_dict):
        """
        Gets the Parameters of an instrument and puts them in a dictionary,
        does the same with any submodules.
        """
        try:
            params_dict.update(
                {param.full_name: param for
                 param in instr.parameters.values()})
            for submodule in instr.submodules.values():
                if isinstance(submodule, ChannelList):
                    params_dict.update(
                        self._get_channel_list_parameters(submodule))
                    for ch in submodule:
                        self._get_instr_parameters(ch, params_dict)
                else:
                    self._get_instr_parameters(submodule, params_dict)
        except AttributeError:
            pass

    def _get_channel_list_parameters(self, channellist):
        try:
            first_chan = channellist[0]
            return {param.full_name: param for
                    param in first_chan.parameters.values()}
        except IndexError:
            return {}

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
