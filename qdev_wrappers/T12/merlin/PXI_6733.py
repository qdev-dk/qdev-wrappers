import time


from qcodes import Instrument
from qcodes.utils.validators import Numbers, Ints, Enum
from qcodes.instrument.sweep_values import SweepFixedValues

from functools import partial
import numpy as np
from datetime import datetime

import PyDAQmx
from PyDAQmx.DAQmxFunctions import *
from PyDAQmx.DAQmxConstants import *
from PyDAQmx import Task, int32, DAQmxStartTask
from ctypes import byref

from qcodes import MultiParameter

import warnings

class ParameterArray(MultiParameter):

    def __init__(self, name, instrument, names, get_cmd=None, set_cmd=None, units=None, **kwargs):
        shapes = tuple(() for i in names)
        super().__init__(name, names, shapes, **kwargs)
        self._get = get_cmd
        self._set = set_cmd
        self._instrument = instrument
        self.units = units

    def get(self):
        if self._get is None:
            return None
        try:
            value = self._get()
            self._save_val(value)
            return value
        except Exception as e:
            e.args = e.args + ('getting {}'.format(self.full_name),)
            raise e

    def set(self, setpoint):
        if self._set is None:
            return None
        return self._set(setpoint)


    def sweep(self, start, stop, step=None, num=None):
        """
        Create a collection of parameter values to be iterated over.
        Requires `start` and `stop` and (`step` or `num`)
        The sign of `step` is not relevant.

        Args:
            start (Union[int, float]): The starting value of the sequence.
            stop (Union[int, float]): The end value of the sequence.
            step (Optional[Union[int, float]]):  Spacing between values.
            num (Optional[int]): Number of values to generate.

        Returns:
            SweepFixedValues: collection of parameter values to be
                iterated over

        Examples:
            >>> sweep(0, 10, num=5)
             [0.0, 2.5, 5.0, 7.5, 10.0]
            >>> sweep(5, 10, step=1)
            [5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
            >>> sweep(15, 10.5, step=1.5)
            >[15.0, 13.5, 12.0, 10.5]
        """
        return SweepFixedValues(self, start=start, stop=stop,
                                step=step, num=num)

class AOTask(Task):
    def __init__(self, device, channels, rate = 3e4):
        Task.__init__(self)
        self._rate = rate
        self._device = device

        self._ao_channels = channels

        self.configure()


    def configure(self):
        self.ClearTask()
        super().__init__()

        for ch, value in self._ao_channels.items():
            chan = self._device + '/ao' + str(ch)
            self.create_ao_chan(chan, value['range'])

            self._data = np.zeros((len(self._ao_channels),1), dtype=float)

        self.CfgOutputBuffer(uInt32(0))
        warnings.warn('AO task can currently not get the output voltage!')

    def output_range(self, value=None):
        for ch in self._ao_channels.keys():
            self._ao_channels[ch]['range'] = value
        self.configure()


    def write_ch(self, ch, data):
        # print(ch, data)
        self._data[ch] = data
        self.write(self._data)

    def write(self, data):
        self._data[:] = data
        # self._data = np.array(self._data, dtype=float)
        self.WriteAnalogF64(1,#len(data)/len(self._ao_channels),
                            1,
                            -1,
                            DAQmx_Val_GroupByChannel,
                            self._data,
                            None,
                            None)
        # self.StartTask()

    def read(self, ch=None):
        if ch is None:
            return self._data
        else:
            return self._data[ch]

    def create_ao_chan(self, chan, vrange):
        self.CreateAOVoltageChan(chan,
                                 "",
                                 -vrange,
                                 vrange,
                                 DAQmx_Val_Volts,
                                 None)

class PXI_6733(Instrument):
    def __init__(self, name, device, ao_channels=None):
        super().__init__(name)
        self._ao_task = None

        time_constant=0.01
        rate = 1e5
        self._device = device


        ###
        # Output
        if ao_channels is None:
            ao_channels = {0: {'range':10},
                           1: {'range':10},
                           2: {'range':10},
                           3: {'range':10},
                           4: {'range':10},
                           5: {'range':10},
                           6: {'range':10},
                           7: {'range':10}}

        self._make_ao_task(ao_channels)

        self.add_parameter(name='output_range',
                           label='Output rate',
                           # get_cmd=self._ao_task.output_range,
                           set_cmd=self._ao_task.output_range,
                           # set_parser=float,
                           unit='V',
                           vals=Enum(0.1, 0.2, 0.5, 1, 2, 5, 10))

        self.add_parameter('ao',
                           set_cmd=self._ao_task.write,
                           get_cmd=self._ao_task.read,
                           # get_parser=float,
                           names=['ao%d'%ch for ch in ao_channels],
                           units=['V']*len(ao_channels),
                           parameter_class=ParameterArray)
        # ±5 V, ±10 V,

        for ch in ao_channels:
            self.add_parameter('ao%d'%ch,
                               set_cmd=partial(self._ao_task.write_ch, ch),
                               get_cmd=partial(self._ao_task.read, ch),
                               unit='V',
                               vals=Numbers(min_value=-10, max_value=10))


    def _make_ao_task(self, channels):
        self._ao_channels = channels
        if self._ao_task is None:
            self._ao_task = AOTask(self._device,
                                   channels=channels)
        else:
            self._ao_task.ClearTask()
            self._ao_task.__init__(self._device,
                                   channels=channels)

    def _ao_range(self, ch, rang=None):
        if rang is None:
            return self._ao_channels[ch]['range']
        self._ao_channels[ch].update({'range':rang})
        self._make_ao_task(self._ao_channels,
                           self.time_constant(),
                           self.rate())

    def __del__(self):
        print('stopped')
        try:
            self._ao_task.StopTask()
            self._ao_task.ClearTask()
        except:
            pass
        super().__del__()


if __name__ == '__main__':
    import qcodes
    p = PXI_6259('p', 'PXI-6259')
    # print(p._ai_task.read())

    # end = time.time()
    # print(end-start)
    # print(dd)
    print(p.ao([0,0,0,0]))

    print(p.ao([2.2,2.3,0,0]))
    print(p.ao0(),p.ao1())
    p.ao0(1)

    # for i in range(1000):
    #     dd = p._ai_task.read()
    #     print(dd)
