from qcodes.instrument.base import Instrument
from qcodes.utils.helpers import create_on_off_val_mapping
from qcodes.utils import validators as vals
import os
from warnings import warn
from qdev_wrappers.customised_instruments.parameters.delegate_parameters import DelegateParameter
from qdev_wrappers.customised_instruments.interfaces.microwave_source_interface import MicrowaveSourceInterface

# TODO: should HeterodyneSource be private?


class HeterodyneSource(Instrument):
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
                           label='Demodulation Signal Power',
                           unit='dBm',
                           parameter_class=DelegateParameter)
        self.add_parameter(name='status',
                           label='Status',
                           parameter_class=DelegateParameter)
        self.add_parameter(name='mode',
                           label='Mode',
                           parameter_class=DelegateParameter,
                           vals=vals.Enum('basic', 'modulated', 'sidebanded',
                                          'sidebanded_modulated'))
        self.check_settings()

    def check_settings(self):
        raise NotImplementedError


class OneSourceHeterodyneSource(HeterodyneSource):
    """
    Implementation using one microwave source which has two outputs
    at the same frequency. As a result the localos_power cannot be set
    and depends on the power and the demodulation is fixed at 0.
    Available modes are 'basic', 'sidebanded', and 'sideband_modulated'.
    """

    def __init__(self, name: str,
                 microwave_source_if: MicrowaveSourceInterface,
                 localos_power: float=10):
        if not microwave_source_if._dual_output_option:
            raise RuntimeError(
                'Cannot use single microwave source as heterodyne source '
                'if dual_output_option not present')
        if not microwave_source_if._IQ_option:
            raise RuntimeError(
                'Cannot use single microwave source as heterodyne source '
                'without IQ_option.')
        if not microwave_source_if.IQ_state.set_allowed:
            self.mode.set_fn = self._set_mode_wo_IQ
        else:
            self.mode.set_fn = self._set_mode_w_IQ
        self._microwave_source_if = microwave_source_if
        super().__init__(name)
        self.frequency.source = microwave_source_if.frequency
        self.power.source = microwave_source_if.power
        self.demodulation_frequency.set_allowed = False
        self.demodulation_frequency._save_val(0)
        self.localos_power.set_allowed = False
        self.localos_power.get_fn = lambda: localos_power
        self.status.source = microwave_source_if.status
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

    def _set_mode_wo_IQ(self, val):
        status = self._microwave_source_if.status()
        if val == 'basic':
            warn('Basic mode set for heterodyne source with external mixer'
                 ': IQ_state cannot be turned off')
            self._microwave_source_if.pulsemod_state(0)
            self._microwave_source_if.dual_output_state(0)
        elif val == 'sidebanded':
            self._microwave_source_if.pulsemod_state(0)
            self._microwave_source_if.dual_output_state(status)
        elif val == 'modulated':
            self._microwave_source_if.pulsemod_state(1)
            self._microwave_source_if.dual_output_state(status)
        elif val == 'sidebanded_modulated':
            self._microwave_source_if.pulsemod_state(1)
            self._microwave_source_if.dual_output_state(status)

    def _set_mode_w_IQ(self, val):
        status = self._microwave_source_if.status()
        if val == 'basic':
            self._microwave_source_if.IQ_state(0)
            self._microwave_source_if.pulsemod_state(0)
            self._microwave_source_if.dual_output_state(0)
        elif val == 'sidebanded':
            self._microwave_source_if.IQ_state(1)
            self._microwave_source_if.pulsemod_state(0)
            self._microwave_source_if.dual_output_state(status)
        elif val == 'modulated':
            self._microwave_source_if.IQ_state(0)
            self._microwave_source_if.pulsemod_state(1)
            self._microwave_source_if.dual_output_state(status)
        elif val == 'sidebanded_modulated':
            self._microwave_source_if.IQ_state(1)
            self._microwave_source_if.pulsemod_state(1)
            self._microwave_source_if.dual_output_state(status)

    def check_settings(self):
        if not self._microwave_source_if.dual_output_state():
            warn('dual_output_state of single microwave source heterodyne '
                 'source is not on.')


class TwoSourceHeterodyneSource(HeterodyneSource):
    """
    Implementation using two microwave sources.
    Available modes are 'basic', 'sidebanded_basic', 'sidebanded'
    and 'sideband_modulated'.
    """

    def __init__(self, name: str, carrier_source_if: MicrowaveSourceInterface,
                 localos_source_if: MicrowaveSourceInterface):
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
        if carrier_source_if._IQ_option:
            self.mode.set_fn = self._set_mode_w_IQ
        else:
            self.mode.set_fn = self._set_mode_wo_IQ
            self.mode.vals = vals.Enum('basic', 'modulated')
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
        elif carrier_source_if.pulsemod_state():
            self.mode._save_val('modulated')
        elif not localos_source_if.status():
            self.mode._save_val('basic')
        else:
            self.mode._save_val('basic')
            warn('heterodyne source in "basic" mode but local_os '
                 'source is on')

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

    def _set_mode_wo_IQ(self, val):
        status = self._carrier_source_if.status()
        if val == 'basic':
            self._localos_source_if.status(0)
            self._carrier_source_if.pulsemod_state(0)
        elif val == 'modulated':
            self._localos_source_if.status(status)
            self._carrier_source_if.pulsemod_state(1)

    def _set_mode_w_IQ(self, val):
        status = self._carrier_source_if.status()
        if val == 'basic':
            self._localos_source_if.status(0)
            self._carrier_source_if.IQ_state(0)
            self._carrier_source_if.pulsemod_state(0)
        elif val == 'modulated':
            self._localos_source_if.status(status)
            self._carrier_source_if.IQ_state(0)
            self._carrier_source_if.pulsemod_state(1)
        elif val == 'sidebanded':
            self._localos_source_if.status(status)
            self._carrier_source_if.IQ_state(1)
            self._carrier_source_if.pulsemod_state(0)
        elif val == 'sidebanded_modulated':
            self._localos_source_if.status(status)
            self._carrier_source_if.IQ_state(1)
            self._carrier_source_if.pulsemod_state(1)

    def check_settings(self):
        if self._localos_source_if.pulsemod_state():
            warn('localos_source_if of heterodyne source has '
                 'pulsemod_state on')


class SimulatedHeterodyneSource(HeterodyneSource):
    """
    Simulated version.
    """

    def __init__(self, name):
        super().__init__(name)
        valmappingdict = create_on_off_val_mapping(on_val=1, off_val=0)
        inversevalmappingdict = {v: k for k, v in valmappingdict.items()}
        self.frequency(7e9)
        self.power(-10)
        self.demodulation_frequency(0)
        self.localos_power(10)
        self.status.vals = vals.Enum(*valmappingdict.keys())
        self.status.val_mapping = valmappingdict
        self.status.inverse_val_mapping = inversevalmappingdict
        self.status(0)
        self.mode('basic')

    def check_settings(self):
        pass
