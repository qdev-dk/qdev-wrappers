from qcodes.instrument.base import Instrument
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateParameter
from qcodes.utils.helpers import create_on_off_val_mapping
import qcodes.utils.validators as vals

# TODO: add dual output param
# TODO: add dual output param limit warning

class MicrowaveSourceInterface(Instrument):
    """
    Interface for a microwave source with basic set of parameters. This
    is probably too tied to the SGS100A and could be stripped down a bit,
    Let's do that if/when we start using something different that needs
    it. In the meantime it makes simulation easier.
    """
    def __init__(self, name: str, IQ: bool=True, dual_output: bool=False):
        super().__init__(name)
        self._IQ_option = IQ
        self._dual_output_option = dual_output
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
                           parameter_class=DelegateParameter,
                           docstring='On/off status indicates whether output '
                                     'status is modulated by another signal '
                                     '(usually input to trigger channel)')
        self.add_parameter(name='IQ_state',
                           label='IQ State',
                           val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
                           parameter_class=DelegateParameter,
                           docstring='On/off status indicates whether output '
                                     'I and Q is modulated by another signal '
                                     '(usually input to IQ channels)')
        self.add_parameter(name='dual_output_state',
                           label='Dual Output State',
                           val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
                           parameter_class=DelegateParameter,
                           docstring='On/off status indicates whether output '
                                     'from trig out port is on')
        if not IQ:
            self.IQ_state._latest['raw_value'] = 0
            self.IQ_state.set_allowed = False
        if not dual_output:
            self.dual_output_state._latest['raw_value'] = 0
            self.dual_output_state.set_allowed = False


class SGS100AMicrowaveSourceInterface(MicrowaveSourceInterface):
    """
    Interface with real SGS100A microwave source.
    """
    def __init__(self, name: str, microwave_source_name: str,
                 IQ: bool=True, dual_output: bool=False,
                 external_mixer=False):
        super().__init__(name, IQ=IQ, dual_output=dual_output)
        if IQ and external_mixer:
            raise RuntimeError('IQ option AND external_mixer not valid')
        microwave_source = Instrument.find_instrument(microwave_source_name)
        self.microwave_source = microwave_source
        self.frequency.source = microwave_source.frequency
        self.power.source = microwave_source.power
        self.status.source = microwave_source.status
        self.pulsemod_state.source = microwave_source.pulsemod_state
        if dual_output:
            valmappingdict = create_on_off_val_mapping(on_val='LO', off_val='OFF')
            self.dual_output_state.source = microwave_source.ref_LO_out
            self.dual_output.val_mapping = valmappingdict
            inversevalmappingdict = {v: k for k, v in valmappingdict.items()}
            self.dual_output_state.inverse_val_mapping = inversevalmappingdict
        if IQ:
            self.IQ_state.source = microwave_source.IQ_state
        elif external_mixer:
            self.IQ_state._latest['raw_value'] = 1


class SimulatedMicrowaveSourceInterface(MicrowaveSourceInterface):
    """
    Simulated interface version of the microwave source. The val
    mapping and vals are set such that any status parameters
    can be set with reasonable on/off values which are mapped to
    1/0 to be saved and mapped back to True/False as on SGS100A.
    """
    def __init__(self, name: str, IQ: bool=True, dual_output: bool=False):
        super().__init__(name, IQ=IQ,
                         dual_output=dual_output)
        valmappingdict = create_on_off_val_mapping(on_val=1, off_val=0)
        inversevalmappingdict = {v: k for k, v in valmappingdict.items()}
        self.frequency(7e9)
        self.power(-10)
        self.status.vals = vals.Enum(*valmappingdict.keys())
        self.status.val_mapping = valmappingdict
        self.status.inverse_val_mapping = inversevalmappingdict
        self.status(0)
        self.pulsemod_state.vals = vals.Enum(*valmappingdict.keys())
        self.pulsemod_state.val_mapping = valmappingdict
        self.pulsemod_state.inverse_val_mapping = inversevalmappingdict
        self.pulsemod_state(0)
        self.IQ_state.inverse_val_mapping = inversevalmappingdict
        if self.IQ_state.set_allowed:
            self.IQ_state.vals = vals.Enum(*valmappingdict.keys())
            self.IQ_state.val_mapping = valmappingdict
            self.IQ_state(0)
        self.dual_output_state.inverse_val_mapping = inversevalmappingdict
        if self.dual_output_state.set_allowed:
            self.dual_output_state.vals = vals.Enum(*valmappingdict.keys())
            self.dual_output_state.val_mapping = valmappingdict
            self.dual_output_state(0)
