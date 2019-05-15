from qcodes.instrument.channel import InstrumentChannel
import numpy as np
from functools import partial
from qcodes.utils import validators as vals
import logging
from qdev_wrappers.customised_instruments.customised_instruments.parametric_sequencer.parametric_sequencer import Setpoints

logger = logging.getLogger(__name__)


class SetpointsChannel(InstrumentChannel):
    """
    InstrumentChannel which generates and array of setpoints based on the
    values of it's parameters.
    """

    def __init__(self, parent, name: str):
        super().__init__(parent, name)
        self._custom_setpoints = None
        self.add_parameter(name='symbol',
                           label=f'{name} Setpoint Symbol',
                           set_cmd=parent.set_sequencer_not_up_to_date,
                           initial_value=None,
                           vals=vals.MultiType(vals.Strings(),
                                               vals.Enum(None)))
        self.add_parameter(name='start',
                           label=f'{name} Setpoints Start',
                           set_cmd=partial(self._set_start_stop, 'start'),
                           vals=vals.Numbers())
        self.add_parameter(name='stop',
                           label=f'{name} Setpoints Stop',
                           set_cmd=partial(self._set_start_stop, 'stop'),
                           vals=vals.Numbers())
        self.add_parameter(name='npts',
                           label=f'Number of {name} Setpoints',
                           set_cmd=self._set_npts,
                           vals=vals.MultiType(vals.Ints(0, 10000),
                                               vals.Enum(None)),
                           docstring=f'Sets the number of {name} setpoint'
                           'values; equivalent to setting the step')
        self.add_parameter(name='step',
                           label=f'{name} Setpoints Step Size',
                           set_cmd=self._set_step,
                           vals=vals.MultiType(vals.Numbers(),
                                               vals.Enum(None))
                           docstring=f'Sets the number of {name} setpoint'
                           ' values; equivalent to setting the npts')

    def _set_start_stop(self, start_stop, val):
        self._custom_setpoints = None
        npts = int(
            np.round(abs(self.stop() - self.start()) / self.step())) + 1
        self.npts._save_val(npts)
        self.parent.set_sequencer_not_up_to_date()

    def _set_npts(self, npts):
        self._custom_setpoints = None
        step = abs(self.stop() - self.start()) / (npts - 1)
        self.step._save_val(step)
        self.parent.set_sequencer_not_up_to_date()

    def _set_step(self, step):
        self._custom_setpoints = None
        npts = int(np.round(abs(self.stop() - self.start()) / step)) + 1
        self.npts._save_val(npts)
        self.parent.set_sequencer_not_up_to_date()

    def set_custom_setpoint_values(self, values):
        self._custom_setpoints = values
        self.start._save_val(None)
        self.stop._save_val(None)
        self.step._save_val(None)
        self.npts._save_val(len(values))

    @property
    def setpoints(self):
        if self.symbol() is not None:
            symbol = self.symbol()
            if self._custom_setpoints is not None:
                return Setpoints(symbol, self._custom_setpoints)
            else:
                try:
                    setpoints = np.linspace(
                        self.start(), self.stop(), num=self.npts(), endpoint=True)
                    return Setpoints(symbol, setpoints)
                except TypeError:
                    raise TypeError(
                        'Must set all from symbol, start, stop and'
                        ' npts to generate setpoints. Current values: '
                        '{}, {}, {}, {}'.format(self.symbol(), self.start(),
                                                self.stop(), self.npts()))
        else:
            return None
