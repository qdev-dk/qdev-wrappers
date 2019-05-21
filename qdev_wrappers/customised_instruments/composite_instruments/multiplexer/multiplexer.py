from typing import Union, Optional
from contextlib import contextmanager
from qcodes.instrument.base import Instrument
from qcodes.instrument.channel import InstrumentChannel, ChannelList
import qcodes.utils.validators as vals
from qcodes.utils.helpers import create_on_off_val_mapping
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateParameter
from qdev_wrappers.customised_instruments.composite_instruments.sidebander.sidebander import check_carrier_sidebanding_status, Sidebander,SequenceManager
from qdev_wrappers.customised_instruments.composite_instruments.parametric_sequencer.parametric_sequencer import ParametricSequencer
from qdev_wrappers.customised_instruments.interfaces.microwave_source_interface import MicrowaveSourceInterface
from qdev_wrappers.customised_instruments.composite_instruments.heterodyne_source.heterodyne_source import HeterodyneSource

# TODO: does carrier_power and carrier_status as delegate params actually add anything?

class SidebanderChannel(InstrumentChannel, Sidebander):
    def __init__(self, parent: Instrument, name: str,
                 sequencer: ParametricSequencer,
                 carrier: Union[MicrowaveSourceInterface, HeterodyneSource],
                 **kwargs):
        super().__init__(parent=parent, name=name, sequencer=sequencer,
                         carrier=carrier, pulse_building_prepend=True,
                         **kwargs)


class Multiplexer(Instrument, SequenceManager):
    SIDEBANDER_CLASS = SidebanderChannel

    def __init__(self, name: str,
                 sequencer: ParametricSequencer,
                 carrier: Union[MicrowaveSourceInterface, HeterodyneSource],
                 **kwargs):
        super().__init__(name, **kwargs)
        self.carrier = carrier
        self.sequencer = sequencer
        self._pulse_building_prepend = False
        self._sequencer_up_to_date = False
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
        sidebanders = ChannelList(
            self, 'sidebanders', SidebanderChannel)
        self.add_submodule('sidebanders', sidebanders)

    def _set_carrier_frequency(self, val):
        for s in self.sidebanders:
            s.frequency._save_val(val + s.sideband_frequency())

    def add_sidebander(self, name=None):
        if name is None:
            ch_num = len(self.sidebanders)
            name = '{}{}'.format(self.name, ch_num)
        sidebander = self.SIDEBANDER_CLASS(
            self, name, self.sequencer, self.carrier)
        sidebander.carrier_frequency.set_allowed = False
        self.add_submodule(name, sidebander)
        self.sidebanders.append(sidebander)
        return sidebander
