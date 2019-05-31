from qcodes.instrument.base import Instrument
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateParameter
from qcodes.utils.helpers import create_on_off_val_mapping
from typing import Optional

# TODO: add dual output param limit warning

class MicrowaveSourceInterface(Instrument):
    """
    Interface for a microwave source with basic set of parameters. This
    is probably too tied to the SGS100A and could be stripped down a bit,
    Let's do that if/when we start using something different that needs
    it. In the meantime it makes simulation easier.
    """
    def __init__(self, name: str,
                 pulse_modulation: Optional[bool]=None,
                 IQ_modulation: Optional[bool]=None,
                 LO_output: Optional[bool]=None):
        super().__init__(name)
        self._pulse_modulation = pulse_modulation
        self._IQ_modulation = IQ_modulation
        self._LO_output = LO_output
        self.add_parameter(name='frequency',
                           label='Frequency',
                           unit='Hz',
                           parameter_class=DelegateParameter)
        self.add_parameter(name='power',
                           label='Power',
                           unit='dBm',
                           parameter_class=DelegateParameter)
        self.add_parameter(name='state',
                           label='State',
                           val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
                           parameter_class=DelegateParameter)
        self.add_parameter(name='pulse_modulation_state',
                           label='Pulse Modulation State',
                           val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
                           parameter_class=DelegateParameter,
                           docstring='On/off state indicates whether output '
                                     'state is modulated by another signal')
        self.add_parameter(name='IQ_modulation_state',
                           label='IQ modulation State',
                           val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
                           parameter_class=DelegateParameter,
                           docstring='On/off state indicates whether output '
                                     'I and Q is modulated by another signal')
        self.add_parameter(name='LO_output_state',
                           label='Local Oscillator Output State',
                           val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
                           parameter_class=DelegateParameter,
                           docstring='On/off state indicates whether  '
                                     'from trig out port is on')
        if pulse_modulation is not None:
            self.pulse_modulation_state._latest['raw_value'] = int(pulse_modulation)
            self.pulse_modulation_state.set_allowed = False
        if IQ_modulation is not None:
            self.IQ_modulation_state._latest['raw_value'] = int(IQ_modulation)
            self.IQ_modulation_state.set_allowed = False
        if LO_output != 0 and IQ_modulation == 0:
            raise RuntimeError(
                'Cannot create microwave source instance with no IQ '
                'modulation which outputs the local oscillator tone, '
                'change IQ_modulation or LO_output')
        elif LO_output is not None:
            self.LO_output_state._latest['raw_value'] = int(LO_output)
            self.LO_output_state.set_allowed = False


class SGS100AMicrowaveSourceInterface(MicrowaveSourceInterface):
    """
    Interface with real SGS100A microwave source.
    """
    def __init__(self, name: str, microwave_source_name: str,
                 IQ_modulation: Optional[bool]=None,
                 pulse_modulation: Optional[bool]=None,
                 LO_output: Optional[bool]=None):
        super().__init__(name,
                         IQ_modulation=IQ_modulation,
                         pulse_modulation=pulse_modulation,
                         LO_output=LO_output)
        microwave_source = Instrument.find_instrument(microwave_source_name)
        self.microwave_source = microwave_source
        self.frequency.source = microwave_source.frequency
        self.power.source = microwave_source.power
        self.state.source = microwave_source.status
        self.pulse_modulation_state.source = microwave_source.pulsemod_state
        self.IQ_modulation_state.source = microwave_source.IQ_state
        if LO_output is None:
            valmappingdict = create_on_off_val_mapping(on_val='LO', off_val='OFF')
            self.LO_output_state.source = microwave_source.ref_LO_out
            self.LO_output_state.val_mapping = valmappingdict
            inversevalmappingdict = {v: k for k, v in valmappingdict.items()}
            self.LO_output_state.inverse_val_mapping = inversevalmappingdict

class SimulatedMicrowaveSourceInterface(MicrowaveSourceInterface):
    """
    Simulated interface version of the microwave source which initialises
    with defaults.
    """
    def __init__(self, name: str,
                 IQ_modulation: Optional[bool]=None,
                 pulse_modulation: Optional[bool]=None,
                 LO_output: Optional[bool]=None):
        super().__init__(name,
                         IQ_modulation=IQ_modulation,
                         pulse_modulation=pulse_modulation,
                         LO_output=LO_output)
        self.frequency(7e9)
        self.power(-10)
        self.state(0)
        if pulse_modulation is None:
            self.pulse_modulation_state(0)
        if IQ_modulation is None:
            self.IQ_modulation_state(0)
        if LO_output is None:
            self.LO_output_state(0)
