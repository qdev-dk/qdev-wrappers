import numpy as np
from time import sleep
from qcodes.utils.validators import Numbers, Arrays
from qcodes.instrument.parameter import ParameterWithSetpoints, Parameter, DelegateParameter
from qcodes.instrument_drivers.stanford_research.SR830 import SR830


class SR830_ext(SR830):
    """
    This  is an extesension  of the Stanford Research Systems SR830
    Lock-in Amplifier driver

    The extension adds the functionallety to sweep a DelegateParameter
    from an other instruments while writiing to the buffer by sending software triggers.
    Furthermore, it adds the prepare_and_get_buffer function which is needed by bundle_lockin.py
    """
    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, **kwargs)

        self.add_parameter('sweep_param',
                           source=None,
                           parameter_class=DelegateParameter)

        self.add_parameter('sweep_start',
                           unit='',
                           initial_value=0,
                           get_cmd=None,
                           set_cmd=None)

        self.add_parameter('sweep_stop',
                           unit='',
                           initial_value=1,
                           get_cmd=None,
                           set_cmd=None)                                            

        self.add_parameter('sweep_n_points',
                           unit='',
                           initial_value=10,
                           vals=Numbers(1, 1e3),
                           get_cmd=None,
                           set_cmd=None)

        self.add_parameter('setpoints',
                           parameter_class=GeneratedSetPoints,
                           startparam=self.sweep_start,
                           stopparam=self.sweep_stop,
                           numpointsparam=self.sweep_n_points,
                           vals=Arrays(shape=(self.sweep_n_points.get_latest,)))

        self.add_parameter('sweep_wait_time',
                           unit='s',
                           initial_value=0.1,
                           get_cmd=None,
                           set_cmd=None)

        self.add_parameter(name='trace',
                           get_cmd=self._get_current_data,
                           label='Signal',
                           unit='V',
                           vals=Arrays(shape=(self.sweep_n_points.get_latest,)),
                           setpoints=(self.setpoints,),
                           parameter_class=ParameterWithSetpoints
                           )

    def _get_current_data(self):
        axis = self.setpoints()
        self.buffer_reset()
        for x in axis:
            self.sweep_param.set(x)
            sleep(self.sweep_wait_time.get())
            self.send_trigger()
        self.ch1_databuffer.prepare_buffer_readout()
        return self.ch1_databuffer.get()

    def prepare_and_get_buffer(self):
        self.ch1_databuffer.prepare_buffer_readout()
        return self.ch1_databuffer.get()

    def set_sweep_parameters(self,sweep_param, start, stop, n_points=10, wait_time=0.1, label=None):
        self.sweep_param.source = sweep_param

        self.sweep_start.unit = sweep_param.unit
        self.sweep_start.vals = sweep_param.vals
        self.sweep_start.set(start)

        self.sweep_stop.unit = sweep_param.unit
        self.sweep_stop.vals = sweep_param.vals
        self.sweep_stop.set(stop)
        self.sweep_n_points.set(n_points)
        self.sweep_wait_time.set(wait_time)
        self.setpoints.unit = sweep_param.unit
        if label is not None:
            self.setpoints.label = label


class GeneratedSetPoints(Parameter):
    """
    A parameter that generates a setpoint array from start, stop and num points
    parameters.
    """
    def __init__(self, startparam, stopparam, numpointsparam, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._startparam = startparam
        self._stopparam = stopparam
        self._numpointsparam = numpointsparam

    def get_raw(self):
        return np.linspace(self._startparam(), self._stopparam(),
                           self._numpointsparam())
