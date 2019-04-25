from typing import Union, Optional
from contextlib import contextmanager
from qcodes.instrument.base import Instrument
import qcodes.utils.validators as vals
from qcodes.utils.helpers import create_on_off_val_mapping
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateParameter
from qdev_wrappers.customised_instruments.composite_instruments.sidebander.sidebander import check_carrier_sidebanding_status, Sidebander, to_sidebanding_default
from qdev_wrappers.customised_instruments.composite_instruments.parametric_sequencer.parametric_sequencer import ParametricSequencer
from qdev_wrappers.customised_instruments.interfaces.microwave_source_interface import MicrowaveSourceInterface
from qdev_wrappers.customised_instruments.composite_instruments.heterodyne_source.heterodyne_source import HeterodyneSource

# TODO: docstrings

class Multiplexer(Instrument):
    def __init__(self, name: str,
                 sequencer: ParametricSequencer,
                 carrier: Union[MicrowaveSourceInterface, HeterodyneSource],
                 **kwargs):
        super().__init__(name, **kwargs)
        self.carrier = carrier
        self.sequencer = sequencer
        self.add_parameter(
            name='carrier_power',
            source=carrier.power,
            parameter_class=DelegateParameter)
        self.add_parameter(
            name='carrier_frequency',
            set_fn=self._set_carrier_frequency,
            source=carrier.frequency,
            parameter_class=DelegateParameter)
        self.add_parameter(
            name='carrier_status',
            source=carrier.status,
            parameter_class=DelegateParameter)

    def _set_carrier_frequency(self, val):
        for s in self.sidebanders:
            s.frequency._save_val(val + s.sideband_frequency())

    def generate_context(self):
        context = {}
        for s in self.sidebanders:
            context.update(s.generate_context())
        return context

    def add_sidebander(self):
        ch_num = len(self.sidebanders)
        name = '{}{}'.format(self.name, ch_num)
        sidebander = Sidebander(name, self.sequencer, self.carrier,
                                pulse_building_prepend=True)
        sidebander.carrier_frequency.set_allowed = False
        self.add_submodule(name, sidebander)
        return sidebander

    def clear_sidebanders(self):
        for n, s in self.submodules.items():
            if isinstance(s, Sidebander):
                del self.submodules[n]

    def change_sequence(self, **kwargs):
        context = self.generate_context()
        context.update(kwargs.pop('context', {}))
        self.sequencer.change_sequence(context=context, **kwargs)
        for s in self.sidebanders:
            s.sync_parameters()
        check_carrier_sidebanding_status(self.carrier)

    def to_default(self):
        to_sidebanding_default(self.carrier, self.sequencer)

    @contextmanager
    def single_upload(self):
        with self.sequencer.no_upload():
            yield
        self.sequencer._upload_sequence()

    @property
    def sidebanders(self):
        return [s for s in self.submodules.values() if isinstance(s, Sidebander)]
