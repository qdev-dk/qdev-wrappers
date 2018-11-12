from qcodes.instrument.channel import InstrumentChannel
from qcodes.utils import validators as vals
from functools import partial
import qcodes as qc
import os
import sys
import yaml
import numpy as np
from broadbean.loader import read_element
from contextlib import contextmanager

scriptfolder = qc.config["user"]["scriptfolder"]
pulsebuildingfoldername = qc.config["user"]["pulsebuildingfolder"]


class SetpointsChannel(InstrumentChannel):
    """
    InstrumentChannel which generates and array of setpoitns based on the
    values of it's parameters. 
    """
    # TODO: add flexibility for custom setpoints
    def __init__(self, parent, name: str, inner: bool=True):
        type_title = 'Inner' if inner else 'Outer'
        self.add_parameter(name='symbol',
                           label='{type_title} Setpoint Symbol',
                           set_cmd=self._set_symbol,
                           vals=vals.Strings())
        self.add_parameter(name='start',
                           label='{type_title} Setpoints Start',
                           set_cmd=partial(self._set_start_stop, 'start'))
        self.add_parameter(name='stop',
                           label='{type_title} Setpoints Stop',
                           set_cmd=partial(self._set_start_stop, 'stop'))
        self.add_parameter(name='npts',
                           label='Number of {type_title} Setpoints',
                           set_cmd=self._set_npts,
                           vals=vals.Ints(0, 1000),
                           docstring='Sets the number of {type_title} setpoint'
                           'values; equivalent to setting the step')
        self.add_parameter(name='step',
                           label='{type_title} Setpoints Step Size',
                           set_cmd=self._set_step,
                           docstring='Sets the number of {type_title} setpoint'
                           ' values; equivalent to setting the npts')
        self.start._save_val(0)
        self.stop._save_val(10)
        self.step._save_val(1)
        self.npts._save_val(11)

    def _set_symbol(self, symbol):
        self.symbol._save_val(symbol)
        if not self.suppress_sequence_upload:
            self._update_sequence()

    def _set_start_stop(self, start_stop, val):
        self.parameters[start_stop]._save_val(val)
        if not self.suppress_sequence_upload:
            self._update_sequence()

    def _set_npts(self, num):
        step = abs(self.stop() - self.start()) / num
        self.step._save_val(step)
        self.npts._save_val(num)
        if not self.suppress_sequence_upload:
            self._update_sequence()

    def _set_step(self, step):
        npts = int(abs(self.stop() - self.start()) / step)
        self.npts._save_val(npts)
        self.step._save_val(step)
        if not self.suppress_sequence_upload:
            self._update_sequence()

    @property
    def setpoints(self):
        if self.symbol() is not None:
            try:
                symbol = self.symbol()
                setpoints = np.linspace(
                    self.start(), self.stop(), num=self.npts())
                return (symbol, setpoints)
            except TypeError:
                raise TypeError(
                    'Must set all from symbol, start, stop and'
                    ' npts to generate setpoints. Current values: '
                    '{}, {}, {}, {}'.format(
                        self.symbol(), self.start(), self.stop(), self.npts()))
        else:
            return None


class SequenceChannel(InstrumentChannel):
    """
    An InstrumentChannel intended to belong to a ParametricWaveformAnalyser
    and which effectively groups the parameters related to the sequence
    including the sequence mode, the template element and the setpoint
    related paramters.
    """
    # TODO: template element to be a parameter (serialisable)

    def __init__(self, parent, name: str):
        self._template_element_dict = None
        self._first_element = None
        self.additional_context = {}
        self.additional_context_labels = {}
        self.additional_context_units = {}
        self.suppress_sequence_upload = True
        super().__init__(parent, name)
        inner_setpoints_channel = SetpointsChannel(
            self, 'inner_setpoints', inner=True)
        outer_setpoints_channel = SetpointsChannel(
            self, 'outer_setpoints', inner=False)
        self.add_submodule('inner_setpoints', inner_setpoints_channel)
        self.add_submodule('outer_setpoints', outer_setpoints_channel)
        self.add_parameter(name='mode',
                           set_cmd=self._set_seq_mode,
                           get_cmd=self._get_seq_mode,
                           docstring='Sets the repeat_mode on the sequencer'
                           'and the seq_mode on the alazar, reinstates all the'
                           'alazar channels and updates the sequence to '
                           'include or exclude the first element.')
        self.add_parameter(name='template_element',
                           label='Template Element',
                           set_cmd=self._set_template_element,
                           get_cmd=self._get_template_element,
                           docstring='Saves the name of the current template '
                           'element and sets/gets the actual element')

    def _get_seq_mode(self):
        if (self._parent._alazar.seq_mode() and
                self._parent._sequencer.repeat_mode() == 'sequence'):
            return True
        elif (not self._parent._alazar.seq_mode() and
              self._parent._sequencer.repeat_mode() == 'element'):
            return False
        elif (not self._parent._alazar.seq_mode() and
              (self._parent._sequencer.get_inner_setpoints() is None or
               len(self._parent._sequencer.get_inner_setpoints()) == 1) and
              self._parent._sequencer.get_outer_setpoints() is None):
            return False
        else:
            raise RuntimeError(
                'seq modes on sequencer and alazar do not match')

    def _set_seq_mode(self, mode):
        if str(mode).upper() in ['TRUE', '1', 'ON']:
            self._parent._alazar.seq_mode(True)
            self._parent._sequencer.repeat_mode('sequence')
            self._first_element = None
        else:
            self._parent._alazar.seq_mode(False)
            self._parent._sequencer.repeat_mode('element')
            self._first_element = self._template_element_dict['first_element']
        self._save_val(mode)
        self._update_sequence()

    def _get_template_element(self):
        return self._template_element_dict[
            self.template_element._latest['value']]

    def _set_template_element(self, template_element_name):
        self.template_element._save_val(template_element_name)
        if not self.suppress_sequence_upload:
            self._update_sequence()

    def _generate_context(self):
        """
        Makes up context, labels and units dictionaries based on all of the
        pulse bui associated with the parent Parametric
        Waveform Analyser.
        """
        context = {}
        labels = {}
        units = {}
        for name, param in self._parent._pulse_building_parameters.items():
            context[name] = param()
            labels[name] = param.label
            units[name] = param.unit
        return context, labels, units

    def _update_sequence(self):
        """
        Based on the values of the PulseBuildingParameters, the inner and
        outer setpoints and the template element uploads a sequence
        and updates the alazar_channels.
        """
        context, labels, units = self._generate_context()
        self._parent._sequencer.set_template(
            self.template_element(),
            first_sequence_element=self._first_element,
            inner_setpoints=self.inner_setpoints.setpoints,
            outer_setpoints=self.outer_setpoints.setpoints,
            context=context,
            labels=labels,
            unit=units)
        self._parent.readout._update_alazar_channels()

    def reload_template_element_dict(self):
        """
        Reloads the dictionary of template elements from the
        specified folder within the qc.config.user.scriptfolder with name
        qc.config.user.pulsebuildingfoldername
        """
        folderpath = os.path.join(scriptfolder, pulsebuildingfoldername)
        if not os.path.isdir(folderpath):
            raise ValueError(
                f'Pulse building folder {folderpath} cannot be found')
        sys.path.append(folderpath)
        template_element_dict = {}
        for file in os.listdir(folderpath):
            element_name = os.path.splitext(file)[0]
            if file.endswith(".yaml"):
                with open(file) as f:
                    yf = yaml.safe_load(f)
                element = read_element(yf)
            elif file.endswith(".py"):
                try:
                    element = importlib.import_module(
                        element_name).create_template_element()
                except AttributeError:
                    continue
            template_element_dict[element_name] = element
        self._template_element_dict = template_element_dict
        self.template_element.vals = vals.Enum(
            *template_element_dict.keys())

    @contextmanager
    def single_sequence_update(self):
        """
        For use when changing multiple PulseBuildingParameters at once
        ensures only one sequence upload.
        """
        initial_supression_value = self.suppress_sequence_upload
        self.suppress_sequence_upload = False
        yield
        self._update_sequence()
        self.suppress_sequence_upload = initial_supression_value
