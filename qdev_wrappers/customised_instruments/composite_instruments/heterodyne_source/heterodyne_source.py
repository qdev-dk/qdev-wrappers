from qcodes.instrument.base import Instrument
from qcodes.utils.helpers import create_on_off_val_mapping
from warnings import warn
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateParameter

# TODO: should HeterodyneSource be private?


class HeterodyneSource(Instrument):
    """
    Virtual instrument that represents a heterodyne source outputting at
    two frequencies with one intended for mixing up and the other for mixing
    down. These frequencies are separated by a 'demodulation_frequncy' which
    can be tuned in some cases (fixed to 0 for single miscorwave source
    implementation). The state of both tones and the powers and frequency of
    the mixing up tone can be adjusted. It can be made up
    either of a single microwave source with sidebanding and dual output or
    by two microwave sources.
    """

    def __init__(self, name: str):
        super().__init__(name)
        self.add_parameter(name='frequency',
                           label='Carrier Frequency',
                           unit='Hz',
                           parameter_class=DelegateParameter)
        self.add_parameter(name='power',
                           label='Carrier Power',
                           unit='dBm',
                           parameter_class=DelegateParameter)
        self.add_parameter(name='demodulation_frequency',
                           label='Base Demodulation Frequency',
                           unit='Hz',
                           parameter_class=DelegateParameter)
        self.add_parameter(name='localos_power',
                           label='Local Oscillator Power',
                           unit='dBm',
                           parameter_class=DelegateParameter)
        self.add_parameter(name='state',
                           val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
                           parameter_class=DelegateParameter)
        self.add_parameter(name='pulse_modulation_state',
                           val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
                           parameter_class=DelegateParameter)
        self.add_parameter(name='IQ_modulation_state',
                           val_mapping=create_on_off_val_mapping(on_val=1, off_val=0),
                           parameter_class=DelegateParameter)

    def check_settings(self):
        raise NotImplementedError


class OneSourceHeterodyneSource(HeterodyneSource):
    """
    Implementation using one microwave source which outputs an IQ modulated
    signal and the local oscillator. As a result the localos_power cannot be set
    and depends on the power and the demodulation is fixed at 0.
    """
    def __init__(self, name: str,
                 microwave_source_if_name: str,
                 localos_power: float=10):
        source_if = Instrument.find_instrument(microwave_source_if_name)
        self.source = source_if
        if source_if._LO_output == 0:
            raise RuntimeError(
                'Cannot use single microwave source as heterodyne source '
                'if LO_output not allowed')
        if source_if._IQ_modulation == 0:
            raise RuntimeError(
                'Cannot use single microwave source as heterodyne source '
                'without IQ_option.')
        super().__init__(name)
        self.frequency.source = source_if.frequency
        self.power.source = source_if.power
        self.demodulation_frequency.set_allowed = False
        self.demodulation_frequency._save_val(0)
        self.localos_power.set_allowed = False
        self.localos_power.get_fn = lambda: localos_power
        self.state.source = source_if.state
        self.pulse_modulation_state.source = source_if.pulse_modulation_state
        self.IQ_modulation_state.source = source_if.IQ_modulation_state

    def check_settings(self):
        if not self.IQ_modulation_state():
            warn('IQ modulation of single source heterodyne source is off')
        if not self.source.LO_output_state():
            warn('LO output state of single source heterodyne source is off')


class TwoSourceHeterodyneSource(HeterodyneSource):
    """
    Implementation using two microwave sources.
    """

    def __init__(self, name: str, carrier_source_if_name: str,
                 localos_source_if_name: str):
        carrier_source_if = Instrument.find_instrument(carrier_source_if_name)
        localos_source_if = Instrument.find_instrument(localos_source_if_name)
        self.carrier_source = carrier_source_if
        self.localos_source = localos_source_if
        super().__init__(name)
        self.frequency.source = carrier_source_if.frequency
        self.frequency.set_fn = self._set_carrier_frequency
        self.power.source = carrier_source_if.power
        self.demodulation_frequency.set_fn = self._set_base_demod_frequency
        self.demodulation_frequency.get_fn = self._get_base_demod_frequency
        self.localos_power.source = localos_source_if.power
        self.state.source = carrier_source_if.state
        self.state.set_fn = self._set_state
        self.pulse_modulation_state.source = self.carrier_source.pulse_modulation_state
        self.IQ_modulation_state.source = self.carrier_source.IQ_modulation_state

    def _set_carrier_frequency(self, val):
        self.localos_source.frequency(
            val + self.demodulation_frequency())

    def _set_base_demod_frequency(self, val):
        self.localos_source.frequency(
            self.carrier_source.frequency() + val)

    def _get_base_demod_frequency(self):
        return (self.localos_source.frequency() -
                self.carrier_source.frequency())

    def _set_state(self, val):
            self.localos_source.state(val)

    def check_settings(self):
        if self.localos_source.pulse_modulation_state():
            warn('localos source of heterodyne source has '
                 'pulse_modulation_state on')


class SimulatedHeterodyneSource(HeterodyneSource):
    """
    Simulated version.
    """
    def __init__(self, name):
        super().__init__(name)
        self.frequency(7e9)
        self.power(-10)
        self.demodulation_frequency(0)
        self.localos_power(10)
        self.state(0)
        self.pulse_modulation_state(0)
        self.IQ_modulation_state(1)

    def check_settings(self):
        pass
