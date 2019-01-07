from qcodes.instrument.base import Instrument
from qdev_wrappers.customised_instruments.interfaces.interface_parameter import InterfaceParameter
from qcodes.utils.helpers import create_on_off_val_mapping
import qcodes.utils.validators as vals


class _MicrowaveSourceInterface(Instrument):
    """
    Interface for a microwave source with basic set of parameters. This
    is probably too tied to the SGS100A and could be stripped down a bit,
    Let's do that if/when we start using something different that needs
    it. In the meantime it makes simulation easier
    """
    def __init__(self, name):
        super().__init__(name)
        self.add_parameter(name='frequency',
                           label='Frequency',
                           unit='Hz',
                           parameter_class=InterfaceParameter)
        self.add_parameter(name='power',
                           label='Power',
                           unit='dBm',
                           parameter_class=InterfaceParameter)
        self.add_parameter(name='status',
                           label='Status',
                           parameter_class=InterfaceParameter)
        self.add_parameter(name='IQ_state',
                           label='IQ State',
                           parameter_class=InterfaceParameter)
        self.add_parameter(name='pulsemod_state',
                           label='Pulse Modulation State',
                           parameter_class=InterfaceParameter)


class SGS100AMicrowaveSourceInterface(_MicrowaveSourceInterface):
    """
    Interface with real SGS100A microwave source.
    """
    def __init__(self, name, microwave_source):
        super().__init__(name)
        self.frequency.source = self.microwave_source.frequency
        self.power.source = self.microwave_source.power
        self.status.source = self.microwave_source.status
        self.IQ_state.source = self.microwave_source.IQ_state
        self.pulsemod_state.source = self.microwave_source.pulsemod_state


class SimulatedMicrowaveSourceInterface(_MicrowaveSourceInterface):
    """
    Simulated interface version of the microwave source.
    """
    def __init__(self, name):
        super().__init__(name)
        valmappingdict = create_on_off_val_mapping(on_val=1, off_val=0)
        self.status.vals = vals.Enum(*valmappingdict.keys())
        self.IQ_state.vals = vals.Enum(*valmappingdict.keys())
        self.pulsemod_state.vals = vals.Enum(*valmappingdict.keys())
        self.status.val_mapping = valmappingdict
        self.IQ_state.val_mapping = valmappingdict
        self.pulsemod_state.val_mapping = valmappingdict
        inversevalmappingdict = {v: k for k, v in valmappingdict.items()}
        self.status.inverse_val_mapping = inversevalmappingdict
        self.IQ_state.inverse_val_mapping = inversevalmappingdict
        self.pulsemod_state.inverse_val_mapping = inversevalmappingdict
