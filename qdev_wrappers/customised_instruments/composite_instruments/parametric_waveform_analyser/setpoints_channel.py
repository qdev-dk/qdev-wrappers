from qcodes.instrument.channel import InstrumentChannel
import numpy as np
from functools import partial
from qcodes.utils import validators as vals


class SetpointsChannel(InstrumentChannel):
    """
    InstrumentChannel which generates and array of setpoints based on the
    values of it's parameters.
    """

    def __init__(self, parent, name: str, type_title=None):
        super().__init__(parent, name)
        self._custom_setpoints = None
        type_title = '' if type_title is None else (type_title + ' ')
        self.add_parameter(name='symbol',
                           label=f'{type_title}Setpoint Symbol',
                           set_cmd=self._set_symbol,
                           vals=vals.MultiType(vals.Strings(),
                                               vals.Enum(None)))
        self.add_parameter(name='start',
                           label=f'{type_title}Setpoints Start',
                           set_cmd=partial(self._set_start_stop, 'start'),
                           vals=vals.Numbers())
        self.add_parameter(name='stop',
                           label=f'{type_title}Setpoints Stop',
                           set_cmd=partial(self._set_start_stop, 'stop'),
                           vals=vals.Numbers())
        self.add_parameter(name='npts',
                           label=f'Number of {type_title}Setpoints',
                           set_cmd=self._set_npts,
                           vals=vals.Ints(0, 1000),
                           docstring='Sets the number of {type_title}setpoint'
                           'values; equivalent to setting the step')
        self.add_parameter(name='step',
                           label=f'{type_title} Setpoints Step Size',
                           set_cmd=self._set_step,
                           vals=vals.Numbers(),
                           docstring='Sets the number of {type_title}setpoint'
                           ' values; equivalent to setting the npts')

    def _set_symbol(self, symbol):
        self.parent._up_to_date = False

    def _set_start_stop(self, start_stop, val):
        self._custom_setpoints = None
        self.parameters[start_stop]._save_val(val)
        npts = int(np.round(abs(self.stop() - self.start()) / self.step())) + 1
        self.npts._save_val(npts)
        self.parent._up_to_date = False

    def _set_npts(self, npts):
        if self._custom_setpoints is not None:
            raise RuntimeError(
                'Cannot set npts when custom setpoints are used')
        step = abs(self.stop() - self.start()) / (npts - 1)
        self.step._save_val(step)
        self.parent._up_to_date = False

    def _set_step(self, step):
        if self._custom_setpoints is not None:
            raise RuntimeError(
                'Cannot set npts when custom setpoints are used')
        npts = int(np.round(abs(self.stop() - self.start()) / step)) + 1
        self.npts._save_val(npts)
        self.parent._up_to_date = False

    def set_custom_setpoints(self, values):
        self._custom_setpoints = values
        self.start._save_val(None)
        self.stop._save_val(None)
        self.step._save_val(None)
        self.npts._save_val(len(values))

    @property
    def setpoints(self):
        if self.symbol() is not None:
            if self._custom_setpoints is not None:
                return self._custom_setpoints
            else:
                try:
                    symbol = self.symbol()
                    setpoints = np.linspace(
                        self.start(), self.stop(), num=self.npts(), endpoint=True)
                    return (symbol, setpoints)
                except TypeError:
                    raise TypeError(
                        'Must set all from symbol, start, stop and'
                        ' npts to generate setpoints. Current values: '
                        '{}, {}, {}, {}'.format(self.symbol(), self.start(),
                                                self.stop(), self.npts()))
        else:
            return None