from qcodes.instrument.parameter import Parameter, ArrayParameter, MultiParameter
from qcodes.instrument.base import Instrument
from qcodes.instrument.chann import Instrument

class DelegateParameter(Parameter):
    """
    Parameter which by default behaves like ManualParameter but can
    be easily configured to get/set a source parameter or run a
    function when get/set is called. The functions if specified
    have priority over the source. For setting if function and source
    are specified the function will be executed and then the source set.
    If a function is False it means the parameter cannot be get/set.
    """
    def __init__(self, name: str, source: Parameter=None, 
        get_fn=None, set_fn=None, *args, **kwargs):
        self.source = source
        self.set_fn = set_fn
        self.get_fn = get_fn
        super().__init__(name=name, *args, **kwargs)

    def get_raw(self, *args, **kwargs):
        if self.get_fn is False:
            raise RuntimeError(f'Parmeter {self.name} not gettable')
        elif self.get_fn is not None:
            return self._get_fn(*args, **kwargs)
        elif self.source is not None:
            return self.source.get(*args, **kwargs)
        else:
            return self._latest['value']

    def set_raw(self, *args, **kwargs):
        if self.set_fn is False:
            raise RuntimeError(f'Parmeter {self.name} not settable')
        elif self.set_fn is not None:
            self.set_fn(*args, **kwargs)
        if self.source is not None:
            self.source.set(*args, **kwargs)


class DelegateArrayParameter(ArrayParameter):
    """
    """
    def __init__(self, name: str, source: Parameter=None, 
        get_fn=None, set_fn=None, **kwargs):
        self.source = source
        self.set_fn = set_fn
        self.get_fn = get_fn
        if source is not None:
            super().__init__(name=name,
                             shape=source.shape,
                             label=source.label,
                             unit=source.unit,
                             setpoints=source.setpoints,
                             setpoint_names=source.setpoint_names,
                             setpoint_labels=source.setpoint_labels,
                             setpoint_units=source.setpoint_units,
                             **kwargs)
        else:
            super().__init__(name=name,
                             shape=source.shape,
                             **kwargs)


    def get_raw(self, *args, **kwargs):
        if self.get_fn is False:
            raise RuntimeError(f'Parmeter {self.name} not gettable')
        elif self.get_fn is not None:
            return self._get_fn(*args, **kwargs)
        elif self.source is not None:
            self.label = self.source.label
            self.unit = self.source.unit
            self.sepoints = self.source.setpoints
            self.setpoint_names = self.source.setpoint_names
            self.setpoint_labels = self.source.setpoint_labels
            self.setpoint_units = self.source.setpoint_units
            return self.source.get(*args, **kwargs)
        else:
            return np.random.random(self.shape)

    def set_raw(self, *args, **kwargs):
        if self.set_fn is False:
            raise RuntimeError(f'Parmeter {self.name} not settable')
        elif self.set_fn is not None:
            self.set_fn(*args, **kwargs)
        if self.source is not None:
            self.source.set(*args, **kwargs)


class DelegateMultiParameter(MultiParameter):
    def __init__(self, name: str, source: Parameter, **kwargs):
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

    def get_raw(self, *args, **kwargs):
        self.names = self.source.names
        self.shapes = self.source.shapes
        self.labels = self.source.labels
        self.units = self.source.units
        self.setpoints = self.source.setpoints
        self.setpoint_names = self.source.setpoint_names
        self.setpoint_labels = self.source.setpoint_labels
        self.setpoint_units = self.source.setpoint_units
        return self.source.get(*args, **kwargs)


class DelegateMultiChannelParameter(MultiParameter):
    def __init__(self, name: str, instrument: Instrument, channellist, paramname, **kwargs):
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
