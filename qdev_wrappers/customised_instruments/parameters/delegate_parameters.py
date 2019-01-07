from qcodes.instrument.parameter import Parameter, ArrayParameter, MultiParameter


class DelegateParameter(Parameter):
    def __init__(self, name: str, source: Parameter, *args, **kwargs):
        self.source = source
        super().__init__(name=name, *args, **kwargs)

    def get_raw(self, *args, **kwargs):
        return self.source.get(*args, **kwargs)

    def set_raw(self, *args, **kwargs):
        self.source(*args, **kwargs)


class DelegateArrayParameter(ArrayParameter):
    def __init__(self, name, source, **kwargs):
        label = kwargs.pop('label') if 'label' in kwargs else source.label
        unit = kwargs.pop('unit') if 'unit' in kwargs else source.unit
        self.source = source
        super().__init__(name=name,
                         shape=source.shape,
                         label=label,
                         unit=unit,
                         setpoints=source.setpoints,
                         setpoint_names=source.setpoint_names,
                         setpoint_labels=source.setpoint_labels,
                         setpoint_units=source.setpoint_units,
                         **kwargs)

    def get_raw(self):
        self.shape = self.source.shape
        self.label = self.source.label
        self.unit = self.source.unit
        self.sepoints = self.source.setpoints
        self.setpoint_names = self.source.setpoint_names
        self.setpoint_labels = self.source.setpoint_labels
        self.setpoint_units = self.source.setpoint_units
        return self.source.get()


class DelegateMultiParameter(MultiParameter):
    def __init__(self, name, source, **kwargs):
        self.source = source
        names = kwargs.pop('names') if 'names' in kwargs else source.names
        labels = kwargs.pop('labels') if 'labels' in kwargs else source.labels
        units = kwargs.pop('units') if 'units' in kwargs else source.units
        super().__init__(name=name,
                         shapes=source.shapes,
                         names=names,
                         labels=labels,
                         units=units,
                         setpoints=source.setpoints,
                         setpoint_names=source.setpoint_names,
                         setpoint_labels=source.setpoint_labels,
                         setpoint_units=source.setpoint_units,
                         **kwargs)

    def get_raw(self):
        self.names = self.source.names
        self.shapes = self.source.shapes
        self.labels = self.source.labels
        self.units = self.source.units
        self.sepoints = self.source.setpoints
        self.setpoint_names = self.source.setpoint_names
        self.setpoint_labels = self.source.setpoint_labels
        self.setpoint_units = self.source.setpoint_units
        return self.source.get()


class DelegateMultiChannelParameter(MultiParameter):
    def __init__(self, name, instrument, channellist, paramname, **kwargs):
        self._full_name = instrument.name + '_Multi_' + paramname
        self._param_name = paramname
        self._channels = channellist
        shapes = tuple(() for _ in self._channels)
        names = kwargs.pop('names') if 'names' in kwargs else tuple(
            ch.name for ch in self._channels)
        labels = kwargs.pop('labels') if 'labels' in kwargs else None
        units = kwargs.pop('units') if 'units' in kwargs else None
        super().__init__(name=name,
                         shapes=shapes,
                         names=names,
                         labels=labels,
                         units=units,
                         instrument=instrument)

    def get_raw(self):
        multi_chan_param = getattr(self._channels, self._param_name)
        self.names = multi_chan_param.names
        self.shapes = multi_chan_param.shapes
        self.labels = multi_chan_param.labels
        self.units = multi_chan_param.units
        self.sepoints = multi_chan_param.setpoints
        self.setpoint_names = multi_chan_param.setpoint_names
        self.setpoint_labels = multi_chan_param.setpoint_labels
        self.setpoint_units = multi_chan_param.setpoint_units
        return multi_chan_param.get()

    def set_raw(self, val):
        self._channels.__getattr__(self._param_name).set(val)
