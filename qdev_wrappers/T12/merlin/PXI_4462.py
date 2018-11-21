import time


from qcodes import Instrument
from qcodes.utils.validators import Numbers, Ints, Enum


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

class AITask(Task):

    _input_mode = {'diff': DAQmx_Val_Diff,
                   'pseudo_diff': DAQmx_Val_PseudoDiff,
                   'nrse': DAQmx_Val_NRSE,
                   'rse': DAQmx_Val_RSE}

    def __init__(self, device, channels, time_constant=0.05, rate = 1e5):
        Task.__init__(self)
        self._rate = rate
        self._time_constant = time_constant
        self._device = device

        self._ai_channels = channels

        self.configure()


    def configure(self):

        self.ClearTask()
        super().__init__()

        for ch, value in self._ai_channels.items():
            chan = self._device + '/ai' + str(ch)
            self.create_ai_chan(chan, value['range'], value['mode'])


        self._samps_per_chan_to_acquire = max(2,int(self._rate*self._time_constant))

        self._data = np.zeros((len(self._ai_channels),self._samps_per_chan_to_acquire))

        self.CfgSampClkTiming("",
                              self._rate,
                              DAQmx_Val_Rising,
                              # DAQmx_Val_FiniteSamps,
                              DAQmx_Val_ContSamps,
                              self._samps_per_chan_to_acquire)


    def input_range(self, value=None):
        for ch in self._ai_channels.keys():
            self._ai_channels[ch]['range'] = value
        self.configure()

    def time_constant(self, value=None):
        if value is None:
            return self._time_constant
        if value > 0:
            self._time_constant = value
        else:
            raise ValueError("time_constant must be finite")
        self.configure()

    def sample_rate(self, value=None):
        if value is None:
            return self._rate
        if value > 0:
            self._rate = value
        else:
            raise ValueError("rate must be finite")
        self.configure()

    def create_ai_chan(self, chan, vrange=10, mode='diff'):
        self.CreateAIVoltageChan(chan,
                                 "",
                                 self._input_mode[mode],
                                 -vrange,
                                 vrange,
                                 DAQmx_Val_Volts,
                                 None)
    def read(self):
        read = int32()
        self.ReadAnalogF64(self._samps_per_chan_to_acquire,
                           -1,
                           DAQmx_Val_GroupByChannel,
                           self._data,
                           self._data.size,
                           byref(read),
                           None)
        self.StopTask()
        return np.mean(self._data, axis=1)



class PXI_4462(Instrument):
    def __init__(self, name, device, ai_channels=None):
        super().__init__(name)
        self._ai_task = None

        time_constant=0.0000000001
        rate = 100e3
        self._device = device

        if ai_channels is None:
            ai_channels = {0: {'range':10, 'mode':'diff'},
                           1: {'range':10, 'mode':'diff'},
                           2: {'range':10, 'mode':'diff'},
                           3: {'range':10, 'mode':'diff'}}



        self._make_ai_task(ai_channels, time_constant, rate)


        self.add_parameter(name='time_constant',
                           label='Time constant',
                           get_cmd=self._ai_task.time_constant,
                           set_cmd=self._ai_task.time_constant,
                           set_parser=float,
                           unit='s',
                           vals=Numbers(min_value=0.0001))

        self.add_parameter(name='sample_rate',
                           label='Sample rate',
                           get_cmd=self._ai_task.sample_rate,
                           set_cmd=self._ai_task.sample_rate,
                           set_parser=int,
                           unit='S/s',
                           vals=Ints(max_value=int(1e6)))


        self.add_parameter(name='input_range',
                           label='Input rate',
                           # get_cmd=self._ai_task.input_range,
                           set_cmd=self._ai_task.input_range,
                           set_parser=float,
                           unit='V',
                           vals=Enum(0.316,1.00,3.16,10.0,31.6,42.4))

        self.add_parameter('ai',
                           get_cmd=self._ai_task.read,
                           # get_parser=float,
                           names=['ai%d'%ch for ch in ai_channels],
                           units=['V']*len(ai_channels),
                           parameter_class=ParameterArray)

        for ch in ai_channels:
            self.add_parameter('ai%d'%ch,
                               get_cmd=partial(self._get_ai_ch, ch),
                               unit='V')

            self.add_parameter('ai%d_range'%ch,
                               label='Range ai%d'%ch,
                               set_cmd=partial(self._ai_range, ch),
                               get_cmd=partial(self._ai_range, ch),
                               set_parser=float,
                               unit='V',
                               vals=Enum(0.316,1.00,3.16,10.0,31.6,42.4))

            self.add_parameter('ai%d_mode'%ch,
                               label='Mode ai%d'%ch,
                               set_cmd=partial(self._ai_mode, ch),
                               get_cmd=partial(self._ai_mode, ch),
                               vals=Enum('diff','pseudo_diff','nrse','rse'))


    def _ai_range(self, ch, rang=None):
        if rang is None:
            return self._ai_channels[ch]['range']
        self._ai_channels[ch].update({'range':rang})
        self._make_ai_task(self._ai_channels,
                           self.time_constant(),
                           self.sample_rate())

    def _ai_mode(self, ch, mode=None):
        if mode is None:
            return self._ai_channels[ch]['mode']
        self._ai_channels[ch].update({'mode':mode})
        self._make_ai_task(self._ai_channels,
                           self.time_constant(),
                           self.sample_rate())

    def _make_ai_task(self, channels, time_constant, rate):
        self._ai_channels = channels
        if self._ai_task is None:
            self._ai_task = AITask(self._device,
                                   channels=channels,
                                   time_constant=time_constant,
                                   rate=rate)
        else:
            self._ai_task.ClearTask()
            self._ai_task.__init__(self._device,
                                   channels=channels,
                                   time_constant=time_constant,
                                   rate=rate)


    def _get_ai_ch(self, ch):
        # now = datetime.now()
        # if self.ai._latest()['ts'] is None:
        #     tdiff = 100
        # else:
        #     last = self.ai._latest()['ts']
        #     tdiff = (now - last).total_seconds()

        # if tdiff > 2e-4:
            # self.ai.get()

        return self.ai.get()[ch]

    def __del__(self):
        print('stopped')
        try:
            self._ai_task.StopTask()
            self._ai_task.ClearTask()
        except:
            pass
        try:
            self._ao_task.StopTask()
            self._ao_task.ClearTask()
        except:
            pass
        super().__del__()


if __name__ == '__main__':
    import qcodes
    p = PXI_4462('p', 'PXI-4462_2')
    # print(p._ai_task.read())

    # end = time.time()
    # print(end-start)
    # print(p.ao0(0))
    print([float(x) for x in p.ai()])
    print([float(x) for x in p.ai()])
    # print(p.ai())
    print([float(x) for x in p.ai()])
    print([float(x) for x in p.ai()])
    print([float(x) for x in p.ai()])
    print([float(x) for x in p.ai()])
    print([float(x) for x in p.ai()])
    print([float(x) for x in p.ai()])
    print([float(x) for x in p.ai()])
    print([float(x) for x in p.ai()])
    print([float(x) for x in p.ai()])
    print([float(x) for x in p.ai()])
    print([float(x) for x in p.ai()])
    # print(p.ai())

    # for i in range(1000):
    #     dd = p._ai_task.read()
    #     print(dd)