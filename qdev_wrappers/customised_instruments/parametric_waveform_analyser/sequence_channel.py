from qcodes.utils import validators as vals
from qdev_wrappers.customised_instruments.parametric_waveform_analyser.setpoints_channel import SetpointsChannel
from qcodes.instrument.channel import InstrumentChannel
import importlib
import qcodes as qc
import os
import sys
import yaml
from broadbean.loader import read_element
scriptfolder = qc.config["user"]["scriptfolder"]
pulsebuildingfoldername = qc.config["user"]["pulsebuildingfolder"]


class SequenceChannel(InstrumentChannel):
    """
    An InstrumentChannel intended to belong to a ParametricWaveformAnalyser
    and which effectively groups the parameters related to the sequence
    including the sequence mode, the template element and the setpoint
    related paramters.
    """
    # TODO: template element to be a parameter (serialisable)
    # TODO: better way to check if up to date, eg if sequencer has been used by another instr

    def __init__(self, parent, name: str):
        self._template_element_dict = None
        self._first_element = None
        self._up_to_date = False
        super().__init__(parent, name)
        inner_setpoints_channel = SetpointsChannel(
            self, 'inner_setpoints', 'Inner')
        outer_setpoints_channel = SetpointsChannel(
            self, 'outer_setpoints', 'Outer')
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
                           set_cmd=self._set_template_element)

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
        pwa = self._parent
        if str(mode).upper() in ['TRUE', '1', 'ON']:
            pwa._alazar.seq_mode(True)
            pwa._sequencer.repeat_mode('sequence')
        else:
            pwa._alazar.seq_mode(False)
            pwa._sequencer.repeat_mode('element')
            self._sync_repeat_params()
        self.mode._save_val(mode)
        pwa.readout.update_alazar_channels()

    def _set_template_element(self, val):
        self.template_element._save_val(val)
        self._set_not_up_to_date()

    def _sync_repeat_params(self):
        pwa = self._parent
        for paramname, param in pwa._sequencer.repeat.parameters.items():
            param.set(pwa._pulse_building_parameters[paramname].get())

    def _set_not_up_to_date(self):
        for ch in self._parent._alazar_controller.channels:
            ch._stale_setpoints = True
        self._up_to_date = False

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
        return {'context': context, 'labels': labels, 'units': units}

    def update_sequence(self):
        """
        Based on the values of the PulseBuildingParameters, the inner and
        outer setpoints and the template element uploads a sequence
        and updates the alazar_channels.
        """
        if not self._up_to_date:
            self._parent._sequencer.change_sequence(
                template_element=self._template_element_dict[self.template_element()],
                initial_element=self._first_element,
                inner_setpoints=self.inner_setpoints.setpoints,
                outer_setpoints=self.outer_setpoints.setpoints,
                **self._generate_context())
            self._up_to_date = True
        if not self.mode():
            self._sync_repeat_params()
        self._parent.readout.update_alazar_channels()

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
                filepath = os.path.join(folderpath, file)
                with open(filepath) as f:
                    yf = yaml.safe_load(f)
                template_element_dict[element_name] = read_element(yf)
            elif file.endswith(".py"):
                try:
                    template_element_dict[element_name] = importlib.import_module(
                        element_name).create_template_element()
                except AttributeError:
                    continue
        self._template_element_dict = template_element_dict
        self._first_element = template_element_dict['first_element']
        self.template_element.vals = vals.Enum(
            *template_element_dict.keys())
        self._set_not_up_to_date()
