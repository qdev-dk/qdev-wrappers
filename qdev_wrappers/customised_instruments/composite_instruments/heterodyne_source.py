from qcodes.instrument.base import Instrument
from qcodes.utils import validators as vals
import os
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateParameter


class _HeterodyneSource(Instrument):
    """
    Virtual instrument that represents a heterodyne source outputting at
    two frequencies with one intended for mixing up and the other for mixing
    down. These frequencies are separated by a 'demodulation_frequncy' which
    can be tuned in some cases (fixed to 0 for single miscorwave source
    implementation). The status of both tones and the powers and frequency of
    the mixing up tone can be adjusted. It can be made up
    either of a single microwave source with sidebanding and dual output or
    by two microwave sources. Modes are for extended use where one source
    might be sidebanded, modulated, switched off etc and options depend
    on the implementation.
    """

    def __init__(self, name):
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
                           label='Demodulation Signal Power',
                           unit='dBm',
                           parameter_class=DelegateParameter)
        self.add_parameter(name='status',
                           label='Status',
                           parameter_class=DelegateParameter)
        self.add_parameter(name='mode',
                           label='Mode',
                           parameter_class=DelegateParameter,
                           vals=vals.Enum('basic', 'sidebanded', 'sidebanded_modulated'))


class OneSourceHeterodyneSource(_HeterodyneSource):
    """
    Implementation using one microwave source which has two outputs
    at the same frequency. As a result the localos_power cannot be set
    and depends on the power and the demodulation is fixed at 0.
    Available modes are 'basic', 'sidebanded', and 'sideband_modulated'.
    """

    def __init__(self, name, microwave_source_if, localos_power=10):
        self._microwave_source_if = microwave_source_if
        super().__init__(name)
        self.frequency.source = microwave_source_if.frequency
        self.power.source = microwave_source_if.power
        self.demodulation_frequency.set_allowed = False
        self.demodulation_frequency._save_val(0)
        self.localos_power.set_allowed = False
        self.localos_power.get_fn = lambda: localos_power  # TODO
        self.status.source = microwave_source_if.status
        self.mode.set_fn = self._set_mode
        mode_docstring = ("Sets the configuration of the carrier source: /n "
                          "basic - IQ off, pulsemod off /n sidebanded - "
                          "IQ on, pulsemod off /n sidebanded_modulated - "
                          "IQ on, pulsemod on.")
        self.mode.__doc__ = os.linesep.join(
            (mode_docstring, '', self.mode.__doc__))
        if (microwave_source_if.pulsemod_state() and
                microwave_source_if.IQ_state()):
            self.mode._save_val('sideband_modulated')
        elif (microwave_source_if.pulsemod_state()):
            self.mode._save_val('sidebanded')
        else:
            self.mode._save_val('basic')

    def _set_mode(self, val):
        if val == 'basic':
            self._microwave_source_if.IQ_state(0)
            self._microwave_source_if.pulsemod_state(0)
        elif val == 'sidebanded':
            self._microwave_source_if.IQ_state(1)
            self._microwave_source_if.pulsemod_state(0)
        elif val == 'sidebanded_modulated':
            self._microwave_source_if.IQ_state(1)
            self._microwave_source_if.pulsemod_state(1)


class TwoSourceHeterodyneSource(_HeterodyneSource):
    """
    Implementation using two microwave sources.
    Available modes are 'basic', 'sidebanded_basic', 'sidebanded'
    and 'sideband_modulated'.
    """

    def __init__(self, name, carrier_source_if, localos_source_if):
        self._carrier_source_if = carrier_source_if
        self._localos_source_if = localos_source_if
        super().__init__(name)
        self.frequency.source = carrier_source_if.frequency
        self.frequency.set_fn = self._set_carrier_frequency
        self.power.source = carrier_source_if.power
        self.demodulation_frequency.set_fn = self._set_base_demod_frequency
        self.demodulation_frequency.get_fn = self._get_base_demod_frequency
        self.localos_power.source = localos_source_if.power
        self.status.source = carrier_source_if.status
        self.status.set_fn = self._set_status
        self.mode.set_fn = self._set_mode
        mode_docstring = ("Sets the configuration of the carrier and "
                          "localos sources: /n basic - localos off, IQ off,"
                          " pulsemod off /n "
                          "sidebanded - localos on, IQ on, "
                          "pulsemod off /n sidebanded_modulated - "
                          "localos on, IQ on, pulsemod on.")
        self.mode.__doc__ = os.linesep.join(
            (mode_docstring, '', self.mode.__doc__))
        self.status._save_val(carrier_source_if.status())
        if (carrier_source_if.IQ_state() and
                carrier_source_if.pulsemod_state()):
            self.mode._save_val('sidebanded_modulated')
        elif carrier_source_if.IQ_state():
            self.mode._save_val('sidebanded')
        else:
            localos_source_if.status(0)
            self.mode._save_val('basic')
        localos_source_if.pulsemod_state(0)

    def _set_carrier_frequency(self, val):
        self._localos_source_if.frequency(
            val + self.demodulation_frequency())

    def _set_base_demod_frequency(self, val):
        self._localos_source_if.frequency(
            self._carrier_source_if.frequency() + val)

    def _get_base_demod_frequency(self):
        return (self._localos_source_if.frequency() -
                self._carrier_source_if.frequency())

    def _set_status(self, val):
        if self.mode() in ['sidebanded', 'sidebanded_modulated']:
            self._localos_source_if.status(val)

    def _set_mode(self, val):
        status = self.status()
        if val == 'basic':
            self._localos_source_if.status(0)
            self._carrier_source_if.IQ_state(0)
            self._carrier_source_if.pulsemod_state(0)
        elif val == 'sidebanded':
            self._localos_source_if.status(status)
            self._carrier_source_if.IQ_state(1)
            self._carrier_source_if.pulsemod_state(0)
        elif val == 'sidebanded_modulated':
            self._localos_source_if.status(status)
            self._carrier_source_if.IQ_state(1)
            self._carrier_source_if.pulsemod_state(1)


"""
Simulated version.
"""
SimulatedHeterodyneSource = _HeterodyneSource
