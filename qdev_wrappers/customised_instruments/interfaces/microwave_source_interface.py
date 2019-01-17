from qcodes.instrument.base import Instrument
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateParameter
from qcodes.utils.helpers import create_on_off_val_mapping
import qcodes.utils.validators as vals


class _MicrowaveSourceInterface(Instrument):
    """
    Interface for a microwave source with basic set of parameters. This
    is probably too tied to the SGS100A and could be stripped down a bit,
    Let's do that if/when we start using something different that needs
    it. In the meantime it makes simulation easier.
    """
    def __init__(self, name, IQ_option=True):
        super().__init__(name)
        self._IQ_option = IQ_option
        self.add_parameter(name='frequency',
                           label='Frequency',
                           unit='Hz',
                           parameter_class=DelegateParameter)
        self.add_parameter(name='power',
                           label='Power',
                           unit='dBm',
                           parameter_class=DelegateParameter)
        self.add_parameter(name='status',
                           label='Status',
                           parameter_class=DelegateParameter)
        self.add_parameter(name='pulsemod_state',
                           label='Pulse Modulation State',
                           parameter_class=DelegateParameter)
        self.add_parameter(name='IQ_state',
                           label='IQ State',
                           parameter_class=DelegateParameter)
        if not IQ_option:
            self.IQ_state._latest['raw_value'] = 0
            self.IQ_state.set_allowed = False

    def to_default(self):
        """
        Sets the instrument to some relatively arbitrary but hopefully
        harmless defaults:
        - frequency: 6e9
        - power: -10
        - status: 0
        - pulsemod_state: 0
        - IQ_state: 0
        """
        self.frequency(6e9)
        self.power(-10)
        self.status(0)
        self.pulsemod_state(0)
        if self._IQ_option:
            self.IQ_state(0)


class SGS100AMicrowaveSourceInterface(_MicrowaveSourceInterface):
    """
    Interface with real SGS100A microwave source.
    """
    def __init__(self, name, microwave_source, IQ_option=True):
        super().__init__(name, IQ_option=IQ_option)
        self.frequency.source = self.microwave_source.frequency
        self.power.source = self.microwave_source.power
        self.status.source = self.microwave_source.status
        self.pulsemod_state.source = self.microwave_source.pulsemod_state
        self.IQ_state.source = self.microwave_source.IQ_state


class SimulatedMicrowaveSourceInterface(_MicrowaveSourceInterface):
    """
    Simulated interface version of the microwave source. The val
    mapping and vals are set such that any status parameters
    can be set with reasonable on/off values which are mapped to
    1/0 to be saved and mapped back to True/False as on SGS100A.
    """
    def __init__(self, name, IQ_option=True):
        super().__init__(name, IQ_option=IQ_option)
        valmappingdict = create_on_off_val_mapping(on_val=1, off_val=0)
        inversevalmappingdict = {v: k for k, v in valmappingdict.items()}
        self.status.vals = vals.Enum(*valmappingdict.keys())
        self.status.val_mapping = valmappingdict
        self.status.inverse_val_mapping = inversevalmappingdict
        self.pulsemod_state.vals = vals.Enum(*valmappingdict.keys())
        self.pulsemod_state.val_mapping = valmappingdict
        self.pulsemod_state.inverse_val_mapping = inversevalmappingdict
        self.IQ_state.vals = vals.Enum(*valmappingdict.keys())
        self.IQ_state.val_mapping = valmappingdict
        self.IQ_state.inverse_val_mapping = inversevalmappingdict
