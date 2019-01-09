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
        source (None, Parameter): the optional source parameter this one
            is a delegate of.
        set_fn (False, None, Callable):
            - If False then setting the parameter is prohibited.
            - If None then running set results in saving the value provided or
              setting the source parameter to this value if source is not None.
            - If a Callable then this will be executed when set is called
              before saving/setting source.
        get_fn (Bool, None, Callable):
            - If False then getting the parameter is prohibited.
            - Otherwise if a source is provided then that is called.
            - If a Callable is provided and the source is None then the result
              of the Callable is returned.
            - If True and the source is None then the latest value is used.
            - If None and the source is Nont then a random number is generated.
    """
    def __init__(self,
                 name: str,
                 source: Optional['Parameter']=None,
                 get_fn: Optional[Union[Callable, bool]]=None,
                 set_fn: Optional[Union[Callable, bool]]=None,
                 *args, **kwargs):
        self.source = source
        if source is not None and isinstance(get_fn, Callable):
            raise RuntimeError(
                'If source provided cannot have callable get_fn')
        elif source is not None and get_fn is True:
            raise RuntimeError(
                'If source provided cannot have True get_fn')
        self.set_fn = set_fn
        self.get_fn = get_fn
        super().__init__(name=name, *args, **kwargs)

    def get_raw(self, **kwargs):
        if self.get_fn is False:
            raise RuntimeError(f'Parmeter {self.name} not gettable')
        elif self.source is not None:
            return self.source.get(**kwargs)
        if isinstance(self.get_fn, Callable):
            return self.get_fn(**kwargs)
        elif self.get_fn is True:
            return self._latest['raw_value']
        else:
            return np.random.random()

    def set_raw(self, *args, **kwargs):
        if self.set_fn is False:
            raise RuntimeError(f'Parmeter {self.name} not settable')
        elif self.set_fn is not None:
            self.set_fn(*args, **kwargs)
        if self.source is not None:
            self.source.set(*args, **kwargs)


class DelegateArrayParameter(ArrayParameter):
    """
    An ArrayParameter version of DelegateParameter. Not settable.
    """
    def __init__(self,
                 name: str,
                 source: Optional['ArrayParameter']=None,
                 get_fn: Optional[Union[Callable, bool]]=None,
                 **kwargs):
        self.source = source
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
            shape = kwargs.pop('shape', (1,))
            super().__init__(name=name,
                             shape=shape,
                             **kwargs)

    def get_raw(self, **kwargs):
        if self.get_fn is False:
            raise RuntimeError(f'Parmeter {self.name} not gettable')
        elif self.source is not None:
            self.label = self.source.label
            self.unit = self.source.unit
            self.sepoints = self.source.setpoints
            self.setpoint_names = self.source.setpoint_names
            self.setpoint_labels = self.source.setpoint_labels
            self.setpoint_units = self.source.setpoint_units
            return self.source.get(**kwargs)
        elif isinstance(self.get_fn, Callable):
            return self.get_fn(**kwargs)
        else:
            return np.random.random(self.shape)

class DelegateMultiParameter(MultiParameter):
    """
    An MultiParameter version of DelegateParameter. Not settable
    """
    def __init__(self,
                 name: str,
                 source: Optional['MultiParameter']=None,
                 get_fn: Optional[Union[Callable, bool]]=None,
                 **kwargs):
        self.source = source
        self.get_fn = get_fn
        if source is not None:
            super().__init__(name=name,
                             shapes=source.shapes,
                             names=source.names,
                             labels=source.labels,
                             units=source.units,
                             setpoints=source.setpoints,
                             setpoint_names=source.setpoint_names,
                             setpoint_labels=source.setpoint_labels,
                             setpoint_units=source.setpoint_units,
                             **kwargs)
        else:
            names = kwargs.pop('names',
                               ('delegate_parameter1', 'delegate_parameter2'))
            shapes = kwargs.pop('shapes', ((1,), (1,)))
            super().__init__(name=name,
                             shapes=shapes,
                             names=names,
                             **kwargs)

    def get_raw(self, **kwargs):
        if self.get_fn is False:
            raise RuntimeError(f'Parmeter {self.name} not gettable')
        elif self.source is not None:
            self.names = self.source.names
            self.labels = self.source.labels
            self.units = self.source.units
            self.sepoints = self.source.setpoints
            self.setpoint_names = self.source.setpoint_names
            self.setpoint_labels = self.source.setpoint_labels
            self.setpoint_units = self.source.setpoint_units
            return self.source.get(**kwargs)
        elif isinstance(self.get_fn, Callable):
            return self._get_fn(**kwargs)
        else:
            return (np.random.random(sh) for sh in self.shapes)


class DelegateMultiChannelParameter(MultiParameter):
    """
    An MultiParameter version of DelegateParameter which does not
    support simulation/manual parameter 'mode' and must have back end
    ChannelList. Not settable.

    Args:
        name (str): local namee of the parameter
        instrument (Instrument): the instrument to which the channels belong.
        get_fn (Bool, None, Callable):
            - If False then getting the parameter is prohibited.
            - Otherwise returns the results of the
              channels parameters get function.
    """
    def __init__(self,
                 name: str,
                 instrument: Instrument,
                 channellist: ChannelList,
                 paramname: str,
                 get_fn: Optional[bool]=None,
                 **kwargs):
        self.get_fn = get_fn
        self._full_name = instrument.name + '_Multi_' + paramname
        self._param_name = paramname
        self._channels = channellist
        shapes = kwargs.pop('shapes', ((1,) for _ in self._channels))
        names = kwargs.pop('names', (ch.name for ch in self._channels))
        super().__init__(name=name,
                         shapes=shapes,
                         names=names,
                         instrument=instrument)

    def get_raw(self, **kwargs):
        if self.get_fn is False:
            raise RuntimeError(f'Parmeter {self.name} not gettable')
        else:
            multi_chan_param = getattr(self._channels, self._param_name)
            self.names = multi_chan_param.names
            self.shapes = multi_chan_param.shapes
            self.labels = multi_chan_param.labels
            self.units = multi_chan_param.units
            self.sepoints = multi_chan_param.setpoints
            self.setpoint_names = multi_chan_param.setpoint_names
            self.setpoint_labels = multi_chan_param.setpoint_labels
            self.setpoint_units = multi_chan_param.setpoint_units
            return multi_chan_param.get(**kwargs)
