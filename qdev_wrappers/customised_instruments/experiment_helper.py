# from qcodes.utils.helpers import DelegateAttributes
import yaml
import logging
from qcodes.instrument.parameter import _BaseParameter
from qcodes.dataset.measurements import Measurement
from collections import namedtuple
import time
import os
from datetime import datetime

log = logging.getLogger(__name__)

Task = namedtuple('Task', 'type callable')


class ExperimentHelper:
    def __init__(self, settings_instrument, settings_file=None, pwa=None):
        self._settings_instr = settings_instrument
        if settings_file is not None:
            if not settings_file.endswith(".yaml"):
                settings_file += 'yaml'
            settings_file = os.path.abspath(settings_file)
            if not os.path.isfile(settings_file):
                raise ValueError(
                    'Settings file {} cannot be found'.format(settings_file))
        self._settings_file = settings_file
        self._pwa = pwa
        self._latest_run_id = None
        self._latest_set_params = []
        self._latest_set_param_initial_values = []

    def set_up(self):
        """
        Using the settings_file and the settings_instr to set settings on
        all the instruments.
        """
        try:
            with open(self._settings_file, 'r') as settings:
                settings = yaml.load(settings)
        except TypeError:
            settings = {}
        if self._pwa is not None:
            with self._pwa.sequence.single_sequence_update():
                self._traverse_and_set(self._settings_instr, settings)
        else:
            self._traverse_and_set(self._settings_instr, settings)

    def _traverse_and_set(self, instr, settings_dict):
        """
        Given a settings instrument sets the parameters to match those
        SettingsParameters unless a value is specified in the
        settings_dict also provided.
        """
        for key, val in settings_dict.items():
            if isinstance(val, dict):
                submodule = instr.submodules[val]
                self._traverse_and_set(submodule, val)
            else:
                parameter = instr.parameters[key]
                parameter(val)

    def tear_down(self):
        for i, param_val in enumerate(self._latest_set_param_initial_values):
            if param_val is not None:
                self._set_params[i].set(param_val)

    def _chunks(l, n):
        """
        Yield successive n-sized chunks from l.
        """
        for i in range(0, len(l), n):
            yield l[i:i + n]

    def measure(*args):
        set_params = []
        initial_set_param_values = []
        set_param_values = []
        task_tuples = []
        meas = Measurement()
        refresh_time = 1.
        meas.write_period = refresh_time
        for chunk in _chunks(args, 4):
            if (all(isinstance(val, (float, int) for val in chunk[1:])) and
                    isinstance(chunk[0], _BaseParameter)):
                set_param, start, stop, num = chunk
                set_params.append(set_param)
                try:
                    initial_set_param_values.append(set_param())
                except Exception:
                    initial_set_param_values.append(None)
                meas.register_parameter(set_param)
                set_param_values.append(np.linspace(start, stop, num))
            elif all(callable(val) for val in chunk):
                for task in chunk:
                    if isinstance(task, _BaseParameter):
                        meas.register_parameter(task, setpoints=(param_set,))
                        task_tuples.append(Task('parameter', task))
                    else:
                        task_tuples.append(Task('function', task))
            else:
                raise RuntimeError(
                    'args {} do not satisfy (param, start, stop, numpoints) '
                    'pattern or (task1, measurable2, etc) pattern'
                    ''.format(chunk))
        setpoint_combinations = list(product(*set_param_values))
        if len(setpoint_combinations) > 0:
            progress_bar = progressbar.ProgressBar(
                max_value=len(setpoint_combinations))
            points_taken = 0
            time.sleep(0.1)
        else:
            setpoint_combinations = [(0,)]

        self._latest_set_params = set_params
        self._latest_set_param_initial_values = initial_set_param_values
        meas.add_before_run(self.set_up)
        meas.add_after_run(self.tear_down)

        with meas.run() as datasaver:
            self._latest_run_id = datasaver.run_id
            last_time = time.time()
            printable_time = datetime.fromtimestamp(
                last_time).strftime('%Y-%m-%d %H:%M:%S')
            print('Measurement started at ', printable_time)
            for setpointvalues in setpoint_combinations:
                result = []
                if len(setpoint_combinations) > 1:
                    for i, set_param in enumerate(set_params):
                        set_param.set(setpointvalues[i])
                        result.append((set_param, setpointvalues[i]))
                for task_tuple in task_tuples:
                    if task_tuple.type == 'param':
                        result.append(
                            (task_tuple.callable, task_tuple.callable.get()))
                    else:
                        task_tuple.callable()
                datasaver.add_result(*result)
                current_time = time.time()
                if len(setpoint_combinations) > 1:
                    points_taken += 1
                    if current_time - last_time >= refresh_time:
                        last_time = current_time
                        progress_bar.update(points_taken)
                    progress_bar.update(points_taken)
            printable_time = datetime.fromtimestamp(
                current_time).strftime('%Y-%m-%d %H:%M:%S')
            print('Measurement finished at ', printable_time)

    def analyse(self):
        raise NotImplementedError



rabi_measurement = ExperimentHelper(settings_instrument, 'rabi')

rabi_measurement.measure(exp.drive.carrier_frequency,
                         exp.drive.carrier_frequency() - 10e6,
                         exp.drive.carrier_frequency() + 10e6,
                         21, 0,
                         exp.readout.Q0.data)

rabi_measurement.analyse()

exp.drive.Q0.frequency(5.2e9)
