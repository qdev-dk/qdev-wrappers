from qcodes.instrument.base import Instrument
import numpy as np

class SphereCor(Instrument):
    '''
    Class to form spherical coordinates out of 3 input parameters in cartesian coordiantes.
    '''
    def __init__(self, name, paramX, paramY, paramZ, **kwargs):
        super().__init__(name, **kwargs)

        self.paramX = paramX
        self.paramY = paramY
        self.paramZ = paramZ

        # Get current values
        self.rtp_get()

        self.add_parameter('radius',
                            get_cmd=self._get_r,
                            set_cmd=self._set_r,
                            get_parser=float,
                            label = 'radius',
                            unit='')
        self.add_parameter('theta',
                            get_cmd=self._get_theta,
                            set_cmd=self._set_theta,
                            get_parser=float,
                            label = 'theta',
                            unit='degree')
        self.add_parameter('phi',
                            get_cmd=self._get_phi,
                            set_cmd=self._set_phi,
                            get_parser=float,
                            label = 'phi',
                            unit='degree')

    def rtp_get(self):
        x = self.paramX()
        y = self.paramY()
        z = self.paramZ()
        sphere = self._carttosphere([x , y , z])
        self._radius, self._theta, self._phi = sphere
        return sphere

    def rtp_set(self, sphere):
        x, y, z = self._spheretocart(sphere)
        self._radius, self._theta, self._phi = sphere
        self.paramX(x)
        self.paramY(y)
        self.paramZ(z)

    def _get_r(self):
        self.rtp_get()
        return self._radius

    def _set_r(self, val):
        self._radius = val
        self.rtp_set([self._radius, self._theta, self._phi])

    def _get_theta(self):
        self.rtp_get()
        return self._theta

    def _set_theta(self, val):
        self._theta = val
        self.rtp_set([self._radius, self._theta, self._phi])

    def _get_phi(self):
        self.rtp_get()
        return self._phi

    def _set_phi(self, val):
        self._phi = val
        self.rtp_set([self._radius, self._theta, self._phi])

    def _spheretocart(self, sphere):
        """
        r,  theta,  phi = sphere
        """
        r,  theta,  phi = sphere
        theta = theta*np.pi/180
        phi = phi*np.pi/180
        x = (r * np.sin(theta) * np.cos(phi))
        y = (r * np.sin(theta) * np.sin(phi))
        z = (r * np.cos(theta))
        return [x,  y,  z]

    def _carttosphere(self, cartesian):
        x, y, z = cartesian
        r = np.sqrt(x**2 + y**2 + z**2)
        if r < 1e-6:
            theta = 0
            phi = 0
        else:
            theta = np.arccos(z / r)*180/np.pi
            phi = np.arctan2(y,  x)*180/np.pi
            if phi<0:
                phi = phi+360
        return [r, theta, phi]