from typing import Union, Optional
from warnings import warn
from qcodes.instrument.base import Instrument
import qcodes.utils.validators as vals
from contextlib import contextmanager
from .pulse_building_parameter import PulseBuildingParameter
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateParameter
from qdev_wrappers.customised_instruments.composite_instruments.parametric_sequencer.parametric_sequencer import ParametricSequencer
from qdev_wrappers.customised_instruments.interfaces.microwave_source_interface import MicrowaveSourceInterface
from qdev_wrappers.customised_instruments.composite_instruments.heterodyne_source.heterodyne_source import HeterodyneSource

# TODO: docstrings
def check_carrier_sidebanding_status(carrier):
    if not carrier.status():
        warn('Carrier status is off')
    if isinstance(carrier, MicrowaveSourceInterface):
        if not carrier.IQ_state():
            warn('Sidebander carrier IQ state is off')
    elif isinstance(carrier, HeterodyneSource):
        if 'sidebanded' not in carrier.mode():
            warn('Sidebander carrier mode indicates not sidebanded')


class SequenceManager:

    def change_sequence(self, **kwargs):
        context_dict = self.generate_context()
        context_dict['context'].update(kwargs.pop('context', {}))
        context_dict['labels'].update(kwargs.pop('labels', {}))
        context_dict['units'].update(kwargs.pop('units', {}))
        self.sequencer.change_sequence(**context_dict, **kwargs)
        if self.sequencer._do_upload:
            self._sequencer_up_to_date = True
            self.sync_repeat_parameters()
        else:
            self._sequencer_up_to_date = False
        check_carrier_sidebanding_status(self.carrier)

    def sync_repeat_parameters(self):
        if self.sequencer.sequence_mode() == 'element':
            inner = self.sequencer.inner_setpoints
            outer = self.sequencer.outer_setpoints
            for setpoints in [i for i in [inner, outer] if i is not None]:
                if setpoints.symbol in self.pulse_building_parameters:
                    param = self.pulse_building_parameters[setpoints.symbol]
                    if setpoints.symbol in self.sequencer.repeat.parameters:
                        sequencer_param = self.sequencer.repeat.parameters[setpoints.symbol]
                        try:
                            sequencer_param.set(param())
                        except (RuntimeWarning, RuntimeError):
                            param._save_val(sequencer_param())
                            warn('Parameter {} could not be synced, value is now '
                                 '{}'.format(setpoints.symbol, sequencer_param()))

    def generate_context(self):
        context = {}
        labels = {}
        units = {}
        for p in self.pulse_building_parameters.values():
            context[p.symbol_name] = p()
            labels[p.symbol_name] = p.label
            units[p.symbol_name] = p.unit
        return {'context': context, 'labels': labels, 'units': units}

    def update_sequencer(self):
        original_do_upload_setting = self.sequencer._do_upload
        self.sequencer._do_upload = True
        if not self._sequencer_up_to_date:
            self.change_sequence()
        self.sequencer._do_upload = original_do_upload_setting

    @property
    def pulse_building_parameters(self):
        param_dict = {p.symbol_name: p for p in self.parameters.values() if
                      isinstance(p, PulseBuildingParameter)}
        for s in self.submodules.values():
            try:
                param_dict.update(s.pulse_building_parameters)
            except AttributeError:
                pass
        return param_dict


class SidebandParam(PulseBuildingParameter):
    def set_raw(self, val):
        self.instrument.frequency._save_val(self.instrument.carrier.frequency() + val)
        super().set_raw(val)


class Sidebander(Instrument, SequenceManager):
    """
    An instrument which represents a sequencer and microwave drive where the
    sequencer is used to sideband the microwave drive.
    """

    def __init__(self, name: str,
                 sequencer_name: str,
                 carrier_if_name: str,
                 symbol_prepend: Optional[str]= None,
                 **kwargs):
        super().__init__(name, **kwargs)
        self.carrier = Instrument.find_instrument(carrier_if_name)
        self.sequencer = Instrument.find_instrument(sequencer_name)
        self._sequencer_up_to_date = False
        self._symbol_prepend = '{symbol_prepend}_' if symbol_prepend else ''

        self.add_parameter(
            name='frequency',
            set_cmd=self._set_frequency,
            get_cmd=self._get_frequency,
            docstring='Setting updates sideband to generate required'
            ' frequency, getting calculates resultant sidebanded frequency')
        self.add_parameter(
            name='carrier_frequency',
            set_fn=self._set_carrier_frequency,
            source=self.carrier.frequency,
            parameter_class=DelegateParameter)

        # pulse building parameters
        self.add_parameter(
            name='sideband_frequency',
            parameter_class=SidebandParam,
            docstring='Setting this also updates the frequency parameter')
        self.add_parameter(
            name='I_offset',
            symbol_name=self._symbol_prepend + 'I_offset',
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='Q_offset',
            symbol_name=self._symbol_prepend + 'Q_offset',
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='gain_offset',
            symbol_name=self._symbol_prepend + 'gain_offset',
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='phase_offset',
            symbol_name=self._symbol_prepend + 'phase_offset',
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='amplitude',
            symbol_name=self._symbol_prepend + 'amplitude',
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='status',
            symbol_name=self._symbol_prepend + 'status',
            parameter_class=PulseBuildingParameter,
            vals=vals.Enum(0, 1))
        self.I_offset._save_val(0)
        self.Q_offset._save_val(0)
        self.amplitude._save_val(0.8)
        self.phase_offset._save_val(0)
        self.gain_offset._save_val(0)
        self.status._save_val(1)
        self.frequency._save_val(self.carrier.frequency())
        self.sideband_frequency._save_val(0)
        self.check_settings()

    def _set_frequency(self, val):
        new_sideband = val - self.carrier.frequency()
        self.sideband_frequency(new_sideband)

    def _get_frequency(self):
        return self.carrier.frequency() + self.sideband_frequency()

    def _set_carrier_frequency(self, val):
        self.frequency._save_val(val + self.sideband_frequency())

    def check_settings(self):
        check_carrier_sidebanding_status(self.carrier)
        if self.sequencer._template_element is None:
            warn("No template element uploaded to sequencer.")
