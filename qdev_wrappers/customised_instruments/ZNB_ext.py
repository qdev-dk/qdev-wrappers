import logging
import time
from functools import partial

# QCoDeS imports
from qcodes.instrument_drivers.rohde_schwarz.ZNB import ZNB, ZNBChannel
from qcodes.utils import validators as vals

log = logging.getLogger(__name__)


class ZNBChannel_ext(ZNBChannel):
    def __init__(self, parent, name, channel, vna_parameter: str=None):
        super().__init__(parent, name, channel, vna_parameter=vna_parameter)

        if self.vna_parameter() == 'B2G1SAM':
            self.add_parameter(
                'readout_freq',
                label='Readout frequency',
                unit='Hz',
                set_cmd=partial(self._set_readout_freq, self._instrument_channel),
                get_cmd=partial(self._get_readout_freq, self._instrument_channel),
                get_parser=float)
            self.add_parameter(
                'readout_power',
                label='Readout power',
                unit='dBm',
                set_cmd=partial(self._set_readout_pow, self._instrument_channel),
                get_cmd=partial(self._get_readout_pow, self._instrument_channel),
                get_parser=int,
                vals=vals.Numbers(-150, 25))

    def _set_readout_freq(self, channel, freq):
        self.write('SOUR{}:FREQ:CONV:ARB:EFR1 ON, 0, 1, {:.7f}, '
                   'CW'.format(channel, freq))
        self.write('SOUR{}:FREQ2:CONV:ARB:IFR 0, 1, {:.7f},'
                   'CW'.format(channel, freq))

    def _get_readout_freq(self, channel):
        return self.ask(
            'SOUR{}:FREQ:CONV:ARB:EFR1?'.format(channel)).split(',')[3]

    def _set_readout_pow(self, channel, pow):
        self.write('SOUR{}:POW:GEN1:OFFS {:.3f}, ONLY'.format(channel, pow))
        self.write('SOUR{}:POW2:OFFS {:.3f}, ONLY'.format(channel, pow))

    def _get_readout_pow(self, channel):
        return self.ask('SOUR{}:POW:GEN1:OFFS?'.format(channel)).split(',')[0]

    # this is a quick and dirty work around to get scaling of the plot
    # in mod 3 powers
    def _set_format(self, val):
        super()._set_format(val)
        if val == 'MLIN\n':
            self.trace.unit = 'V'


class ZNB_ext(ZNB):

    CHANNEL_CLASS = ZNBChannel_ext
    WRITE_DELAY = 0.1

    def __init__(self,
                 name,
                 visa_address,
                 S21=True,
                 spec_mode=False,
                 gen_address=None,
                 timeout=40):
        super().__init__(
            name, visa_address, init_s_params=False, timeout=timeout)

        if S21:
            self.add_channel(channel_name='S21')
            self.channels.autoscale()
        if spec_mode:
            if gen_address is not None:
                self.add_spectroscopy_channel(gen_address)
                self.channels.autoscale()
            else:
                log.warning('spec mode not added as ' +
                            'no generator ip address provided')


    # spectroscopy
    # override Base class
    def add_channel(self, channel_name: str, **kwargs):
        super().add_channel(channel_name, **kwargs)
        i_channel = len(self.channels)
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
        self.write('SYST:COMM:RDEV:GEN{:.0f}:DEF "{}", "{}", "{}",  "{}", '
                   'OFF, ON'.format(gen, gen_name, driver, interface, address))

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
                                 channel_name='SPEC',
                                 vna_parameter='B2G1SAM',
                                 readout_freq=6e9,
                                 readout_power=-60):
        """
        Adds a generator and uses it to generate a fixed frequency tone, the
        response at this frequency is read out at port 2 which is also set to
        be fixed freq. Port 1 is set as the port for sweeping etc"""
        self.set_external_generator(generator_address)
        self.add_channel(channel_name,vna_parameter=vna_parameter)
        new_channel = getattr(self, channel_name)
        chan_num = len(self.channels)
        self.write('SOUR{}:POW2:STAT OFF'.format(chan_num))
        self.write('SOUR{}:POW:GEN1:PERM ON'.format(chan_num))
        self.write('SOUR{}:POW1:PERM ON'.format(chan_num))
        self.write('SOUR{}:POW:GEN1:STAT ON'.format(chan_num))
        self.write('ROSC EXT')
        for n in range(chan_num):
            if 'G1' not in self.channels[n].vna_parameter():
                self.write('SOUR{}:POW:GEN1:STAT Off'.format(n+1))

        # setting default values
        new_channel.readout_freq(readout_freq)
        new_channel.readout_power(readout_power)

    def write(self, *args, **kwargs):
        time.sleep(self.WRITE_DELAY)
        super().write(*args, **kwargs)
