from qcodes.instrument.base import Instrument
from qcodes.utils import validators as vals
import os
from qdev_wrappers.customised_instruments.interfaces.parameters import InterfaceParameter


# TODO: validators, docstrings


class HeterodyneSource(Instrument):
    def __init__(self, name):
        super().__init__(name)
        self.add_parameter(name='frequency',
                           label='Carrier Frequency',
                           unit='Hz',
                           parameter_class=InterfaceParameter)
        self.add_parameter(name='power',
                           label='Carrier Power',
                           unit='dBm',
                           parameter_class=InterfaceParameter)
        self.add_parameter(name='demodulation_frequency',
                           label='Base Demodulation Frequency',
                           unit='Hz',
                           parameter_class=InterfaceParameter)
        self.add_parameter(name='localos_power',
                           label='Demodulation Signal Power',
                           unit='dBm',
                           parameter_class=InterfaceParameter)
        self.add_parameter(name='status',
                           label='Status',
                           parameter_class=InterfaceParameter)
        self.add_parameter(name='mode',
                           label='Mode',
                           parameter_class=InterfaceParameter)


class OneSourceHeterodyneSource(HeterodyneSource):
    def __init__(self, name, microwave_source_interface):
        self._microwave_source_interface = microwave_source_interface
        super().__init__(name)
        self.frequency._source = microwave_source_interface.frequency
        self.power._source = microwave_source_interface.power
        self.demodulation_frequency._set_fn = False
        self.demodulation_frequency._save_val(0)
        self.localos_power._set_fn = False
        self.localos_power._get_fn = microwave_source_interface.power.get  # TODO
        self.status._source = microwave_source_interface.status
        self.mode._set_fn = self._set_mode
        self.mode.vals = vals.Enum('basic', 'sideband', 'sideband_modulated')
        mode_docstring = ("Sets the configuration of the carrier source: /n "
                          "basic - IQ off, pulsemod off /n sidebanded - "
                          "IQ on, pulsemod off /n sidebanded_modulated - "
                          "IQ on, pulsemod on.")
        self.mode.__doc__ = os.linesep.join(
            (mode_docstring, '', self.mode.__doc__))

    def _set_mode(self, val):
        if val == 'basic':
            self._microwave_source_interface.IQ_state(0)
            self._microwave_source_interface.pulsemod_state(0)
        elif val == 'sidebanded':
            self._microwave_source_interface.IQ_state(1)
            self._microwave_source_interface.pulsemod_state(0)
        elif val == 'sidebanded_modulated':
            self._microwave_source_interface.IQ_state(1)
            self._microwave_source_interface.pulsemod_state(1)


class TwoSourceHeterodyneSource(HeterodyneSource):
    def __init__(self, name, carrier_source_interface, localos_source_interface):
        self._carrier_source_interface = carrier_source_interface
        self._localos_source_interface = localos_source_interface
        super().__init__(name)
        self.frequency._set_fn = self._set_carrier_frequency
        self.frequency._get_fn = carrier_source_interface.frequency.get
        self.power._source = carrier_source_interface.power
        self.demodulation_frequency._set_fn = self._set_base_demod_frequency
        self.demodulation_frequency._get_fn = self._get_base_demod_frequency
        self.localos_power._source = localos_source_interface.power
        self.status._set_fn = self._set_status
        self.status._get_fn = carrier_source_interface.status.get
        self.mode._set_fn = self._set_mode
        self.mode.vals = vals.Enum(
            'basic', 'sidebanded_basic', 'sideband', 'sideband_modulated')
        mode_docstring = ("Sets the configuration of the carrier and "
                          "localos sources: /n basic - localos off, IQ off,"
                          " pulsemod off /n sidebanded_basic - "
                          "localos off, IQ on, pulsemod off /n"
                          "sidebanded - localos on, IQ on, "
                          "pulsemod off /n sidebanded_modulated - "
                          "localos on, IQ on, pulsemod on.")
        self.mode.__doc__ = os.linesep.join(
            (mode_docstring, '', self.mode.__doc__))

    def _set_carrier_frequency(self, val):
        self._carrier_source_interface.frequency(val)
        self._localos_source_interface.frequency(
            val + self.demodulation_frequency())

    def _set_base_demod_frequency(self, val):
        self._localos_source_interface.frequency(
            self._carrier_source_interface.frequency() + val)

    def _get_base_demod_frequency(self):
        return (self._localos_source_interface.frequency() -
                self._carrier_source_interface.frequency())

    def _set_status(self, val):
        self._localos_source_interface.status(val)
        self._carrier_source_interface.status(val)

    def _set_mode(self, val):
        if val == 'basic':
            self._carrier_source_interface.status(1)
            self._localos_source_interface.status(0)
            self._carrier_source_interface.IQ_state(0)
            self._carrier_source_interface.pulsemod_state(0)
        elif val == 'sidebanded_basic':
            self._carrier_source_interface.status(1)
            self._localos_source_interface.status(0)
            self._carrier_source_interface.IQ_state(1)
            self._carrier_source_interface.pulsemod_state(0)
        elif val == 'sidebanded':
            self._carrier_source_interface.status(1)
            self._localos_source_interface.status(1)
            self._carrier_source_interface.IQ_state(1)
            self._carrier_source_interface.pulsemod_state(0)
        elif val == 'sidebanded_modulated':
            self._carrier_source_interface.status(1)
            self._localos_source_interface.status(1)
            self._carrier_source_interface.IQ_state(1)
            self._carrier_source_interface.pulsemod_state(1)


class SimulatedHeterodyneSource(HeterodyneSource):
    def __init__(name):
        super().__init__(name)
