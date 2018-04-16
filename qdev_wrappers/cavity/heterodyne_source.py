from qcodes.instrument.base import Instrument
from qcodes import ManualParameter
from qcodes.utils import validators as vals
import logging
from qdev_wrappers.parameters import DelegateParameter

# TODO: name help pleaaase!
class HeterodyneSource(Instrument):
    """
    This driver is a wrapper used to set two SGS100A microwave sources
    for use as part of a lock in amplifier together with an Alazar
    acquisition card and assumingthe physical setup including mixing
    and a low pass filter.
    """

    def __init__(self, name, cavity=None, localos=None, pwa=None, demodulation_frequency=None):
        self._cavity = cavity
        self._localos = localos
        if cavity is None or localos is None:
            raise RuntimeError('must initialise with mocrowave sources for cavity and local oscillator')
        super().__init__(name)

        self._pwa = pwa
        self.add_parameter(name='frequency',
                           set_cmd=self._set_drive_frequency,
                           get_cmd=self._cavity.frequency,
                           vals=vals.Numbers(1e6, 20e9))
        self.add_parameter(name='demodulation_frequency',
                           set_cmd=self._set_demod_frequency,
                           initial_value=demodulation_frequency,
                           vals=vals.Numbers(1e6, 200e6))
        self.add_parameter(name='status',
                           set_cmd=self._set_status,
                           get_cmd=self._get_status)
        self.add_parameter(name='ref_osc_source',
                           set_cmd=self._set_ref_osc_source,
                           get_cmd=self._get_ref_osc_source,
                           vals=vals.Enum('INT', 'EXT'))
        self.add_parameter(name='ref_osc_external_freq',
                           set_cmd=self._set_ref_osc_external_freq,
                           get_cmd=self._get_ref_osc_external_freq,
                           vals=vals.Enum('10MHz', '100MHz', '1000MHz'))
        self.add_parameter(name='power',
                           parameter_class=DelegateParameter,
                           source=self._cavity.power)
        self.add_parameter(name='localos_power',
                           parameter_class=DelegateParameter,
                           source=self._localos.power)
        self.add_parameter(name='IQ_state',
                   parameter_class=DelegateParameter,
                   source=self._cavity.IQ_state)
        self.add_parameter(name='pulsemod_state',
           parameter_class=DelegateParameter,
           source=self._cavity.pulsemod_state)
        self.add_parameter(name='pulsemod_source',
           parameter_class=DelegateParameter,
           source=self._cavity.pulsemod_source)

    def _set_ref_osc_source(self, ref_osc_source):
        self._cavity.ref_osc_source(ref_osc_source)
        self._localos.ref_osc_source(ref_osc_source)

    def _get_ref_osc_source(self):
        cav_source = self._cavity.ref_osc_source()
        lo_source = self._localos.ref_osc_source()
        if cav_source == lo_source:
            return cav_source
        else:
            logging.warning(
                'cavity and local oscillator do not have the '
                'same reference source: {}, {}'.format(cav_source, lo_source))


    def _set_ref_osc_external_freq(self, ref_osc_external_freq):
        self._cavity.ref_osc_external_freq(ref_osc_external_freq)
        self._localos.ref_osc_external_freq(ref_osc_external_freq)

    def _get_ref_osc_external_freq(self):
        cav_source_freq = self._cavity.ref_osc_external_freq()
        lo_source_freq = self._localos.ref_osc_external_freq()
        if cav_source_freq == lo_source_freq:
            return cav_source_freq
        else:
            logging.warning(
                'cavity and local oscillator do not have the '
                'same reference source frequency: {}, {}'.format(cav_source_freq, lo_source_freq))

    def _set_status(self, status):
        if str(status).upper() in ['TRUE', '1', 'ON']:
            self._cavity.status('on')
            self._localos.status('on')
        elif str(status).upper() in ['FALSE', '0', 'OFF']:
            self._cavity.status('off')
            self._localos.status('off')
        else:
            raise ValueError('status must be bool, 1, 0, "on" or "off"')

    def _get_status(self):
        return self._cavity.status() == 'On' and self._localos.status() == 'On'

    def _set_drive_frequency(self, frequency):
        self._cavity.frequency(frequency)
        self._localos.frequency(frequency + self.demodulation_frequency())

    def _set_demod_frequency(self, frequency):
        self._localos.frequency(self._cavity.frequency() + frequency)
        if self._pwa is not None:
            self._pwa.set_demod_freq(frequency)
        else:
            logging.warning(
                'Attempt to set demodulation frequency on heterodyne readout setup'
                'without setting demodulation frequency for software demodulation.')

    # TODO: pulsemod source
    def reset(self):
        self._cavity.reset()
        self._localos.reset()
        self._cavity.IQ_state('on')
        self._localos.IQ_state('off')
        self._localos.pulsemod_source('INT')
        self._cavity.pulsemod_source('INT')
        self._cavity.pulsemod_state('off')
        self._localos.pulsemod_state('off')
        self.ref_osc_source('EXT')
        self.ref_osc_external_freq('10MHz')
        self.status(True)

    def on(self):
        self.status(True)

    def off(self):
        self.status(False)
