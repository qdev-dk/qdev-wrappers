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


def to_sidebanding_default(carrier, sequencer):
    sequencer.sequence_mode('element')
    sequencer.repetition_mode('inf')
    carrier.status(1)
    if isinstance(carrier, MicrowaveSourceInterface):
        carrier.IQ_state(1)
    else:
        carrier.mode('sidebanded')


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
            set_fn=self._set_sideband,
            parameter_class=PulseBuildingParameter,
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

    @contextmanager
    def single_upload(self):
        with self.sequencer.no_upload():
            yield
        self.sequencer._upload_sequence()

    def change_sequence(self, **kwargs):
        s_context = self.generate_context()
        s_context.update(kwargs.pop('context', {}))
        self.sequencer.change_sequence(context=s_context, **kwargs)
        self.sync_parameters(self)
        check_carrier_sidebanding_status(self.carrier)

    def sync_parameters(self):
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

    def to_sidebanding_default(self):
        to_sidebanding_default(self.carrier, self.sequencer)

    # Parameter getters and setters
    def _set_frequency(self, val):
        new_sideband = val - self.carrier.frequency()
        self.sideband_frequency(new_sideband)

    def _get_frequency(self):
        return self.carrier.frequency() + self.sideband_frequency()

    def _set_sideband(self, val):
        self.frequency._save_val(self.carrier.frequency() + val)

    def _set_carrier_frequency(self, val):
        self.frequency._save_val(val + self.sideband_frequency())

    # Properties
    @property
    def pulse_building_parameters(self):
        param_dict = {p.symbol_name: p for p in self.parameters.values() if
                      isinstance(p, PulseBuildingParameter)}
        return param_dict

    # Private methods
    def generate_context(self):
        return {p: v() for p, v in self.pulse_building_parameters.items()}
