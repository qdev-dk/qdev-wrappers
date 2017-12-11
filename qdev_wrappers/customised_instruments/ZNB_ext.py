<<<<<<< HEAD
from qcodes.instrument_drivers.rohde_schwarz.ZNB import ZNB, FrequencySweep, ZNBChannel
=======
import numpy as np

# QCoDeS imports
from qcodes.instrument_drivers.rohde_schwarz.ZNB import (FrequencySweep, ZNB,
                                                         ZNBChannel)

>>>>>>> a4339af... right inheritance

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
            channel=n,
            parameter_class=FrequencySweepMagSetCav)


class VNA_ext(ZNB):

    CHANNEL_CLASS = ZNBChannel_ext
