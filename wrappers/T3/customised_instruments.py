# -*- coding: utf-8 -*-
"""
Customised instruments with extra features such as voltage dividers and derived
parameters for use with T3
"""
import numpy as np

from qcodes.instrument_drivers.QDev.QDac_channels import QDac
from qcodes.instrument_drivers.stanford_research.SR830 import SR830
from qcodes.instrument_drivers.stanford_research.SR830 import ChannelBuffer
from qcodes.instrument_drivers.Keysight.Keysight_34465A import Keysight_34465A
from qcodes.instrument_drivers.AlazarTech.ATS9360 import AlazarTech_ATS9360
from qcodes.instrument_drivers.AlazarTech.acq_controllers import ATS9360Controller
from qcodes.instrument_drivers.rohde_schwarz.ZNB import ZNB
from qcodes.instrument_drivers.tektronix.AWG5014 import Tektronix_AWG5014
from qcodes.instrument_drivers.yokogawa.GS200 import GS200
from qcodes.instrument_drivers.devices import VoltageDivider
from qcodes.instrument_drivers.Harvard.Decadac import Decadac
from qcodes.utils import validators as vals
from qcodes import ManualParameter
from qcodes import ArrayParameter


class Scope_avg(ArrayParameter):

    def __init__(self, name, channel=1, **kwargs):

        super().__init__(name, shape=(1,), **kwargs)
        self.has_setpoints = False
        self.zi = self._instrument

        if not channel in [1, 2]:
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

# A conductance buffer, needed for the faster 2D conductance measurements
# (Dave Wecker style)


class ConductanceBuffer(ChannelBuffer):
    """
    A full-buffered version of the conductance based on an
    array of X measurements

    We basically just slightly tweak the get method
    """

    def __init__(self, name: str, instrument: 'SR830_T10', **kwargs):
        super().__init__(name, instrument, channel=1)
        self.unit = ('e^2/h')

    def get(self):
        # If X is not being measured, complain
        if self._instrument.ch1_display() != 'X':
            raise ValueError('Can not return conductance since X is not '
                             'being measured on channel 1.')

        resistance_quantum = 25.818e3  # (Ohm)
        xarray = super().get()
        iv_conv = self._instrument.ivgain
        ac_excitation = self._instrument.amplitude_true()

        gs = xarray / iv_conv / ac_excitation * resistance_quantum

        return gs


# Subclass the SR830
class SR830_T3(SR830):
    """
    An SR830 with the following super powers:
        - a Voltage divider
        - An I/V converter
        - A conductance buffer
    """

    def __init__(self, name, address, config, **kwargs):
        super().__init__(name, address, **kwargs)

        # using the vocabulary of the config file
        self.ivgain = float(config.get('Gain Settings',
                                       'iv gain'))
        self.__acf = float(config.get('Gain Settings',
                                      'ac factor'))

        self.add_parameter('amplitude_true',
                           label='ac bias',
                           parameter_class=VoltageDivider,
                           v1=self.amplitude,
                           division_value=self.acfactor)

        self.acbias = self.amplitude_true

        self.add_parameter('g',
                           label='{} conductance'.format(self.name),
                           # use lambda for late binding
                           get_cmd=self._get_conductance,
                           unit='e^2/h',
                           get_parser=float)

        self.add_parameter('conductance',
                           label='{} conductance'.format(self.name),
                           parameter_class=ConductanceBuffer)

        self.add_parameter('resistance',
                           label='{} Resistance'.format(self.name),
                           get_cmd=self._get_resistance,
                           unit='Ohm',
                           get_parser=float)

    def _get_conductance(self):
        """
        get_cmd for conductance parameter
        """
        resistance_quantum = 25.8125e3  # (Ohm)
        i = self.R() / self.ivgain
        # ac excitation voltage at the sample
        v_sample = self.amplitude_true()

        return (i / v_sample) * resistance_quantum

    def _get_resistance(self):
        """
        get_cmd for resistance parameter
        """
        i = self.R() / self.ivgain
        # ac excitation voltage at the sample
        v_sample = self.amplitude_true()

        return (v_sample / i)

    @property
    def acfactor(self):
        return self.__acf

    @acfactor.setter
    def acfactor(self, acfactor):
        self.__acf = acfactor
        self.amplitude_true.division_value = acfactor

    def snapshot_base(self, update=False, params_to_skip_update=None):
        if params_to_skip_update is None:
            params_to_skip_update = (
                'conductance', 'ch1_databuffer', 'ch2_databuffer')
        snap = super().snapshot_base(
            update=update, params_to_skip_update=params_to_skip_update)
        return snap


# Subclass the QDAC
class QDAC_T10(QDac):
    """
    A QDac with three voltage dividers
    """

    def __init__(self, name, address, config, **kwargs):
        super().__init__(name, address, **kwargs)

        # Define the named channels

        topo_channel = int(config.get('Channel Parameters',
                                      'topo bias channel'))
        topo_channel = self.channels[topo_channel - 1].v

        self.add_parameter('current_bias',
                           label='{} conductance'.format(self.name),
                           # use lambda for late binding
                           get_cmd=lambda: self.channels.chan40.v.get() / 10E6 * 1E9,
                           set_cmd=lambda value: self.channels.chan40.v.set(
                               value * 1E-9 * 10E6),
                           unit='nA',
                           get_parser=float)

        self.topo_bias = VoltageDivider(topo_channel,
                                        float(config.get('Gain Settings',
                                                         'dc factor topo')))


class Decadac_T3(Decadac):
    """
    A Decadac with one voltage dividers
    """

    def __init__(self, name, address, config, **kwargs):
        self.config = config
        deca_physical_min = int(self.config.get('Decadac Range', 'min_volt'))
        deca_physical_max = int(self.config.get('Decadac Range', 'max_volt'))
        kwargs.update({'min_val': deca_physical_min,
                       'max_val': deca_physical_max})
        super().__init__(name, address, **kwargs)

        # Define the named channels

        # Assign labels:
        labels = config.get('Decadac Channel Labels')
        for chan, label in labels.items():
            self.channels[int(chan)].volt.label = label

        # Take voltage divider of source/drain into account:
        dcbias_i = int(config.get('Channel Parameters',
                                  'source channel'))
        dcbias = self.channels[dcbias_i].volt
        self.dcbias = VoltageDivider(dcbias,
                                     float(config.get('Gain Settings',
                                                      'dc factor')))
        self.dcbias.label = config.get('Decadac Channel Labels', dcbias_i)

        # Assign custom variable names
        lcut = config.get('Channel Parameters', 'left cutter')
        self.lcut = self.channels[int(lcut)].volt

        rcut = config.get('Channel Parameters', 'right cutter')
        self.rcut = self.channels[int(rcut)].volt

        jj = config.get('Channel Parameters', 'central cutter')
        self.jj = self.channels[int(jj)].volt

        rplg = config.get('Channel Parameters', 'right plunger')
        self.rplg = self.channels[int(rplg)].volt

        lplg = config.get('Channel Parameters', 'left plunger')
        self.lplg = self.channels[int(lplg)].volt

        self.add_parameter('cutters',
                           label='{} cutters'.format(self.name),
                           # use lambda for late binding
                           get_cmd=self.get_cutters,
                           set_cmd=self.set_cutters,
                           unit='V',
                           get_parser=float)

        # Set up voltage and ramp safetly limits in software
        ranges = config.get('Decadac Channel Limits')
        ramp_settings = config.get('Decadac Channel Ramp Setttings')

        for chan in range(20):
            try:
                chan_range = ranges[str(chan)]
            except KeyError:
                continue
            range_minmax = chan_range.split(" ")
            if len(range_minmax) != 2:
                raise ValueError(
                    "Expected: min max. Got {}".format(chan_range))
            else:
                rangemin = float(range_minmax[0])
                rangemax = float(range_minmax[1])
            vldtr = vals.Numbers(rangemin, rangemax)
            self.channels[chan].volt.set_validator(vldtr)

            try:
                chan_ramp_settings = ramp_settings[str(chan)]
            except KeyError:
                continue
            ramp_stepdelay = chan_ramp_settings.split(" ")
            if len(ramp_stepdelay) != 2:
                raise ValueError(
                    "Expected: step delay. Got {}".format(chan_ramp_settings))
            else:
                step = float(ramp_stepdelay[0])
                delay = float(ramp_stepdelay[1])
            self.channels[chan].volt.set_step(step)
            self.channels[chan].volt.set_delay(delay)

    def set_all(self, voltage_value, set_dcbias=False):
        channels_in_use = self.config.get('Decadac Channel Labels').keys()
        channels_in_use = [int(ch) for ch in channels_in_use]

        for ch in channels_in_use:
            self.channels[ch].volt.set(voltage_value)

        if set_dcbias:
            self.dcbias.set(voltage_value)

    def set_cutters(self, voltage_value):
        dic = self.config.get('Channel Parameters')

        self.channels[int(dic['left cutter'])].volt.set(voltage_value)
        self.channels[int(dic['right cutter'])].volt.set(voltage_value)

    def get_cutters(self):
        dic = self.config.get('Channel Parameters')

        vleft = self.channels[int(dic['left cutter'])].volt.get()
        vright = self.channels[int(dic['right cutter'])].volt.get()
        if (abs(vleft - vright) > 0.05):
            print('Error! Left and right cutter are not the same!')
        else:
            return vleft


# Subclass the DMM
class Keysight_34465A_T10(Keysight_34465A):
    """
    A Keysight DMM with an added I-V converter
    """

    def __init__(self, name, address, **kwargs):
        super().__init__(name, address, **kwargs)

        self.iv_conv = 1

        self.add_parameter('ivconv',
                           label='Current',
                           unit='pA',
                           get_cmd=self._get_current,
                           set_cmd=None)

    def _get_current(self):
        """
        get_cmd for dmm readout of IV_TAMP parameter
        """
        return self.volt() / self.iv_conv * 1E12


class GS200_T3(GS200):
    def __init__(self, name, address, config=None, **kwargs):
        super().__init__(name, address, **kwargs)

        # Set voltage and ramp limits from config
        self.config = config
        if config is not None:
            try:
                ramp_stepdelay = config.get(
                    'Yokogawa Ramp Settings', 'voltage').split(" ")
                ranges_minmax = config.get(
                    'Yokogawa Limits', 'voltage').split(" ")
            except KeyError as e:
                raise KeyError('Settings not found in config file. Check they '
                               'are specified correctly. {}'.format(e))
            self.voltage.set_step(int(ramp_stepdelay[0]))
            self.voltage.set_delay(int(ramp_stepdelay[1]))
            vldtr = vals.Numbers(int(ranges_minmax[0]), int(ranges_minmax[1]))
            self.voltage.set_validator(vldtr)


class AlazarTech_ATS9360_T3(AlazarTech_ATS9360):
    def __init__(self, name, seq_mode='off'):
        if seq_mode is 'on':
            io_mode = 'AUX_IN_TRIGGER_ENABLE'
            io_param = 'TRIG_SLOPE_POSITIVE'
        elif seq_mode is 'off':
            io_mode = 'AUX_IN_AUXILIARY'
            io_param = 'NONE'
        else:
            raise ValueError('must set seq mode to "on" or '
                             '"off", received {}'.format(seq_mode))
        super().__init__(name=name)
        self.config(clock_source='EXTERNAL_CLOCK_10MHz_REF',
                    sample_rate=500000000,
                    clock_edge='CLOCK_EDGE_RISING',
                    decimation=1,
                    coupling=['DC', 'DC'],
                    channel_range=[.4, .4],
                    impedance=[50, 50],
                    trigger_operation='TRIG_ENGINE_OP_J',
                    trigger_engine1='TRIG_ENGINE_J',
                    trigger_source1='EXTERNAL',
                    trigger_slope1='TRIG_SLOPE_POSITIVE',
                    trigger_level1=140,
                    trigger_engine2='TRIG_ENGINE_K',
                    trigger_source2='DISABLE',
                    trigger_slope2='TRIG_SLOPE_POSITIVE',
                    trigger_level2=128,
                    external_trigger_coupling='DC',
                    external_trigger_range='ETR_2V5',
                    trigger_delay=0,
                    timeout_ticks=0,
                    aux_io_mode=io_mode,
                    aux_io_param=io_param
                    )
        self.add_parameter(name='seq_mode',
                           get_cmd=self._get_seq_mod,
                           set_cmd=self._set_seq_mode,
                           vals=vals.Anything()
                           )

    def _get_seq_mod(self):
        if (self.aux_io_mode() is 'AUX_IN_TRIGGER_ENABLE' and
                self.aux_io_param() is 'TRIG_SLOPE_POSITIVE'):
            return 'on'
        elif (self.aux_io_mode() is 'AUX_IN_AUXILIARY' and
              self.aux_io_param() is 'NONE'):
            return 'off'
        else:
            raise ValueError('aux_io_mode: {}, aux_io_param: {} '
                             'do not correspond to seq_mode on or off')

    def _set_seq_mode(self, mode):
        if mode is 'on':
            self.config(sample_rate=self.sample_rate(),
                          clock_edge=self.clock_edge(),
                          clock_source=self.clock_source(),
                          aux_io_mode='AUX_IN_TRIGGER_ENABLE',
                          aux_io_param='TRIG_SLOPE_POSITIVE')
        elif mode is 'off':
            self.config(sample_rate=self.sample_rate(),
                          clock_edge=self.clock_edge(),
                          clock_source=self.clock_source(),
                          aux_io_mode='AUX_IN_AUXILIARY',
                          aux_io_param='NONE')
        else:
            raise ValueError('must set seq mode to "on" or "off"')


class ATS9360Controller_T3(ATS9360Controller):
    def __init__(self, name, alazar, ctrl_type='ave'):
        if ctrl_type is 'samp':
            integrate_samples = False
            average_records = True
        elif ctrl_type is 'ave':
            integrate_samples = True
            average_records = True
        elif ctrl_type is 'rec':
            integrate_samples = True
            average_records = False
        else:
            raise Exception('acquisition controller type must be in {}, '
                            'received: {}'.format(['samp', 'ave', 'rec'],
                                                  ctrl_type))
        super().__init__(name=name, alazar_name=alazar.name,
                         integrate_samples=integrate_samples,
                         average_records=average_records)


class AWG5014_T3(Tektronix_AWG5014):
    def __init__(self, name, visa_address, **kwargs):
        super().__init__(name, visa_address, **kwargs)
        self.add_parameter(name='current_seq',
                           parameter_class=ManualParameter,
                           initial_value=None,
                           label='Uploaded sequence index',
                           vals=vals.Ints())
        self.ref_source('EXT')
        self.clear_message_queue()


class VNA_T3(ZNB):
    def __init__(self, name, visa_address, S21=True, spec_mode=False, gen_address=None,
                 timeout=40):
        super().__init__(name, visa_address, init_s_params=False, timeout=timeout)
        if S21:
            self.add_channel('S21')
            self.add_parameter(name='single_S21', get_cmd=self._get_single)
        if spec_mode and gen_address is not None:
            self.add_spectroscopy_channel(gen_address)
        elif spec_mode:
            print('spec mode not added as no generator ip address provided')
    def _get_single(self):
        return self.channels.S21.trace_mag_phase()[0][0]