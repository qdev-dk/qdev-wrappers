from qcodes.instrument.base import Instrument
from qdev_wrappers.customised_instruments.interfaces.interface_parameter import InterfaceParameter


class MicrowaveSourceInterface(Instrument):
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


class SGS100AMicrowaveSourceInterface(MicrowaveSourceInterface):
    def __init__(self, name, microwave_source):
        super().__init__(name)
        self.frequency.source = self.microwave_source.frequency
        self.power.source = self.microwave_source.power
        self.status.source = self.microwave_source.status
        self.IQ_state.source = self.microwave_source.IQ_state
        self.pulsemod_state.source = self.microwave_source.pulsemod_state


class SimulatedMicrowaveSourceInterface(MicrowaveSourceInterface):
    def __init__(self, name):
        super().__init__(name)
