import numpy as np
from qcodes import ArrayParameter


class Scope_avg(ArrayParameter):

    def __init__(self, name, channel=1, **kwargs):

        super().__init__(name, shape=(1,), **kwargs)
        self.has_setpoints = False
        self.zi = self._instrument

        if channel not in [1, 2]:
            raise ValueError('Channel must be 1 or 2')

        self.channel = channel

    def make_setpoints(self, sp_start, sp_stop, sp_npts):
        """
        Makes setpoints and prepares the averager (updates its unit)
        """
        self.shape = (sp_npts,)
        self.unit = self._instrument.Scope.units[self.channel - 1]
        self.setpoints = (tuple(np.linspace(sp_start, sp_stop, sp_npts)),)
        self.has_setpoints = True

    def get(self):

        if not self.has_setpoints:
            raise ValueError('Setpoints not made. Run make_setpoints')

        data = self._instrument.Scope.get()[self.channel - 1]
        data_avg = np.mean(data, 0)

        # KDP: handle less than 4096 points
        # (4096 needs to be multiple of number of points)
        down_samp = np.int(self._instrument.scope_length.get() / self.shape[0])
        if down_samp > 1:
            data_ret = data_avg[::down_samp]
        else:
            data_ret = data_avg

        return data_ret
