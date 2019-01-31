from qcodes.instrument.parameter import Parameter, MultiParameter

class AlazarMultiChannelParameterHack(MultiParameter):
    """
    A hack parameter which returns the multi channel data of a list of
    alazar channels. This is necessary because the AlazarMultiChannelParameter
    gets created new every time so storing an instance of the class isn't
    useful.
    """
    def __init__(self, name, instr, alazar_chan_list):
        self._channels = alazar_chan_list
        names = tuple(ch.name for ch in self._channels)
        shapes = tuple(() for _ in self._channels)
        super().__init__(name=name,
                         names=names,
                         shapes=shapes,
                         instrument=instr)

    def get_raw(self):
        self.names = self._channels.data.names
        self.shapes = self._channels.data.shapes
        self.labels = self._channels.data.labels
        self.units = self._channels.data.units
        self.sepoints = self._channels.data.setpoints
        self.setpoint_names = self._channels.data.setpoint_names
        self.setpoint_labels = self._channels.data.setpoint_labels
        self.setpoint_units = self._channels.data.setpoint_units
        return self._channels.data()


class PulseBuildingParameter(Parameter):
    """
    A Parameter representing a parameter of a pulse sequence running
    on a ParametricSequencer (ie used to build the context).
    It has a pulse_building_name attribute for use in sequence building
    and updates the sequence on setting.
    """

    def __init__(self, name, instrument, pulse_building_name=None,
                 label=None, unit=None, set_fn=None,
                 vals=None, **kwargs):
        self._set_fn = set_fn
        super().__init__(
            name, instrument=instrument, label=label, unit=unit,
            get_cmd=None, vals=vals, **kwargs)
        pulse_building_name = pulse_building_name or name
        self.pulse_building_name = pulse_building_name

    def set(self, val):
        if self._set_fn is False:
            raise RuntimeError(f"Setting {self.full_name} not allowed")
        elif self._set_fn is None:
            self._save_val(val)
        else:
            self._save_val(val)
            self._set_fn(val)
        if isinstance(self.instrument, SidebandingChannel):
            pwa_instr = self.instrument._parent._parent
        elif isinstance(self.instrument, (ReadoutChannel, DriveChannel)):
            pwa_instr = self.instrument._parent
        else:
            logger.warning(f'could not establish how to update sequence '
                           'while setting {self.name} PulseBuildingParameter')
        try:
            sequencer_param = pwa_instr._sequencer.repeat.parameters[self.pulse_building_name]
            sequencer_param.set(val)
        except KeyError:
            if not pwa_instr.sequence.suppress_sequence_upload:
                pwa_instr.sequence._update_sequence()
