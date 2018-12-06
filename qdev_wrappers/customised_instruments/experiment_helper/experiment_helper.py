import yaml
import logging
from qcodes.instrument.parameter import _BaseParameter
from qcodes.dataset.measurements import Measurement
from qdev_wrappers.customised_instruments.parametric_waveform_analyser.pwa import ParametricWaveformAnalyser
from qdev_wrappers.fitting.fitter import Fitter
from qdev_wrappers.fitting.fit_saving import save_fit_result
from collections import namedtuple
import time
import os
import numpy as np
import qcodes as qc
from itertools import product
import progressbar
from datetime import datetime

log = logging.getLogger(__name__)

scriptfolder = qc.config["user"]["scriptfolder"]
measurementsettingsfoldername = qc.config["user"]["measurementsettingsfolder"]

Task = namedtuple('Task', 'type callable')


class ExperimentHelper:
    def __init__(self, name, settings_instrument,
                 fitclass=None):
        self.name = name
        self._settings_instr = settings_instrument
        if not name.endswith(".yaml"):
            name += '.yaml'
        filepath = os.path.join(
            scriptfolder, measurementsettingsfoldername, name)
        if not os.path.isfile(filepath):
            raise ValueError(
                f'Measurement settings file {filepath} cannot be found')
        self._settings_file = filepath
        self._fitclass = fitclass
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
        self._traverse_and_set(self._settings_instr, settings)
        if any(isinstance(instr, ParametricWaveformAnalyser) for
               instr in self._settings_instr._station.components.values()):
            pwa = next(
                v for v in self._settings_instr._station.components.values() if
                isinstance(v, ParametricWaveformAnalyser))
            pwa.sequence.update_sequence()

    def _traverse_and_set(self, instr, settings_dict):
        """
        Given a settings instrument sets the parameters to match those
        SettingsParameters unless a value is specified in the
        settings_dict also provided.
        """
        for key, val in settings_dict.items():
            if isinstance(val, dict):
                submodule = instr.submodules[key]
                self._traverse_and_set(submodule, val)
            else:
                parameter = instr.parameters[key]
                parameter(val)

    def tear_down(self):
        for i, param_val in enumerate(self._latest_set_param_initial_values):
            if param_val is not None:
                self._latest_set_params[i].set(param_val)
        if any(isinstance(instr, ParametricWaveformAnalyser) for
               instr in self._settings_instr._station.components.values()):
            pwa = next(
                v for v in self._settings_instr._station.components.values() if
                isinstance(v, ParametricWaveformAnalyser))
            pwa.sequence.update_sequence()

    def measure(self, *meas_tasks, sweep=None, delay=0):
        if sweep is not None and len(sweep) % 5 != 0:
            raise RuntimeError(
                'must specify (sweep_param, start, stop, npts) for'
                ' each sweep parameter')
        # TODO: more checks here

        # set up measurement object
        meas = Measurement()
        refresh_time = 1.
        meas.write_period = refresh_time
#        meas.add_before_run(self._set_up, ())
#        meas.add_after_run(self._tear_down, ())

        # reorganise sweep information and set up progressbar
        set_params = []
        initial_set_param_values = []
        set_param_values = []
        sweep = [] if sweep is None else sweep
        for chunk in _chunks(sweep, 5):
            set_param, start, stop, num = chunk
            set_params.append(set_param)
            try:
                initial_set_param_values.append(set_param())
            except Exception:  # TODO: tidy
                initial_set_param_values.append(None)
                meas.register_parameter(set_param)
                set_param_values.append(np.linspace(start, stop, num))
        self._latest_set_params = set_params
        self._latest_set_param_initial_values = initial_set_param_values
        setpoint_combinations = list(product(*set_param_values))
        if len(setpoint_combinations) > 0:
            progress_bar = progressbar.ProgressBar(
                max_value=len(setpoint_combinations))
            points_taken = 0
            time.sleep(0.1)
        else:
            setpoint_combinations = [(0,)]

        # reorganise meas_task information
        task_tuples = []
        for task in meas_tasks:
            setpoints = tuple(set_params) if sweep is not None else None
            if isinstance(task, _BaseParameter):
                meas.register_parameter(task, setpoints=setpoints)
                task_tuples.append(Task('parameter', task))
            else:
                task_tuples.append(Task('function', task))

        # run measurement!
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
                time.sleep(delay)
            printable_time = datetime.fromtimestamp(
                current_time).strftime('%Y-%m-%d %H:%M:%S')
            print('Measurement finished at ', printable_time)

    def fit(self, fitclass=None, run_id=None):
        fitclass = fitclass or self._fitclass
        run_id = run_id or self._latest_run_id
        if run_id is not None and fitclass is not None:
            fit = Fitter(run_id, self._fitclass)
            save_fit_result(fit)
            fit.plot()
        else:
            raise RuntimeError(
                'Must specify fitclass and have run_id to perform fit')
        if len(fit.fit_results) == 1:
            print(fit.fit_results[0]['param_values'])
        return fit.fit_results


def _chunks(l, n):
    """
    Yield successive n-sized chunks from l.
    """
    for i in range(0, len(l), n):
        yield l[i:i + n]
