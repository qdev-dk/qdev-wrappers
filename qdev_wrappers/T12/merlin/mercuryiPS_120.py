from functools import partial
import re
import time
import numpy as np
import collections

from qcodes.instrument.serial import SerialInstrument
from qcodes.utils.validators import Enum, Anything
from qcodes import MultiParameter


class MercuryiPSArray(MultiParameter):
    """
    This parameter holds the MercuryiPS's 3 dimensional parameters
    """
    def __init__(self, name, instrument, names, get_cmd, set_cmd, units=None, **kwargs):
        shapes = tuple(() for i in names)
        super().__init__(name, names, shapes, **kwargs)
        self._get = get_cmd
        self._set = set_cmd
        self._instrument = instrument
        self.units = units

    def get(self):
        try:
            value = self._get()
            self._save_val(value)
            return value
        except Exception as e:
            e.args = e.args + ('getting {}'.format(self.full_name),)
            raise e

    def set(self, setpoint):
        return self._set(setpoint)


class MercuryiPS_120(SerialInstrument):

    """
    This is the qcodes driver for the Oxford MercuryiPS magnet power supply.

    Args:
        name (str): name of the instrument
        address (str): The IP address or domain name of this instrument
        port (int): the IP port to communicate on (TODO: what port is normal?)

        axes (List[str], Optional): axes to support, as a list of uppercase
            characters, eg ``['X', 'Y', 'Z']``. If omitted, will ask the
            instrument what axes it supports.

    Status: beta-version.

    .. todo::

        - SAFETY!! we need to make sure the magnet is only ramped at certain
          conditions!
        - make ATOB a parameter, and move all possible to use
          _read_cmd, _write_cmd
        - this findall stuff in _get_cmd, is that smart?

    The driver is written as an IPInstrument, but it can likely be converted to
    ``VisaInstrument`` by removing the ``port`` arg and defining methods:

        - ``def _send(self, msg): self.visa_handle.write(msg)``
        - ``def _recv(self): return self.visa_handle.read()``

    """
    _mode_map_m = {"Amps, fast": 0,
                   "Tesla, fast": 1,
                   "Amps, slow": 4,
                   "Tesla, slow": 5}

    _mode_map_n = {"At rest": 0,
                   "Sweeping": 1,
                   "Sweep limiting": 2,
                   "Sweeping & sweep limiting": 3}

    _activity_map = {"HOLD": 0,
                     "RTOS": 1,
                     "RTOZ": 2,
                     "CLAMP": 4}

    _switch_heater_map = {"Off magnet at zero (switch closed)": 0,
                          "On (switch open)": 1,
                          "Off magnet at field (switch closed)": 2,
                          "Heater fault (heater is on but current is low)": 5,
                          "No switch fitted": 8}

    _remote_status_map = {"Local and locked": 0,
                          "Remote and locked": 1,
                          "Local and unlocked": 2,
                          "Remote and unlocked": 3,
                          "Auto-run-down": 4,
                          "Auto-run-down": 5,
                          "Auto-run-down": 6,
                          "Auto-run-down": 7}

    _system_status_map_m = {"Normal": 0,
                            "Quenched": 1,
                            "Over Heated": 2,
                            "Warming Up": 4,
                            "Fault": 8}

    _system_status_map_n = {"Normal": 0,
                            "On positive voltage limit": 1,
                            "On negative voltage limit": 2,
                            "Outside negative current limit": 4,
                            "Outside positive current limit": 8}

    _polarity_map_m = {"Desired: Positive, Magnet: Positive, Commanded: Positive": 0,
                       "Desired: Positive, Magnet: Positive, Commanded: Negative": 1,
                       "Desired: Positive, Magnet: Negative, Commanded: Positive": 2,
                       "Desired: Positive, Magnet: Negative, Commanded: Negative": 3,
                       "Desired: Negative, Magnet: Positive, Commanded: Positive": 4,
                       "Desired: Negative, Magnet: Positive, Commanded: Negative": 5,
                       "Desired: Negative, Magnet: Negative, Commanded: Positive": 6,
                       "Desired: Negative, Magnet: Negative, Commanded: Negative": 7}

    _polarity_map_n = {"Negative contactor closed": 1,
                       "Positive contactor closed": 2,
                       "Both contactors open": 3,
                       "Both contactors closed": 4}

    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, stopbits=2, terminator='\r', **kwargs)
        print(self.serial_handle.read_all())

        self.axes = 'xyz'

        self.axes_map = {'x': 3,
                         'y': 2,
                         'z': 1}

        self.amps_per_tesla = {'x': 57.901,
                               'y': 58.019,
                               'z': 18.21}

        self.add_parameter('setpoint',
                           names=tuple('B' + ax.lower() + '_setpoint' for ax in self.axes),
                           units=tuple('T' for ax in self.axes),
                           get_cmd=partial(self._do_magnet, self.axes, '_field_setpoint'),
                           set_cmd=partial(self._do_magnet, self.axes, '_field_setpoint'),
                           # vals=Anything(),
                           parameter_class=MercuryiPSArray)

        self.add_parameter('rate',
                           names=tuple('B' + ax.lower() + '_rate' for ax in self.axes),
                           units=tuple('T/m' for ax in self.axes),
                           get_cmd=partial(self._do_magnet, self.axes, '_field_rate'),
                           set_cmd=partial(self._do_magnet, self.axes, '_field_rate'),
                           # vals=Anything(),
                           parameter_class=MercuryiPSArray)

        self.add_parameter('field',
                           names=tuple('B'+ax.lower() for ax in self.axes),
                           units=tuple('T'for ax in self.axes),
                           get_cmd=partial(self._do_magnet, self.axes, '_field'),
                           set_cmd=partial(self._set_field, self.axes),
                           parameter_class=MercuryiPSArray)

        self.add_parameter(name='activity',
                           names=tuple(ax.lower()+'_activity' for ax in self.axes),
                           set_cmd=partial(self._do_magnet, self.axes, '_activity'),
                           get_cmd=partial(self._do_magnet, self.axes, '_activity'),
                           parameter_class=MercuryiPSArray)

        self.add_parameter(name='remote_status',
                           names=tuple(ax.lower()+'_remote_status' for ax in self.axes),
                           set_cmd=partial(self._do_magnet, self.axes, '_remote_status'),
                           get_cmd=partial(self._do_magnet, self.axes, '_remote_status'),
                           parameter_class=MercuryiPSArray)

        self.add_parameter('rtp',
                           names=['radius', 'theta', 'phi'],
                           get_cmd=partial(self._get_rtp,
                                           self.axes),
                           set_cmd=partial(self._set_rtp, self.axes),
                           units=['T', 'rad', 'rad'],
                           parameter_class=MercuryiPSArray)


        self.add_parameter('radius',
                           get_cmd=self._get_r,
                           set_cmd=self._set_r,
                           unit='T')
        self.add_parameter('theta',
                           get_cmd=self._get_theta,
                           set_cmd=self._set_theta,
                           unit='rad')
        self.add_parameter('phi',
                           get_cmd=self._get_phi,
                           set_cmd=self._set_phi,
                           unit='rad')

        for ax in self.axes:
            get_prefix = '@'+str(self.axes_map[ax])

            self.add_parameter(name=ax.lower()+'_status',
                               get_cmd=get_prefix+'X')

            self.add_parameter(name=ax.lower()+'_communication_protocol',
                               set_cmd=get_prefix+'Q{}',
                               val_mapping={
                                   'Normal': 0,
                                   'Normal LF': 2,
                                   'Extended resolution': 4,
                                   'Extended resolution LF': 6, })

            self.set(ax.lower()+'_communication_protocol',
                     'Extended resolution')

            self.add_parameter(name=ax.lower()+'_mode',
                               set_cmd=partial(
                                   self._ask_value, get_prefix+'M'),
                               get_cmd=partial(
                                   self._get_X, ax.lower(), 'mode_map_m'),
                               val_mapping=self._mode_map_m)

            self.add_parameter(name=ax.lower()+'_mode_m',
                               # set_cmd=get_prefix+'M{}',
                               get_cmd=partial(
                                   self._get_X, ax.lower(), 'mode_map_m'),
                               val_mapping=self._mode_map_m)

            self.add_parameter(name=ax.lower()+'_mode_n',
                               # set_cmd=get_prefix+'M{}',
                               get_cmd=partial(
                                   self._get_X, ax.lower(), 'mode_map_n'),
                               val_mapping=self._mode_map_n)

            self.add_parameter(name=ax.lower()+'_activity',
                               set_cmd=partial(
                                   self._ask_value, get_prefix+'A'),
                               get_cmd=partial(
                                   self._get_X, ax.lower(), 'activity_map'),
                               val_mapping=self._activity_map)

            self.add_parameter(name=ax.lower()+'_switch_heater',
                               set_cmd=partial(
                                   self._ask_value, get_prefix+'H'),
                               get_cmd=partial(
                                   self._get_X, ax.lower(), 'switch_heater_map'),
                               val_mapping=self._switch_heater_map)

            self.add_parameter(name=ax.lower()+'_remote_status',
                               set_cmd=partial(
                                   self._ask_value, get_prefix+'C'),
                               get_cmd=partial(
                                   self._get_X, ax.lower(), 'remote_status_map'),
                               val_mapping=self._remote_status_map)

            self.add_parameter(name=ax.lower()+'_system_status_m',
                               # set_cmd=get_prefix+'{}',
                               get_cmd=partial(
                                   self._get_X, ax.lower(), 'system_status_map_m'),
                               val_mapping=self._system_status_map_m)

            self.add_parameter(name=ax.lower()+'_system_status_n',
                               # set_cmd=get_prefix+'{}',
                               get_cmd=partial(
                                   self._get_X, ax.lower(), 'system_status_map_n'),
                               val_mapping=self._system_status_map_n)

            self.add_parameter(name=ax.lower()+'_polarity_m',
                               # set_cmd=get_prefix+'P{}',
                               get_cmd=partial(
                                   self._get_X, ax.lower(), 'polarity_map_m'),
                               val_mapping=self._polarity_map_m)

            self.add_parameter(name=ax.lower()+'_polarity_n',
                               # set_cmd=get_prefix+'P{}',
                               get_cmd=partial(
                                   self._get_X, ax.lower(), 'polarity_map_n'),
                               val_mapping=self._polarity_map_n)

            self.add_parameter(name=ax.lower()+'_current',
                               get_cmd=partial(
                                   self._ask_float, get_prefix+'R0'),
                               unit='A')

            self.add_parameter(name=ax.lower()+'_voltage',
                               get_cmd=partial(
                                   self._ask_float, get_prefix+'R1'),
                               unit='V')

            self.add_parameter(name=ax.lower()+'_current_measured',
                               get_cmd=partial(
                                   self._ask_float, get_prefix+'R2'),
                               unit='A')

            self.add_parameter(name=ax.lower()+'_current_setpoint',
                               get_cmd=partial(
                                   self._ask_float, get_prefix+'R5'),
                               set_cmd=partial(
                                   self._ask_value, get_prefix+'I'),  # % current
                               unit='A')

            self.add_parameter(name=ax.lower()+'_current_rate',
                               get_cmd=partial(
                                   self._ask_float, get_prefix+'R6'),
                               set_cmd=partial(
                                   self._ask_value, get_prefix+'S'),
                               unit='A/min')

            # Field mode
            self.add_parameter(name=ax.lower()+'_field',
                               get_cmd=partial(
                                   self._ask_float, get_prefix+'R7'),
                               set_cmd=partial(
                                   self._set_field, ax.lower()),
                               unit='T')

            self.add_parameter(name=ax.lower()+'_field_setpoint',
                               get_cmd=partial(
                                   self._ask_float, get_prefix+'R8'),
                               set_cmd=partial(
                                   self._ask_value, get_prefix+'J'),
                               unit='T')

            self.add_parameter(name=ax.lower()+'_field_rate',
                               get_cmd=partial(
                                   self._ask_float, get_prefix+'R9'),
                               set_cmd=partial(
                                   self._ask_value, get_prefix+'T'),
                               unit='T/min')

            # Not intended for the user *manual says so*
            # self.add_parameter(name=ax.lower()+'_DAC zero offset',
            #                    get_cmd=partial(self._ask_float, get_prefix+'R10'),
            #                    unit='A')

            # self.add_parameter(name=ax.lower()+'_Channel 1 freq./4',
            # get_cmd=partial(self._ask_float, get_prefix+'R11'))

            # self.add_parameter(name=ax.lower()+'_Channel 2 freq./4',
            # get_cmd=partial(self._ask_float, get_prefix+'R12'))

            # self.add_parameter(name=ax.lower()+'_Channel 3 freq./4',
            # get_cmd=partial(self._ask_float, get_prefix+'R13'))

            # self.add_parameter(name=ax.lower()+'_Software voltage limit',
            #                    get_cmd=partial(
            #                        self._ask_float, get_prefix+'R15'),
            #                    unit='V')

            # self.add_parameter(name=ax.lower()+'_Persistent magnet current',
            #                    get_cmd=partial(
            #                        self._ask_float, get_prefix+'R16'),
            #                    unit='A')

            # self.add_parameter(name=ax.lower()+'_Trip current',
            #                    get_cmd=partial(
            #                        self._ask_float, get_prefix+'R17'),
            #                    unit='A')

            # self.add_parameter(name=ax.lower()+'_Persistent magnet field',
            #                    get_cmd=partial(
            #                        self._ask_float, get_prefix+'R18'),
            #                    unit='T')

            # self.add_parameter(name=ax.lower()+'_Trip field',
            #                    get_cmd=partial(
            #                        self._ask_float, get_prefix+'R19'),
            #                    unit='T')

            # self.add_parameter(name=ax.lower()+'_Switch heater current',
            #                    get_cmd=partial(
            #                        self._ask_float, get_prefix+'R20'),
            #                    unit='mA')  # TODO

            # self.add_parameter(name=ax.lower()+'_Safe current limit, most negative',
            #                    get_cmd=partial(
            #                        self._ask_float, get_prefix+'R21'),
            #                    unit='A')

            # self.add_parameter(name=ax.lower()+'_Safe current limit, most positive',
            #                    get_cmd=partial(
            #                        self._ask_float, get_prefix+'R22'),
            #                    unit='A')

            # self.add_parameter(name=ax.lower()+'_Lead resistance',
            #                    get_cmd=partial(
            #                        self._ask_float, get_prefix+'R23'),
            #                    unit='mOhm')  # TODO

            # self.add_parameter(name=ax.lower()+'_Magnet inductance',
            #                    get_cmd=partial(
            #                        self._ask_float, get_prefix+'R24'),
            #                    unit='H')

            self.add_parameter(name=ax.lower()+'_IDN',
                               get_cmd=partial(self.get_idn, ax))

            self.connect_message(idn_param=ax.lower()+'_IDN')

        # so we have radius, theta and phi in buffer
        self.remote_status(['Remote and unlocked'])
        self.rtp.get()

    def reset(self):
        self.serial_handle.read_all()

    def hold(self):
        self.activity.set(['HOLD'])

    def rtos(self):
        self.activity.set(['RTOS'])

    def rtoz(self):
        self.activity.set(['RTOZ'])

    def _do_magnet(self, axes, cmd, setpoint=None):
        if setpoint is None:
            val = [None]*len(axes)
            for n, ax in enumerate(axes):
                    val[n] = self.get(ax+cmd)
            return val
        else:

            if isinstance(setpoint, collections.Iterable):
                pass
            else:
                setpoint = [setpoint]

            if (len(setpoint) == 1) and (len(axes) > 1):
                setpoint = [setpoint[0]]*len(axes)

            if len(setpoint) != len(axes):
                raise ValueError('Axes and setpoint do not work together %s %s'%(axes, setpoint))

            for n, ax in enumerate(axes):
                self.set(ax+cmd, setpoint[n])


    def _set_field(self, axes, setpoint):
        if isinstance(setpoint, collections.Iterable):
            pass
        else:
            setpoint = [setpoint]

        if (len(setpoint) == 1) and (len(axes) > 1):
            setpoint = [setpoint[0]]*len(axes)

        if len(setpoint) != len(axes):
            raise ValueError('Axes and setpoint do not work together %s %s'%(axes, setpoint))

        self._do_magnet(axes, '_field_setpoint', setpoint)
        self._do_magnet(axes, '_activity', ['RTOS'])

        ok = np.zeros(len(axes))
        fld = np.zeros(len(axes))

        # print(axes, setpoint)
        while True:
            for n, ax in enumerate(axes):
                if ok[n] == 0:
                    # print(ax)
                    fld[n] = self.get(ax+'_field')
                    if abs(fld[n]-setpoint[n])<=1e-5:
                        ok[n] = 1

            # print(axes, fld, setpoint, ok)

            if ok.all() == 1:
                return
            time.sleep(0.1)
            # print(fld)


    def _ask_value(self, cmd, setpoint):
        # get_prefix = '@'+str(self.axes_map[ax])
        rep = self.ask(cmd+'{:.5f}'.format(setpoint))
        if rep.startswith('?'):
            raise ValueError('Problem with write: %s' % rep)
        if not (cmd[-1] == rep):
            raise ValueError('Problem with ask: %s %s' % (cmd, rep))

    def get_idn(self, axes=None):
        idn = {}
        for ax in self.axes:
            get_prefix = '@'+str(self.axes_map[ax])
            readstuff = self.ask(get_prefix+'V').split('  ')
            model, firmware, vendor = readstuff

            idn[ax] = {
                'model': model,
                'firmware': firmware.split(' ')[1],
                'vendor': vendor.split(' ')[1],
                'serial': None
            }
        return idn[axes or self.axes[0]]

    def _ask_float(self, cmd, retry=True):
        # print(cmd)
        self.write(cmd)
        time.sleep(0.02)
        try:
            rep = self.read_until()
        except UnicodeDecodeError:
            print('UnicodeDecodeError')
            if retry:
                return self._ask_float(cmd, retry=False)
            else:
                return None

        if rep.startswith('?'):
            print('? retry')
            if retry:
                return self._ask_float(cmd, retry=False)
            else:
                return None

        try:
            string = re.sub('(^\D)', '', rep)
        except Exception as e:
            print('re')
            if retry:
                return self._ask_float(cmd, retry=False)
            else:
                return None
            # raise e
        if string == '':
            return None

        try:
            value = float(string)
        except:
            print('float', string)
            if retry:
                return self._ask_float(cmd, retry=False)
            else:
                return None

        return value

    def _get_X(self, ax, req):
        rep = self.get(ax+'_status')

        if req == 'system_status_map_m':
            return rep[1]
        if req == 'system_status_map_n':
            return rep[2]
        if req == 'activity_map':
            return rep[4]
        if req == 'remote_status_map':
            return rep[6]
        if req == 'switch_heater_map':
            return rep[8]
        if req == 'mode_map_m':
            return rep[10]
        if req == 'mode_map_n':
            return rep[11]
        if req == 'polarity_map_m':
            return rep[13]
        if req == 'polarity_map_n':
            return rep[14]
        else:
            return None

    def _get_rtp(self, ax):
        # fld=self.field(ax)
        fld = self._do_magnet(ax, '_field')
        # print(fld)
        sphere=self._carttosphere(fld)
        self._radius, self._theta, self._phi=sphere
        return sphere

    def _set_rtp(self, ax, setpoint):
        fld=self._spheretocart(setpoint)
        self._set_field(self.axes, fld)
        # self.field(ax, fld)

    def _get_r(self):
        # print('getr')
        self.rtp.get()
        return self._radius

    def _set_r(self, val):
        # self.rtp.get()
        self.rtp.set([val, self._theta, self._phi])

    def _get_theta(self):
        self.rtp.get()
        return self._theta

    def _set_theta(self, val):
        # self.rtp.get()
        self.rtp.set([self._radius, val, self._phi])

    def _get_phi(self):
        self.rtp.get()
        return self._phi

    def _set_phi(self, val):
        # self.rtp.get()
        self.rtp.set([self._radius, self._theta, val])

    def _spheretocart(self, sphere):
        """
        r,  theta,  phi = sphere
        """
        r,  theta,  phi = sphere
        x = (r * np.sin(theta) * np.cos(phi))
        y = (r * np.sin(theta) * np.sin(phi))
        z = (r * np.cos(theta))
        return [x,  y,  z]

    def _carttosphere(self, field):
        field = np.array(field)
        r = np.sqrt(np.sum(field**2))
        if r == 0:
            theta = 0
            phi = 0
        else:
            theta = np.arccos(field[2] / r)
            phi = np.arctan2(field[1],  field[0])
            if phi<0:
                phi = phi+np.pi*2
        return [r, theta, phi]
