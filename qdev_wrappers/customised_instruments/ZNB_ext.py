import time
from functools import partial
import numpy as np

# QCoDeS imports
from qcodes.instrument_drivers.rohde_schwarz.ZNB import (FrequencySweep, ZNB,
                                                         ZNBChannel)
from qcodes.utils import validators as vals


class FrequencySweepMagSetCav(FrequencySweep):
    FORMAT = 'dB'

    def get(self):
        # this could also be set here instead of checking
        if self._instrument.format() != self.FORMAT:
            raise RuntimeError('Channel format must be set to {} first'.format(
                self.FORMAT))
        mag_array = super().get()

        ind = np.argmax(mag_array)
        f = tuple(
            np.linspace(
                int(self._instrument.start()),
                int(self._instrument.stop()),
                num=self._instrument.npts()))
        freadout = f[ind] + 0.7e6

        self._instrument._parent.readout_freq(freadout)
        return mag_array


class ZNBChannel_ext(ZNBChannel):
    def __init__(self, parent, name, channel):
        super().__init__(parent, name, channel)

        self.add_parameter(
            name='trace_mag_SetCav',
            start=self.start(),
            stop=self.stop(),
            npts=self.npts(),
            channel=self._instrument_channel,
            parameter_class=FrequencySweepMagSetCav)


class VNA_ext(ZNB):
    CHANNEL_CLASS = ZNBChannel_ext

    # spectroscopy

    # override Base class
    def add_channel(self, vna_parameter: str):
        super().add_channel(vna_parameter)
        i_channel = len(self.channels) + 1
        self.write('SOUR{}:FREQ1:CONV:ARB:IFR 1, 1, 0, SWE'.format(i_channel))
        self.write('SOUR{}:FREQ2:CONV:ARB:IFR 1, 1, 0, SWE'.format(i_channel))
        self.write('SOUR{}:POW1:OFFS 0, CPAD'.format(i_channel))
        self.write('SOUR{}:POW2:OFFS 0, CPAD'.format(i_channel))
        self.write('SOUR{}:POW1:PERM OFF'.format(i_channel))
        self.write('SOUR{}:POW:GEN1:PERM OFF'.format(i_channel))
        self.write('SOUR{}:POW:GEN1:STAT OFF'.format(i_channel))
        self.write('SOUR{}:POW2:STAT ON'.format(i_channel))

    def count_external_generators(self):
        num = self.ask('SYST:COMM:RDEV:GEN:COUN?').strip()
        return int(num)

    def set_external_generator(self,
                               address,
                               gen=1,
                               gen_name="ext gen 1",
                               driver="SGS100A",
                               interface="VXI-11"):
        self.write(
            'SYST:COMM:RDEV:GEN{:.0f}:DEF "{}", "{}", "{}",  "{}", OFF, ON'.
            format(gen, gen_name, driver, interface, address))

    def get_external_generator_setup(self, num=1):
        setup = self.ask(
            'SYSTem:COMMunicate:RDEVice:GEN{:.0f}:DEF?'.format(num)).strip()
        return setup

    def clear_external_generator(self, num=1):
        self.write('SYST:COMM:RDEV:GEN{:.0f}:DEL'.format(num))

    def get_external_generator_numbers(self):
        cat = self.ask('SYST:COMM:RDEV:GEN1:CAT?').strip()
        return cat

    def add_spectroscopy_channel(self,
                                 generator_address,
                                 vna_parameter="B2G1SAM"):
        """
        Adds a generator and uses it to generate a fixed frequency tone, the
        response at this frequency is read out at port 2 which is also set to
        be fixed freq. Port 1 is set as the port for sweeping etc"""
        self.set_external_generator(generator_address)
        self.add_channel(vna_parameter)
        chan_num = len(self.channels)
        self.write('SOUR{}:POW2:STAT OFF'.format(chan_num))
        time.sleep(0.2)
        self.write('SOUR{}:POW:GEN1:PERM ON'.format(chan_num))
        time.sleep(0.2)
        self.write('SOUR{}:POW1:PERM ON'.format(chan_num))
        time.sleep(0.2)
        self.write('SOUR{}:POW:GEN1:STAT ON'.format(chan_num))
        time.sleep(0.2)
        self.write('ROSC EXT')
        self.add_parameter(
            'readout_freq',
            unit='Hz',
            set_cmd=partial(self._set_readout_freq, chan_num),
            get_cmd=partial(self._get_readout_freq, chan_num),
            get_parser=float,
            vals=vals.Numbers(self._min_freq, self._max_freq))
        self.add_parameter(
            'readout_power',
            unit='dBm',
            set_cmd=partial(self._set_readout_pow, chan_num),
            get_cmd=partial(self._get_readout_pow, chan_num),
            get_parser=float,
            vals=vals.Numbers(-150, 25))

    def _set_readout_freq(self, chan_num, freq):
        self.write('SOUR{}:FREQ:CONV:ARB:EFR1 ON, 0, 1, {:.6f}, CW'.format(
            chan_num, freq))
        self.write('SOUR{}:FREQ2:CONV:ARB:IFR 0, 1, {:.6f}, CW'.format(
            chan_num, freq))

    def _get_readout_freq(self, chan_num):
        return self.ask(
            'SOUR{}:FREQ:CONV:ARB:EFR1?'.format(chan_num)).split(',')[3]

    def _set_readout_pow(self, chan_num, pow):
        self.write('SOUR{}:POW:GEN1:OFFS {:.3f}, ONLY'.format(chan_num, pow))
        self.write('SOUR{}:POW2:OFFS {:.3f}, ONLY'.format(chan_num, pow))

    def _get_readout_pow(self, chan_num):
        return self.ask('SOUR{}:POW:GEN1:OFFS?'.format(chan_num)).split(',')[0]
