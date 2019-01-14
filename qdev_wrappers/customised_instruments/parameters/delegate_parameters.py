from qcodes.instrument.parameter import Parameter, ArrayParameter, MultiParameter
from qcodes.instrument.base import Instrument
from qcodes.instrument.channel import ChannelList
from typing import Optional, Union, Callable
import numpy as np


class DelegateParameter(Parameter):
    """
    A Parameter designed to interface with another parameter, mimic it or
    extend it.

    Args:
        name (str): local namee of the parameter
        source (Optional[Parameter]): the source parameter this one
            is a delegate of.
        set_allowed (bool)
        get_allowed (bool)
        get_fn (Optional[Callable]): If no source given and get_allowed this
            allows custom function to be given for get function. If a source is
            given this function is executed before returning the source.get
        set_fn (Optional[Callable]): If set_allowed this allows custom function
            to be run (this is run before the source is set if applicable)
    """

    def __init__(self,
                 name: str,
                 source: Optional['Parameter']=None,
                 set_allowed: bool=True,
                 get_allowed: bool=True,
                 get_fn: Optional[Callable]=None,
                 set_fn: Optional[Callable]=None,
                 *args, **kwargs):
        super().__init__(name=name, *args, **kwargs)
        self.source = source
        self.get_allowed = get_allowed
        self.set_allowed = set_allowed
        self.set_fn = set_fn
        self.get_fn = get_fn
        if source is not None:
            self.unit = source.unit
            if 'label' not in kwargs:
                self.label = source.label

    def get_raw(self, **kwargs):
        if not self.get_allowed:
            raise RuntimeError(f'Parmeter {self.name} not gettable')
        elif self.source is not None:
            if self.get_fn is not None:
                self.get_fn(**kwargs)
            return self.source.get(**kwargs)
        elif self.get_fn is None:
                return self._latest['raw_value']
        else:
            return self.get_fn(**kwargs)

    def set_raw(self, *args, **kwargs):
        if not self.set_allowed:
            raise RuntimeError(f'Parmeter {self.name} not settable')
        elif self.set_fn is not None:
            self.set_fn(*args, **kwargs)
        if self.source is not None:
            self.source.set(*args, **kwargs)


class DelegateArrayParameter(ArrayParameter):
    """
    An ArrayParameter version of DelegateParameter. Not settable.

    Args:
        name (str): local namee of the parameter
        source (Optional[Parameter]): the source parameter this one
            is a delegate of.
        get_allowed (bool)
        get_fn (Optional[Callable]): If no source given and get_allowed this
            allows custom function to be given for get function, otherwise a
            random array of the right shape is returned. If a source is
            given this function is executed before returning the source.get
    """

    def __init__(self,
                 name: str,
                 source: Optional['Parameter']=None,
                 get_allowed: bool=True,
                 get_fn: Optional[Callable]=None,
                 **kwargs):
        shape = source.shape if source else kwargs.pop('shape', (1,))
        super().__init__(name=name, shape=shape, **kwargs)
        self.source = source
        self.get_allowed = get_allowed
        self.get_fn = get_fn
        if source is not None:
            self.unit = source.unit
            self.setpoints = self.source.setpoints
            self.setpoint_names = self.source.setpoint_names
            self.setpoint_labels = self.source.setpoint_labels
            self.setpoint_units = self.source.setpoint_units
            if 'label' not in kwargs:
                self.label = source.label
        elif get_fn is None:
            self.get_fn = self.get_random

    def get_from_source(self, **kwargs):
        self.setpoints = self.source.setpoints
        self.setpoint_names = self.source.setpoint_names
        self.setpoint_labels = self.source.setpoint_labels
        self.setpoint_units = self.source.setpoint_units
        return self.source.get(**kwargs)

    def get_random(self, **kwargs):
        return np.random.random(self.shape)

    def get_raw(self, **kwargs):
        if self.get_allowed is False:
            raise RuntimeError(f'Parmeter {self.name} not gettable')
        elif self.source is not None:
            if self.get_fn is not None:
                self.get_fn(**kwargs)
            return self.get_from_source(**kwargs)
        else:
            return self.get_fn(**kwargs)


class DelegateMultiParameter(MultiParameter):
    """
    An MultiParameter version of DelegateParameter. Not settable.

    Args:
        name (str): local namee of the parameter
        source (Optional[Parameter]): the source parameter this one
            is a delegate of.
        get_allowed (bool)
        get_fn (Optional[Callable]): If no source given and get_allowed this
            allows custom function to be given for get function, otherwise a
            random tuple of arrays of the right shapes is returned. If a source
            is given this function is executed before returning the source.get
    """

    def __init__(self,
                 name: str,
                 source: Optional['Parameter']=None,
                 get_allowed: bool=True,
                 get_fn: Optional[Callable]=None,
                 **kwargs):
        names = kwargs.pop('names', ('delegate_parameter1',
                                      'delegate_parameter2'))
        shapes = kwargs.pop('shapes', ((1,), (1,)))
        super().__init__(name=name, names=names, shapes=shapes, **kwargs)
        self.source = source
        self.get_allowed = get_allowed
        self.get_fn = get_fn
        if source is not None:
            self.names = source.names
            self.shapes = source.shapes
            self.units = source.units
            self.setpoints = self.source.setpoints
            self.setpoint_names = self.source.setpoint_names
            self.setpoint_labels = self.source.setpoint_labels
            self.setpoint_units = self.source.setpoint_units
            if 'labels' not in kwargs:
                self.labels = source.labels
        elif get_fn is None:
            self.get_fn = self.get_random

    def get_from_source(self, **kwargs):
        self.setpoints = self.source.setpoints
        self.setpoint_names = self.source.setpoint_names
        self.setpoint_labels = self.source.setpoint_labels
        self.setpoint_units = self.source.setpoint_units
        return self.source.get(**kwargs)

    def get_random(self, **kwargs):
        return tuple(np.random.random(sh) for sh in self.shapes)

    def get_raw(self, **kwargs):
        if self.get_allowed is False:
            raise RuntimeError(f'Parmeter {self.name} not gettable')
        elif self.source is not None:
            if self.get_fn is not None:
                self.get_fn(**kwargs)
            return self.get_from_source(**kwargs)
        else:
            return self.get_fn(**kwargs)


class DelegateMultiChannelParameter(MultiParameter):
    """
    This is basically a reimagining of MultiChannelInstrumentParameter which
    allows the parameter to stick around instead of a new instance being
    created every time the parameter of a channellist it called. There is no
    simulation option and a backend ChannelList must be provided.

    Args:
        name (str): local namee of the parameter
        channes (ChannelList): the list of channels from which the
            parameter will be gotten.
        param_name (bool): the name of the parameter to be gotten from
            the channels
        get_allowed (bool)
        set_allowed (bool)
        get_fn (Optional[Callable]): If get_allowed this function is executed
            before returning the channel parameter.get results
        set_fn (Optional[Callable]): If set_allowed this allows custom function
            to be run before the source is set.
    """

    def __init__(self,
                 name: str,
                 channels: ChannelList,
                 param_name: str,
                 get_allowed: bool=True,
                 set_allowed: bool=True,
                 set_fn: Optional[Callable]=None,
                 get_fn: Optional[Callable]=None,
                 **kwargs):
        self._channels = channels
        self._param_name = param_name
        self._full_name = channels._parent.name + '_Multi_' + param_name
        parameters = [chan.parameters[param_name] for chan in channels]
        self._is_array_param = isinstance(parameters[0], ArrayParameter)
        names = self._get_names()
        shapes = self._get_shapes(parameters)
        super().__init__(name=name, names=names, shapes=shapes)
        self.labels = self._get_labels(parameters)
        self.units = self._get_units(parameters)
        if self._is_array_param:
            self._set_setpoints_info(parameters)
        self.get_allowed = get_allowed
        self.set_allowed = set_allowed
        self.set_fn = set_fn
        self.get_fn = get_fn

    def _get_names(self):
        return tuple("{}_{}".format(chan.name, self._param_name) for
                     chan in self._channels)

    def _get_shapes(self, parameters):
        if self._is_array_param:
            return tuple(parameter.shape for parameter in parameters)
        else:
            return tuple(() for _ in parameters)

    def _get_labels(self, parameters):
        return tuple(parameter.label for parameter in parameters)

    def _get_units(self, parameters):
        return tuple(parameter.unit for parameter in parameters)

    def _set_setpoints_info(self, parameters):
        self.setpoints = tuple(p.setpoints for p in parameters)
        self.setpoint_names = tuple(p.setpoint_names for p in parameters)
        self.setpoint_labels = tuple(p.setpoint_labels for p in parameters)
        self.setpoint_units = tuple(p.setpoint_units for p in parameters)

    def get_raw(self, **kwargs):
        if self.get_allowed is False:
            raise RuntimeError(f'Parmeter {self.name} not gettable')
        if self.get_fn is not None:
            self.get_fn()
        parameters = [chan.parameters[self._param_name] for
                      chan in self._channels]
        self.names = self._get_names()
        self.shapes = self._get_shapes(parameters)
        self.labels = self._get_labels(parameters)
        self.units = self._get_units(parameters)
        if self._is_array_param:
            self._set_setpoints_info(parameters)
        return tuple(chan.parameters[self._param_name].get(**kwargs) for chan
                     in self._channels)

    def set_raw(self, *args, **kwargs):
        if self.set_allowed is False:
            raise RuntimeError(f'Parmeter {self.name} not settable')
        if self.set_fn is not None:
            self.set_fn(**kwargs)
        for chan in self._channels:
            chan.parameters[self._param_name].set(*args, **kwargs)
