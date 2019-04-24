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
        self._carrier = carrier
        self._sequencer = sequencer
        self._pulse_building_prepend = pulse_building_prepend

        self.add_parameter(
            name='frequency',
            set_cmd=self._set_frequency,
            get_cmd=self._get_frequency,
            docstring='Setting updates sideband to generate required'
            ' frequency, getting calculates resultant sidebanded frequency')
        self.add_parameter(
            name='carrier_power',
            source=carrier.power,
            parameter_class=DelegateParameter)
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
        self.frequency._save_val(self._carrier.frequency())
        self.sideband_frequency._save_val(0)


    def check_carrier_status(self):
        if not self.status():
            warn('Sidebander carrier status is off')
        if isinstance(self._carrier, MicrowaveSourceInterface):
            if not self._carrier.IQ_state():
                warn('Sidebander carrier IQ state is off')
        elif 'sidebanded' not in self._carrier.mode():
            warn('Sidebander carrier mode indicates not sidebanded')

    def change_sequence(self, **kwargs):
        s_context = self.generate_context()
        s_context.update(kwargs.pop('context', {}))
        self._sequencer.change_sequence(context=s_context, **kwargs)
        self.sync_parameters()
        self.check_carrier_status()

    @contextmanager
    def single_upload(self):
        with self._sequencer.no_upload():
            yield
        self._sequencer._upload_sequence()


    def sync_parameters(self):
        inner = self._sequencer.inner_setpoints
        outer = self._sequencer.outer_setpoints
        for setpoints in [inner, outer]:
            try:
                if setpoints.symbol in self.pulse_building_parameters:
                    param = self.pulse_building_parameters[setpoints.symbol]
                    self._sequencer.repeat.parameters[setpoints.symbol](param())
            except AttributeError as e:
                pass

    def to_default(self):
        self._sequencer.sequence_mode('element')
        self._sequencer.repetition_mode('inf')
        self.status(1)
        if isinstance(self._carrier, MicrowaveSourceInterface):
            self._carrier.IQ_state(1)
        else:
            self._carrier.mode('sidebanded')

    # Parameter getters and setters
    def _set_frequency(self, val):
        new_sideband = val - self._carrier.frequency()
        self.sideband_frequency(new_sideband)

    def _get_frequency(self):
        return self._carrier.frequency() + self.sideband_frequency()

    def _set_status(self, val):
        if str(val).upper() in ['1', 'TRUE', 'ON']:
            self._sequencer.run()
            self._carrier.status(0)
            self.check_carrier_status()
        else:
            self._sequencer.stop()
            self._carrier.status(0)

    def _set_sideband(self, val):
        self.frequency._save_val(self._carrier.frequency() + val)

    def _set_carrier_frequency(self, val):
        self.frequency._save_val(val + self.sideband_frequency())

    # Properties
    @property
    def pulse_building_parameters(self):
        param_dict = {n: p for n, p in self.parameters.items() if
                      isinstance(p, PulseBuildingParameter)}
        return param_dict

    # Private methods
    def generate_context(self):
        return {param.symbol_name: param() for param in
                self.pulse_building_parameters.values()}
