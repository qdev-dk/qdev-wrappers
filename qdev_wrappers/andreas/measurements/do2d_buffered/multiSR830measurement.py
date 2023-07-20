
from qcodes.instrument.parameter import ParameterWithSetpoints, Parameter, DelegateParameter

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

class Buffer(ParameterWithSetpoints):

    def get_raw(self):
        npoints = self.root_instrument.sweep_n_points.get_latest()
        return np.random.rand(npoints)


def do2d_multi(param_set1, start1, stop1, num_points1, delay1,
         param_set2, start2, stop2, num_points2, delay2,
         *param_meas):
    '''Scan 2D of param_set and measure param_meas.'''
    meas = Measurement()
    refresh_time = 1. # in s
    meas.write_period = refresh_time

    set_points2 = GeneratedSetPoints(start2, stop2, num_points2)

    meas.register_parameter(param_set1)
    param_set1.post_delay = delay1
    meas.register_parameter(param_set2)
    param_set2.post_delay = delay2
    output = []

    for parameter in param_meas:
        meas.register_parameter(parameter, setpoints=(param_set1, param_set2))
        output.append([parameter, None])
    progress_bar = progressbar.ProgressBar(max_value=num_points1 * num_points2)
    points_taken = 0
    time.sleep(0.1)
    set_points1 = np.linspace(start1, stop1, num_points1)
    set_points2 = np.linspace(start2, stop2, num_points2)

    with meas.run(write_in_background=True) as datasaver:
        run_id = datasaver.run_id
        last_time = time.time()
        for point1 in set_points1:
            #param_set2.set(start2)
            param_set1.set(point1)
            #outputs = []
            for point in set_points2:
                param_set2.set(point)
                for lockin in param_meas:
                    lockin.send_trigger()
        data = []
        for lockin in param_meas:
            lockin.ch1_databuffer.prepare_buffer_readout()    
            data.append(lockin.ch1_databuffer.get())

                # notice that output is a list of tuples and it is created from scratch at each new iteration                
                output = ([(param_set1, set_point1), (param_set2, set_point2)] +
                          [(parameter, parameter.get()) for parameter in param_meas])
                outputs.append(output)
                points_taken += 1
            for output in outputs:
                datasaver.add_result(*output)
                # current_time = time.time()
                # if current_time - last_time >= refresh_time:
                #     last_time = current_time
                #     progress_bar.update(points_taken)
            progress_bar.update(points_taken)
    return run_id
