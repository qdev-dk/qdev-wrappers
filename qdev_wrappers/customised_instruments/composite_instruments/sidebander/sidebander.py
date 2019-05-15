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


def sync_repeat_parameters(sequencer, params_dict):
    if sequencer.sequence_mode() == 'element':
        inner = sequencer.inner_setpoints
        outer = sequencer.outer_setpoints
        for setpoints in [i for i in [inner, outer] if i is not None]:
            if setpoints.symbol in params_dict:
                param = params_dict[setpoints.symbol]
                if setpoints.symbol in sequencer.repeat.parameters:
                    sequencer_param = sequencer.repeat.parameters[setpoints.symbol]
                    try:
                        sequencer_param.set(param())
                    except (RuntimeWarning, RuntimeError):
                        param._save_val(sequencer_param())
                        warn('Parameter {} could not be synced, value is now '
                             '{}'.format(setpoints.symbol, sequencer_param()))


class SidebandParam(PulseBuildingParameter):
    def set_raw(self, val):
        self.parent.frequency._save_val(self.carrier.frequency() + val)
        super().set_raw(val)


class Sidebander(Instrument):
    """
    An instrument which represents a sequencer and microwave drive where the
    sequencer is used to sideband the microwave drive.
    """

    def __init__(self, name: str,
                 sequencer: ParametricSequencer,
                 carrier: Union[MicrowaveSourceInterface, HeterodyneSource],
                 pulse_building_prepend: bool=False,
                 **kwargs):
        super().__init__(name, **kwargs)
        self.carrier = carrier
        self.sequencer = sequencer
        self._pulse_building_prepend = pulse_building_prepend
        self._sequencer_up_to_date = False

        self.add_parameter(
            name='frequency',
            set_cmd=self._set_frequency,
            get_cmd=self._get_frequency,
            docstring='Setting updates sideband to generate required'
            ' frequency, getting calculates resultant sidebanded frequency')
        self.add_parameter(
            name='carrier_frequency',
            set_fn=self._set_carrier_frequency,
            source=carrier.frequency,
            parameter_class=DelegateParameter)

        # pulse building parameters
        self.add_parameter(
            name='sideband_frequency',
            parameter_class=SidebandParam,
            docstring='Setting this also updates the frequency parameter')
        self.add_parameter(
            name='I_offset',
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='Q_offset',
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='gain_offset',
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='phase_offset',
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='amplitude',
            parameter_class=PulseBuildingParameter)
        self.add_parameter(
            name='status',
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

    def _set_frequency(self, val):
        new_sideband = val - self.carrier.frequency()
        self.sideband_frequency(new_sideband)

    def _get_frequency(self):
        return self.carrier.frequency() + self.sideband_frequency()

    def _set_carrier_frequency(self, val):
        self.frequency._save_val(val + self.sideband_frequency())

    # @contextmanager
    # def single_upload(self):
    #     with self.sequencer.no_upload():
    #         yield
    #     self.sequencer._upload_sequence()

    def change_sequence(self, **kwargs):
        context = self.generate_context()
        context.update(kwargs.pop('context', {}))
        original_do_upload_setting = self.sequencer._do_upload
        self.sequencer._do_upload = True
        self.sequencer.change_sequence(context=context, **kwargs)
        self._sequencer_up_to_date = True
        self.sequencer._do_upload = original_setting
        sync_repeat_parameters(self.sequencer, self.pulse_building_parameters)
        check_carrier_sidebanding_status(self.carrier)

    def update_sequence(self):
        if not self._sequencer_up_to_date:
                self.change_sequence()

    # Parameter getters and setters

    # Properties
    @property
    def pulse_building_parameters(self):
        param_dict = {p.symbol_name: p for p in self.parameters.values() if
                      isinstance(p, PulseBuildingParameter)}
        return param_dict

    def generate_context(self):
        context = {}
        labels = {}
        units = {}
        for p in self.pulse_building_parameters.values():
            context[p.symbol_name] = p()
            labels[p.symbol_name] = p.label
            units[p.symbol_name] = p.unit
        return {'context': context, 'labels': labels, 'units': units}
