from qcodes.instrument.base import Instrument
from qcodes import ManualParameter
from qcodes.utils import validators as vals


# TODO: name help pleaaase!
class LockIn(Instrument):
    """
    This driver is a wrapper used to set two SGS100A microwave sources
    for use as part of a lock in amplifier together with an Alazar
    acquisition card and assumingthe physical setup including mixing
    and a low pass filter.
    """

    def __init__(self, cavity=None, localos=None,
                 pwa=None, demodulation_frequency=None):
        self._cavity = cavity
        self._localos = localos
        self._pwa = pwa
        self.add_parameter(name='frequency',
                           set_cmd=self._set_drive_frequency,
                           get_cmd=self._cavity.frequency,
                           vals=vals.Numbers(1e6, 20e9))
        self.add_parameter(name='demodulation_frequency',
                           set_cmd=self._set_demod_frequency,
                           parameter_class=ManualParameter,
                           initial_value=demodulation_frequency,
                           vals=vals.Numbers(1e6, 200e6))
        self.add_parameter(name='status',
                           set_cmd=self._set_status,
                           get_cmd=self._get_status)
        self.add_parameter(name='ref_osc_source',
                           set_cmd=self._set_ref_osc_source,
                           vals=vals.Enum('INT', 'EXT'))
        self.add_parameter(name='ref_osc_external_freq',
                           set_cmd=self._set_ref_osc_extermal_freq,
                           vals=vals.Enum('10MHz', '100MHz', '1000MHz'))

        if demodulation_frequency is not None:
            self._set_demod_frequency(demodulation_frequency)
        # TODO: is this a horrible way to achieve this?
        self.power = self._cavity.power
        self.localos_power = self.localos.power
        self.IQ_state = self._cavity.IQ_state
        self.pulsemod_state = self._cavity.pulsemod_state
        self.pulsemod_source = self._cavity.pulsemod_source

    def _set_ref_osc_source(self, ref_osc_source):
        self._cavity.ref_osc_source(ref_osc_source)
        self._localos.ref_osc_source(ref_osc_source)

    def _set_ref_osc_extermal_freq(self, ref_osc_external_freq):
        self._cavity.ref_osc_external_freq(ref_osc_external_freq)
        self._localos.ref_osc_external_freq(ref_osc_external_freq)

    def _set_status(self, status):
        if status in [True, 1, 'on']:
            self._cavity.status('on')
            self._localos.status('on')
        elif status in [False, 0, 'off']:
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
        self._pwa.set_demod_freq(frequency)

    # TODO: pulsemod source
    def reset(self):
        self._cavity.reset()
        self._localos.reset()
        self.IQ_state('on')
        # self._localos.pulsemod_source('')
        # self.pulsemod_source('')
        self.pulsemod_state('off')
        self._localos.pulsemod_state('off')
        self.ref_osc_source('EXT')
        self.ref_osc_external_freq('10MHz')
        self.status(True)

    def on(self):
        self.status(True)

    def off(self):
        self.status(False)
