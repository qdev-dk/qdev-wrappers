import numpy as np
import logging
import concurrent.futures
import time
import progressbar
from qcodes.utils.validators import Numbers, Arrays
from qcodes.instrument.base import Instrument
from qcodes.instrument.parameter import ParameterWithSetpoints, _BaseParameter
from qcodes import Measurement
from SR830_ext import GeneratedSetPoints 
from typing import List

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
file_handler = logging.FileHandler('bundletimeing.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class BundleLockin(Instrument):
    """
    This is an instrument consisting of multiple Stanford Research Systems SR830
    Lock-in Amplifiers.
    The Instrument adds the functionallety of getting the trace
    of the induvidial lockins.
    The induvidial traces  share the setpoints  between lockins.
    """
    def __init__(self, name: str, lockins:tuple, *args, **kwargs) -> None:
        super().__init__(name, *args, **kwargs)

        self.lockins = lockins
        for lockin in self.lockins:
            lockin.buffer_SR('Trigger')
            lockin.buffer_trig_mode.set('ON')

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
                           vals=Numbers(1,1e3),
                           get_cmd=None,
                           set_cmd=None)              

        self.add_parameter('setpoints',
                            parameter_class=GeneratedSetPoints,
                            startparam=self.sweep_start,
                            stopparam=self.sweep_stop,
                            numpointsparam=self.sweep_n_points,
                            vals=Arrays(shape=(self.sweep_n_points.get_latest,)))

        for lockin in lockins:
            self.add_parameter('trace_{}'.format(lockin.name),
                        label='Signal {}'.format(lockin.name),
                        get_cmd = lockin.prepare_and_get_buffer,
                        unit='V',
                        vals=Arrays(shape=(self.sweep_n_points.get_latest,)),
                        setpoints=(self.setpoints,),
                        parameter_class=ParameterWithSetpoints)

    def set_sweep_parameters(self,sweep_param, start, stop, n_points=10, label=None):
        
        self.sweep_start.unit = sweep_param.unit
        self.sweep_start.vals = sweep_param.vals
        self.sweep_start.set(start)
        
        self.sweep_stop.unit = sweep_param.unit
        self.sweep_stop.vals = sweep_param.vals
        self.sweep_stop.set(stop)
        self.sweep_n_points.set(n_points)
        self.setpoints.unit = sweep_param.unit
        if label is not None:
            self.setpoints.label = label


def do2d_multi(param_slow: _BaseParameter, start_slow: float, stop_slow: float,
               num_points_slow: int, delay_slow: float,
               param_fast: _BaseParameter, start_fast: float, stop_fast: float,
               num_points_fast: int, delay_fast: float,
               bundle: BundleLockin,
               write_period: float = 1.,
               threading: List[bool] = [True, True, True, True],
               show_progress_bar: bool = True
               ):
    """
    This is a do2d only to be used with BundleLockin.

    Args:
        param_slow: The QCoDeS parameter to sweep over in the outer loop
        start_slow: Starting point of sweep in outer loop
        stop_slow: End point of sweep in the outer loop
        num_points_slow: Number of points to measure in the outer loop
        delay_slow: Delay after setting parameter in the outer loop
        param_fast: The QCoDeS parameter to sweep over in the inner loop
        start_fast: Starting point of sweep in inner loop
        stop_fast: End point of sweep in the inner loop
        num_points_fast: Number of points to measure in the inner loop
        delay_fast: Delay after setting parameter before measurement is performed
        write_period: The time after which the data is actually written to the
                      database.
        threading: For each ellement which are True, write_in_background, buffer_reset,
                   and send_trigger and get_trace will be threaded respectively
        show_progress_bar: should a progress bar be displayed during the
                           measurement.
    """

    logger.info('Starting do2d_multi with {}'.format(num_points_slow * num_points_fast))
    logger.info('write_in_background {},threading buffer_reset {},threading send_trigger {},threading  get trace {}'.format(*threading))
    begin_time = time.perf_counter()
    meas = Measurement()
    bundle.set_sweep_parameters(param_fast, start_fast, stop_fast, num_points_fast, label="Voltage")
    interval_slow = np.linspace(start_slow, stop_slow, num_points_slow)
    meas.write_period = write_period
    set_points_fast = bundle.setpoints

    meas.register_parameter(set_points_fast)
    param_fast.post_delay = delay_fast

    meas.register_parameter(param_slow)
    param_slow.post_delay = delay_slow

    bundle_parameters = bundle.__dict__['parameters']
    traces = [bundle_parameters[key] for key in bundle_parameters.keys() if 'trace' in key]
    for trace in traces:
        meas.register_parameter(trace, setpoints=(param_slow, set_points_fast))

    time_fast_loop = 0.0
    time_set_fast = 0.0
    time_buffer_reset = 0.0
    time_trigger_send = 0.0
    time_get_trace = 0.0

    if show_progress_bar:
        progress_bar = progressbar.ProgressBar(max_value=num_points_slow * num_points_fast)
        points_taken = 0

    with meas.run(write_in_background=threading[0]) as datasaver:
        run_id = datasaver.run_id

        for point_slow in interval_slow:
            param_slow.set(point_slow)

            begin_time_temp_buffer = time.perf_counter()
            if threading[1]:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    for lockin in bundle.lockins:
                        executor.submit(lockin.buffer_reset)
            else:
                for lockin in bundle.lockins:
                    lockin.buffer_reset()
            time_buffer_reset += time.perf_counter() - begin_time_temp_buffer

            begin_time_temp_fast_loop = time.perf_counter()
            for point_fast in set_points_fast.get():
                begin_time_temp_set_fast = time.perf_counter()
                param_fast.set(point_fast)

                time_set_fast += time.perf_counter() - begin_time_temp_set_fast
                begin_time_temp_trigger = time.perf_counter()
                if threading[2]:
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        for lockin in bundle.lockins:
                            executor.submit(lockin.send_trigger)
                else:
                    for lockin in bundle.lockins:
                        lockin.send_trigger()
                if show_progress_bar:
                    points_taken += 1
                    progress_bar.update(points_taken)
                time_trigger_send += time.perf_counter() - begin_time_temp_trigger    
            time_fast_loop += time.perf_counter() - begin_time_temp_fast_loop

            begin_time_temp_trace = time.perf_counter()
            if threading[3]:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    data = executor.map(trace_tuble, traces)

                data = list(data)
            else:
                data = []
                for trace in traces:
                    data.append((trace, trace.get()))
            time_get_trace += time.perf_counter() - begin_time_temp_trace

            data.append((param_slow, param_slow.get()))
            data.append((set_points_fast, set_points_fast.get()))
            datasaver.add_result(*data)

    message = 'Have finished the measurement in {} seconds. run_id {}'.format(time.perf_counter()-begin_time, run_id)
    logger.info(message)
    message2 = 'Time used in buffer reset {}. Time used in send trigger {}. Time used in get trace {}'.format(time_buffer_reset, time_trigger_send, time_get_trace)
    logger.info(message2)
    logger.info('time in the fast loop {}'.format(time_fast_loop))
    logger.info('time setting in the fast loop {}'.format(time_set_fast))

def trace_tuble(trace):
    return (trace, trace.get())
