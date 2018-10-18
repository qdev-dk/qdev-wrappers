from typing import Dict, List, Tuple, Sequence
from broadbean.element import Element
from broadbean.types import ContextDict, Symbol
import logging
import numpy as np
import os
import yaml
import importlib
from contextlib import contextmanager
from qcodes import Station, Instrument, ChannelList
from qcodes.instrument.channel import InstrumentChannel
from qdev_wrappers.parameters import DelegateParameter
from qdev_wrappers.alazar_controllers.ATSChannelController import (
    ATSChannelController, AlazarMultiChannelParameter)
from qdev_wrappers.alazar_controllers.acquisition_parameters import NonSettableDerivedParameter
from qdev_wrappers.alazar_controllers.alazar_channel import AlazarChannel
from qcodes.utils import validators as vals
from qcodes.instrument.parameter import ParameterWithSetpoints, GeneratedSetPoints
from broadbean.loader import read_element

logger = logging.getLogger(__name__)

# TODO: type hints


class PulseBuildingParameter(Parameter):
    """
    A Parameter representing a parameter of a pulse sequence running
    on a ParametricSequencer.
    It has a pulse_building_name attribute for use in sequence building
    and updates the sequence on setting.
    """

    def __init__(self, name, instrument, pulse_building_name=None,
                 label=None, unit=None, set_cmd=None,
                 vals=None):
        if set_cmd is None:
            set_cmd = self._set_and_update_sequence
        super().__init__(
            name, instrument=instrument, label=label, unit=unit,
            get_cmd=None, set_cmd=set_cmd,
            vals=vals)
        pulse_building_name = pulse_building_name or name
        self.pulse_building_name = pulse_building_name

    def _set_and_update_sequence(self, val):
        self._save_val()
        if isinstance(self.instrument, SidebandingChannel):
            pwa_instr = self.instrument._parent._parent
        elif isinstance(self.instrument, (ReadoutChannel, DriveChannel)):
            pwa_instr = instrument._parent
        else:
            logger.warning(f'could not establish how to update sequence '
                           'while setting {self.name} PulseBuildingParameter')
        if not pwa_instr.suppress_sequence_upload:
            pwa._update_sequence()


class AlazarChannel_ext(AlazarChannel):
    """
    An extension to the Alazar channel which has added
    convenience function for updating records, buffers
    and setpoints from dictionary
    """

    def __init__(self, parent, name: str,
                 demod: bool=False,
                 alazar_channel: str='A',
                 average_buffers: bool=True,
                 average_records: bool=True,
                 integrate_samples: bool=True):
        super().__init__(parent, name, demod=demod,
                         alazar_channel=alazar_channel,
                         average_buffers=average_buffers,
                         average_records=average_records,
                         integrate_samples=integrate_samples)

    def update(self, settings: Dict):
        """
        Updates the setpoints, setpoint names and setpoint labels and
        the num_averages/num_reps of the channel.

        NB Fails if the new settings require a change in averaging
            settings such as changing the state of 'average_records'
        """
        fail = False
        if settings['average_records'] != self._average_records:
            fail = True
        elif settings['average_buffers'] != self._average_buffers:
            fail = True
        if fail:
            raise RuntimeError(
                'alazar channel cannot be updated to change averaging '
                'settings, run clear_channels before changing settings')
        self.records_per_buffer._save_val(settings['records'])
        self.buffers_per_acquisition._save_val(settings['buffers'])
        if self.dimensions == 1 and self._integrate_samples:
            self.prepare_channel(
                setpoints=settings['record_setpoints'],
                setpoint_name=settings['record_setpoint_name'],
                setpoint_label=settings['record_setpoint_label'],
                setpoint_unit=settings['record_setpoint_unit'])
        else:
            self.prepare_channel(**settings)


class SidebandingChannel(InstrumentChannel):
    """
    An InstrumentChannel intended to belong to a ReadoutChannel or a
    DriveChannel of a ParametricWaveformAnalyser. One SidebandingChannel
    is used to control and keep track of the drive or readout signals
    at one frequency (eg for one qubit) and also contains the
    PulseBuildingParameters which relate to the parts of the
    pulse sequence which generate the sideband signal.

    A carrier microwave source is assumed, the signal of which is mixed
    with a signal at the 'sideband_frequency' to produce a signal at the
    'frequency'.

    If readout is intended then it is assumed that this is done by mixing
    the signal back down with the signal from a localos microwave souce
    (which together with the carrier microwave source comprises a
    heterodyne_source) to produce a signal at
    'demodulation_frequency' which can be measured using an Alazar card.
    In this case both a 'demodulation_frequency' parameter and an
    'alazar_channels' ChannelList of the associated alazar
    channels are effective attributes.
    """

    # TODO: add power parameter which takes into account carrier_power,
    #   awg channel amplitude and pulse amplitude

    def __init__(self, parent, name: str, ch_num: int,
                 frequency=frequency):
        super().__init__(parent, name)
        self.ch_num = ch_num

        # pulse building parameters
        pre_str = f'Q{ch_num}_{self.type}_'
        self.add_parameter(name='sideband_frequency',
                           pulse_building_name=pre_str + 'sideband_frequency',
                           set_cmd=False,
                           parameter_class=PulseBuildingParameter,
                           docstring='set via frequency or'
                           'readout.carrier_frequency')
        self.add_parameter(name='pulse_amplitude',
                           pulse_building_name=pre_str + 'pulse_amplitude',
                           label='Pulse Amplitude',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='I_offset',
                           pulse_building_name=pre_str + 'I_offset',
                           label='I Offset',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='Q_offset',
                           pulse_building_name=pre_str + 'Q_offset',
                           label='Q Offset',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='gain_offset',
                           pulse_building_name=pre_str + 'gain_offset',
                           label='Gain Offset',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='phase_offset',
                           pulse_building_name=pre_str + 'phase_offset',
                           label='Phase Offset',
                           unit='degrees',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='DRAG_amplitude',
                           pulse_building_name=pre_str + 'DRAG_amplitude',
                           label='DRAG amplitude',
                           parameter_class=PulseBuildingParameter)

        # composite parameters
        self.add_parameter(name='frequency',
                           set_cmd=self._set_drive_freq,
                           docstring='Sets sideband frequency '
                           'in order to get the required '
                           'drive and updates the demodulation '
                           'frequencies on the relevant '
                           'alazar channels if relevant')

        if isinstance(parent, ReadoutChannel):
            self._type = 'readout'
            self.add_parameter(name='demodulation_frequency',
                               alternative='frequency',
                               parameter_class=NonSettableDerivedParameter)
            alazar_chan_list = ChannelList(
                self,
                'alazar_channels',
                AlazarChannel_ext,
                multichan_paramclass=AlazarMultiChannelParameter)
            self.add_submodule('alazar_channels', alazar_chan_list)
        elif isinstance(parent, DriveChannel):
            self._type = 'drive'
        else:
            raise RuntimeError('parent of SidebandingChannel must be'
                               'DriveChannel or ReadoutChannel')

        self._pulse_building_parameters = {
            p.pulse_building_name: p for p in self.parameters.values() if
            isinstance(p, PulseBuildingParameter)}

        if frequency is not None:
            self.frequency(frequency)

    def _set_drive_freq(self, frequency):
        sideband = self._parent.carrier_frequency() - frequency
        self.sideband_frequency._set_and_update_sequence(sideband)

        if self._type == 'readout':
            demod = self._parent.base_demodulation_frequency() + sideband
            self.demodulation_frequency._save_val(demod)
            for ch in self.alazar_channels:
                ch.demod_freq(demod)

    def update(self, frequency=None):
        """
        Based on the carrier frequency the sideband and drive
        frequencies are updated (and the demodulation_frequency where
        relevant). If a drive is specified then this is used to choose
        the sideband_frequency and the sequence is updated, otherwise
        the existing sideband value is used and the frequency
        is updated.
        """
        carrier = self._parent.carrier_frequency()
        old_sideband = self.sideband_frequency()
        drive = frequency

        if drive is not None:
            sideband = carrier - drive
        else:
            sideband = old_sideband
            drive = carrier - sideband

        self.sideband_frequency._set_and_update_sequence(sideband)
        self.frequency._save_val(drive)

        if self._type == 'readout':
            old_demod = self.demodulation_frequency()
            base_demod = self._parent.base_demodulation_frequency()
            demod = base_demod + sideband
            if demod != old_demod:
                self.demodulation_frequency._save_val(demod)
                for ch in self.alazar_channels:
                    ch.demod_freq(demod)


class ReadoutChannel(InstrumentChannel):
    """
    An InstrumentChannel intended to belong to a ParametricWaveformAnalyser
    and which effectively groups the parameters related to readout including
    heterodyne_source parameters, alazar_controller parameters and
    PulseBuildingParameters.

    Sidebanding channels can be added for each readout frequency, the alazar
    channels of these can be accessed by the 'all_readout_channels' attribute.
    """

    def __init__(self, parent, name):
        super().__init__(parent, name)

        # heterodyne source parameters
        self.add_parameter(name='carrier_frequency',
                           set_cmd=self._set_carrier_frequency,
                           initial_value=parent._heterodyne_source.frequency(),
                           label='Readout Carrier Frequency',
                           unit='Hz',
                           docstring='Sets the frequency on the '
                           'heterodyne_source and updates the demodulation '
                           'channels so that their frequencies are still'
                           ' carrier + sideband.')
        self.add_parameter(name='carrier_power',
                           label='Readout Power',
                           unit='dBm',
                           parameter_class=DelegateParameter,
                           source=parent._heterodyne_source.power)
        self.add_parameter(name='status',
                           label='Readout Status',
                           parameter_class=DelegateParameter,
                           source=parent._heterodyne_source.status)
        self.add_parameter(name='base_demodulation_frequency',
                           set_cmd=self._set_base_demod_frequency,
                           label='Base Demodulation Frequency',
                           unit='Hz',
                           initial_value=parent._heterodyne_source.demodulation_frequency(),
                           docstring='Sets the frequency difference '
                           'between the carrier source and the localos '
                           'source on the heterodyne source and updates '
                           'the alazar channels to demodulate at this '
                           'frequency plus the frequency of any sidebands.')

        # alazar controller parameters
        self.add_parameter(name='meas_duration',
                           set_cmd=self._set_meas_dur,
                           label='Measurement Duration',
                           unit='s',
                           initial_value=1e-6)
        self.add_parameter(name='meas_delay',
                           label='Measurement Delay',
                           unit='s',
                           set_cmd=self._set_meas_delay,
                           initial_value=0)

        # alazar channel parameters
        self.add_parameter(name='demodulation_type',
                           set_cmd=self._set_demod_type,
                           initial_value='magphase',
                           vals=vals.Enum('magphase', 'realimag'),
                           docstring='Sets the two alazar channels '
                           'on each demodulation channel to give the '
                           'results in magnitude and phase space or '
                           'real and imaginary space')
        self.add_parameter(name='single_shot',
                           set_cmd=self._set_single_shot,
                           initial_value=True,
                           vals=vals.Bool())
        self.add_parameter(name='num',
                           set_cmd=self._set_num,
                           initial_value=1,
                           vals=vals.Ints(),
                           docstring='Number of repetitions if single_shot, '
                           'number of averages otherwise')
        self.add_parameter(name='integrate_time',
                           set_cmd=self._set_integrate_time,
                           initial_value=True,
                           vals=vals.Bool(),
                           docstring='Whether or not time is integrated over '
                           'in the measurement')

        # pulse building parameters
        self.add_parameter(name='total_duration',  # TODO should this live on sequence?
                           label='Cycle Time',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='marker_readout_delay',
                           label='Marker Readout Delay',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='pulse_duration',
                           label='Readout Pulse Duration',
                           pulse_building_name='readout_pulse_duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='marker_duration',
                           label='Marker Duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.all_readout_channels = parent._alazar_controller.channels
        self._sidebanding_channels = []

    def _set_carrier_frequency(self, carrier_freq):
        self._parent._heterodyne_source.frequency(carrier_freq)
        for demod_ch in self._sidebanding_channels:
            demod_ch.update()

    def _set_base_demod_frequency(self, demod_freq):
        self._heterodyne_source.demodulation_frequency(demod_freq)
        for demod_ch in self._demod_channels:
            demod_ch.update()

    def _set_demod_type(self, demod_type):
        for demod_ch in self._sidebanding_channels:
            if demod_type == 'magphase':
                demod_ch.alazar_channels[0].demod_type('magnitude')
                demod_ch.alazar_channels[0].data.label = f'Q{demod_ch_num} Magnitude'
                demod_ch.alazar_channels[1].demod_type('phase')
                demod_ch.alazar_channels[1].data.label = f'Q{demod_ch_num} Phase'
            else:
                demod_ch.alazar_channels[0].demod_type('real')
                demod_ch.alazar_channels[0].data.label = f'Q{demod_ch_num} Real'
                demod_ch.alazar_channels[1].demod_type('imaginary')
                demod_ch.alazar_channels[1].data.label = f'Q{demod_ch_num} Imaginary'

    def _set_single_shot(self, val):
        self.single_shot._save_val(val)
        self._update_alazar_channels()

    def _set_num(self, num):
        self.num._save_val(num)
        settings = get_alazar_ch_settings(self._parent)
        for ch in self.all_readout_channels:
            ch.update(settings)

    def _set_meas_dur(self, meas_dur):
        self.parent._alazar_controller.int_time(meas_dur)
        for ch in self.all_readout_channels:
            if not ch._integrate_samples:
                ch.prepare_channel()

    def _set_meas_delay(self, meas_delay):
        self.parent._alazar_controller.int_delay(meas_delay)
        for ch in self.all_readout_channels:
            if not ch._integrate_samples:
                ch.prepare_channel()

    def _set_integrate_time(self, val):
        self.integrate_time._save_val(val)
        self._update_alazar_channels()

    @property
    def _pulse_building_parameters(self):
        pulse_building_parameters = {}
        for n, p in self.parameters.items():
            if isinstance(p, PulseBuildingParameter):
                pulse_building_parameters[p.pulse_building_name] = p
        for demod_ch in self._sidebanding_channels:
            pulse_building_parameters.update(
                demod_ch._pulse_building_parameters)
        return pulse_building_parameters

    def _update_alazar_channels(self):
        """
        Updates all of the alazar channels based on the current settings
        of the ParametricWaveformAnalyser.
        """
        settings = get_alazar_ch_settings(self._parent)
        try:
            for ch in self._parent._alazar_controller.channels:
                ch.update(settings)
        except RuntimeError:
            self._reinstate_alazar_channels(settings)

    def _reinstate_alazar_channels(self, settings):
        """
        Clears all the alazar channels and creates new ones based on the
        settings dict provided. This is necessary if the averaging settings
        (average_records, average_buffers, integrate_samples) are changed.
        """
        self._parent._alazar_controller.channels.clear()
        for demod_ch in self._sidebanding_channels:
            demod_ch.alazar_channels.clear()
            self._create_and__create_alazar_channel_pair(settings, demod_ch)

    def _create_alazar_channel_pair(self, settings, demod_ch):
        """
        Create alazar channel pair based on the settings dictionary and the
        demodulations settings of the demod_ch. Put channels into demod_ch
        channels and all_readot_channels list (via alazar_controller.channels).
        """
        demod_ch_num = demod_ch.ch_num
        chan1 = AlazarChannel_ext(self._parent._alazar_controller,
                                  name=f'Q{demod_ch_num}_realmag',
                                  demod=True,
                                  average_records=settings['average_records'],
                                  average_buffers=settings['average_buffers'],
                                  integrate_samples=self.integrate_time())
        chan2 = AlazarChannel_ext(self._parent._alazar_controller,
                                  name=f'Q{demod_ch_num}_imaginaryphase',
                                  demod=True,
                                  average_records=settings['average_records'],
                                  average_buffers=settings['average_buffers'],
                                  integrate_samples=self.integrate_time())
        if self.demodulation_type() == 'magphase':
            chan1.demod_type('magnitude')
            chan1.data.label = f'Q{demod_ch_num} Magnitude'
            chan2.demod_type('phase')
            chan1.data.label = f'Q{demod_ch_num} Phase'
        else:
            chan1.demod_type('real')
            chan1.data.label = f'Q{demod_ch_num} Real'
            chan2.demod_type('imaginary')
            chan1.data.label = f'Q{demod_ch_num} Imaginary'

        for ch in [chan1, chan2]:
            ch.demod_freq(demod_ch.demodulation_frequency())
            self._parent._alazar_controller.channels.append(ch)
            demod_ch.alazar_channels.append(ch)

    def _add_sidebanding_channel(self, frequency):
        """
        Creates a SidebandingChannel with a frequency as
        specified and a pair of alazar channels which will readout
        at the frequency of the SidebandingChannel but whose
        other settings are controlled by parameters of the readout
        channel (single_shot, demodulation_type, integrate_time, num)
        """
        demod_ch_num = len(self._sidebanding_channels)
        demod_ch = SidebandingChannel(
            self, 'Q{demod_ch_num}_readout'.format(demod_ch_num), demod_ch_num,
            frequency=frequency)
        settings = get_alazar_ch_settings(self._parent)
        self._create_alazar_channel_pair(settings, demod_ch)
        self._sidebanding_channels.append(demod_ch)
        self.add_submodule(f'Q{demod_ch_num}', demod_ch)
        return demod_ch

    @contextmanager
    def sideband_update(self):
        """
        Can be used for maintaining the drive_frequencies of the
        SidebandingChannels while changing the carrier_frequency
        """
        old_drives = [demod_ch.frequency()
                      for demod_ch in self._sidebanding_channels]
        yield
        for i, demod_ch in enumerate(self.demod_chan_sidebanding_channelsnels):
            demod_ch.update(drive=old_drives[i])


class DriveChannel(InstrumentChannel):
    """
    An InstrumentChannel intended to belong to a ParametricWaveformAnalyser
    and which effectively groups the parameters related to drive including
    qubit_source parameters and PulseBuildingParameters.

    Sidebanding channels can be added for each drive frequency.
    """

    def __init__(self, parent, name):
        super().__init(parent, name)

        # qubit source parameters
        self.add_parameter(name='carrier_power',
                           label='Drive Power',
                           unit='dBm',
                           parameter_class=DelegateParameter,
                           source=parent._qubit_source.power)
        self.add_parameter(name='carrier_frequency',
                           set_cmd=self._set_carrier_frequency,
                           initial_value=parent._qubit_source.frequency(),
                           label='Drive Carrier Frequency',
                           unit='Hz',
                           docstring='Sets the frequency on the '
                           'heterodyne_source and updates the demodulation '
                           'channels so that their frequencies are still'
                           ' carrier + sideband.')
        self.add_parameter(name='status',
                           label='Drive Status',
                           parameter_class=DelegateParameter,
                           source=parent._qubit_source.status)

        # pulse building parameters
        self.add_parameter(name='drive_stage_duration',
                           label='Drive Stage Duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='sigma_cutoff',
                           label='Sigma Cutoff',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='drive_readout_delay',
                           label='Drive Readout Delay',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='modulation_marker_duration',
                           label='Drive Modulation Duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='pulse_separation',
                           label='Drive Pulse Separation',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self.add_parameter(name='pulse_duration',
                           pulse_building_name='drive_pulse_duration',
                           label='Drive Pulse Duration',
                           unit='s',
                           parameter_class=PulseBuildingParameter)
        self._sidebanding_channels = []

    def _set_carrier_frequency(self, carrier_freq):
        self._parent._qubit_source.frequency(carrier_freq)
        for demod_ch in self._sidebanding_channels:
            demod_ch.update()

    @property
    def _pulse_building_parameters(self):
        pulse_building_parameters = {}
        for n, p in self.parameters.items():
            if isinstance(p, PulseBuildingParameter):
                pulse_building_parameters[p.pulse_building_name] = p
        for demod_ch in self._sidebanding_channels:
            pulse_building_parameters.update(
                demod_ch._pulse_building_parameters)
        return pulse_building_parameters

    def _add_sidebanding_channel(self, frequency):
        """
        Creates a SidebandingChannel with a frequency as
        specified.
        """
        demod_ch_num = len(self._demod_channels)
        demod_ch = SidebandingChannel(
            self, 'Q{}_drive'.format(demod_ch_num), demod_ch_num,
            frequency=frequency)
        self._sidebanding_channels.append(demod_ch)
        self.add_submodule(f'Q{demod_ch_num}', demod_ch)
        return demod_ch

    @contextmanager
    def sideband_update(self):
        """
        Can be used for maintaining the drive_frequencies of the
        SidebandingChannels while changing the carrier_frequency
        """
        old_drives = [demod_ch.frequency()
                      for demod_ch in self._sidebanding_channels]
        yield
        for i, demod_ch in enumerate(self.demod_chan_sidebanding_channelsnels):
            demod_ch.update(drive=old_drives[i])


class SequenceChannel(InstrumentChannel):
    """
    An InstrumentChannel intended to belong to a ParametricWaveformAnalyser
    and which effectively groups the parameters related to the sequence
    including the sequence mode, the template element and the setpoint
    related paramters.
    """
    # TODO: setpoints to be a parameter (and be setpoints for alazar)
    # TODO: template element to be a parameter
    # TODO: break into inner_setpoints and outer_setpoints channels?

    def __init__(self, parent, name):
        self._inner_setpoints = None
        self._outer_setpoints = None
        self._template_element_dict = None
        self._first_element = None
        self.additional_context = {}
        self.additional_context_labels = {}
        self.additional_context_units = {}
        self.suppress_sequence_upload = {}
        super().__init__(parent, name)
        self.add_parameter(name='seq_mode',
                           set_cmd=self._set_seq_mode,
                           get_cmd=self._get_seq_mode,
                           docstring='Sets the repeat_mode on the sequencer'
                           'and the seq_mode on the alazar, reinstates all the'
                           'alazar channels and updates the sequence to '
                           'include or exclude the first element.')
        self.add_parameter(name='template_element', # TODO: serialise template element
                           label='Template Element',
                           set_cmd=self._set_template_element,
                           get_cmd=self._get_template_element,
                           docstring='Saves the name of the current template '
                           'element and sets/gets the actual element')

        # setpoint parameters
        self.add_parameter(name='inner_setpoint_symbol',  # TODO setpointS?
                           label='Inner Setpoint Symbol',
                           set_cmd=partial(self._set_setpoint_symbol, 'inner'),
                           vals=vals.Strings())
        self.add_parameter(name='inner_setpoint_start',
                           label='Inner Setpoints Start',
                           set_cmd=partial(self._set_setpoint_start, 'inner'))
        self.add_parameter(name='inner_setpoint_stop',
                           label='Inner Setpoints Stop',
                           set_cmd=partial(self._set_setpoint_stop, 'inner'))
        self.add_parameter(name='inner_setpoint_npts',
                           label='Number of Inner Setpoints',
                           set_cmd=partial(self._set_setpoint_npts, 'inner'),
                           vals=vals.Ints(0, 1000),
                           docstring='Sets the number of setpoint values, '
                           'equivalent to setting the inner_setpoints_step')
        self.add_parameter(name='inner_setpoint_step',
                           label='Inner Setpoints Step Size',
                           set_cmd=partial(self._set_setpoint_step, 'inner'),
                           docstring='Sets the number of setpoint values, '
                           'equivalent to setting the inner_setpoint_npts')
        self.add_parameter(name='outer_setpoint_symbol',
                           label='Outer Setpoint Symbol',
                           set_cmd=partial(self._set_setpoint_symbol, 'outer'),
                           vals=vals.Strings())
        self.add_parameter(name='outer_setpoint_start',
                           label='Outer Setpoints Start',
                           set_cmd=partial(self._set_setpoint_start, 'outer'))
        self.add_parameter(name='outer_setpoint_stop',
                           label='Outer Setpoints Stop',
                           set_cmd=partial(self._set_setpoint_stop, 'outer'))
        self.add_parameter(name='outer_setpoint_npts',
                           label='Number of Outer Setpoints',
                           set_cmd=partial(self._set_setpoint_npts, 'outer'),
                           vals=vals.Ints(0, 1000),
                           docstring='Sets the number of setpoint values, '
                           'equivalent to setting the outer_setpoint_step')
        self.add_parameter(name='outer_setpoint_step',
                           label='Outer Setpoints Step Size',
                           set_cmd=partial(self._set_setpoint_step, 'outer'),
                           docstring='Sets the number of setpoint values, '
                           'equivalent to setting the outer_setpoint_npts')

    def _get_seq_mode(self):
        if (self._parent._alazar.seq_mode() and
                self._parent._sequencer.repeat_mode() == 'sequence'):
            return True
        elif (not self._parent._alazar.seq_mode() and
              self._parent._sequencer.repeat_mode() == 'element'):
            return False
        elif (not self._parent._alazar.seq_mode() and
                (len(self._parent._sequencer.get_inner_setpoints()) == 1 and
                    self._parent._sequencer.get_outer_setpoints() is None)):
            return False
        else:
            raise RuntimeError(
                'seq modes on sequencer and alazar do not match')

    def _set_seq_mode(self, mode):
        if str(mode).upper() in ['TRUE', '1', 'ON']:
            self._parent._alazar.seq_mode(True)
            self._parent._sequencer.repeat_mode('sequence')
            self._first_element = None
        else:
            self._parent._alazar.seq_mode(False)
            self._parent._sequencer.repeat_mode('element')
            self._first_element = self._template_element_dict['first_element']
        self._save_val(mode)
        self._update_sequence()

    def _get_template_element(self):
        return self._template_element_dict[
            self.template_element._latest['value']]

    def _set_template_element(self, template_element_name):
        self.template_element._save_val(template_element_name)
        if not self.suppress_sequence_upload:
            self._update_sequence()

    # TODO: refactor these three functions into setpoints parameter?
    def _set_setpoint_symbol(self, setpoint_type, symbol):
        self.parameters[f'{setpoint_type}_setpoints_symbol']._save_val(symbol)
        if not self.suppress_sequence_upload:
            self._update_sequence()

    def _set_setpoint_start(self, setpoint_type, start):
        setattr(self, _{setpoint_type}_setpoints, None)
        self.parameters[f'{setpoint_type}_setpoint_start']._save_val(start)
        if not self.suppress_sequence_upload:
            self._update_sequence()

    def _set_setpoint_stop(self, setpoint_type, stop):
        setattr(self, _{setpoint_type}_setpoints, None)
        self.parameters[f'{setpoint_type}_setpoint_stop']._save_val(stop)
        if not self.suppress_sequence_upload:
            self._update_sequence()

    def _set_setpoint_npts(self, setpoint_type, num):
        start = self.parameters[f'{setpoint_type}_setpoint_start']()
        stop = self.parameters[f'{setpoint_type}_setpoint_stop']()
        step = abs(stop - start) / num
        setattr(self, _{setpoint_type}_setpoints, None)
        self.parameters[f'{setpoint_type}_setpoint_step']._save_val(step)
        self.parameters[f'{setpoint_type}_setpoint_npts']._save_val(num)
        if not self.suppress_sequence_upload:
            self._update_sequence()

    def _set_setpoint_step(self, setpoint_type, step):
        start = self.parameters[f'{setpoint_type}_setpoint_start']()
        stop = self.parameters[f'{setpoint_type}_setpoint_stop']()
        npts = int(abs(stop - start) / step)
        setattr(self, _{setpoint_type}_setpoints, None)
        self.parameters[f'{setpoint_type}_setpoint_npts']._save_val(npts)
        self.parameters[f'{setpoint_type}_setpoint_step']._save_val(step)
        if not self.suppress_sequence_upload:
            self._update_sequence()

    @property
    def inner_setpoints(self):
        if self._inner_setpoints is not None:
            return self._inner_setpoints
        else:
            return np.linspace(self.inner_setpoints_start(),
                               self.inner_setpoints_stop(),
                               num=self.inner_setpoints_npts())

    @property
    def outer_setpoints(self):
        if self._outer_setpoints is not None:
            return self._outer_setpoints
        else:
            return np.linspace(self.outer_setpoints_start(),
                               self.outer_setpoints_stop(),
                               num=self.outer_setpoints_npts())

    def _generate_context(self):
        """
        Makes up context, labels and units dictionaries based on all of the
        pulse bui associated with the parent Parametric
        Waveform Analyser.
        """
        context = {}
        labels = {}
        units = {}
        for name, param in self._parent._pulse_building_parameters.items():
            context[name] = param()
            labels[name] = param.label
            units[name] = param.unit
        return context, labels, units

    def _update_sequence(self):
        """
        Based on the values of the PulseBuildingParameters, the inner and
        outer setpoints and the template element uploads a sequence
        and updates the alazar_channels.
        """
        context, labels, units = self._generate_context()
        context.update(self.additional_context)
        labels.update(self.additional_context_labels)
        units.update(self.additional_context_units)
        self._parent._sequencer.set_template(
            self.template_element(),
            first_sequence_element=self._first_element,
            inner_setpoints=self.inner_setpoints,
            outer_setpoints=self.outer_setpoints,
            context=context,
            labels=labels,
            unit=units)
        self._parent.readout._update_alazar_channels()

    def set_setpoints(self, inner_setpoints, outer_setpoints=None):
        """
        Method to manually set to setpoints instead of using the start,
        stop and step/npts parameters. Useful if you want non evenly
        spaced setpoints.
        """
        initial_supress_sequence_upload = self.suppress_sequence_upload
        self.suppress_sequence_upload = False

        inner_symbol, inner_setpoints = inner_setpoints
        self.inner_setpoints_symbol(inner_symbol)
        self._inner_setpoints = inner_setpoints

        if outer_setpoints is not None:
            outer_symbol, outer_setpoints = outer_setpoints
            self.outer_setpoints_symbol(outer_symbol)
            self._outer_setpoints = outer_setpoints
        else:
            self._outer_setpoints = None
            self.outer_setpoints_symbol._save_val(None)

        self.inner_setpoints_start._save_val(None)
        self.inner_setpoints_stop._save_val(None)
        self.inner_setpoints_step._save_val(None)
        self.inner_setpoints_npts._save_val(None)
        self.outer_setpoints_start._save_val(None)
        self.outer_setpoints_stop._save_val(None)
        self.outer_setpoints_step._save_val(None)
        self.outer_setpoints_npts._save_val(None)

        self.suppress_sequence_upload = initial_supress_sequence_upload
        if not self.suppress_sequence_upload:
            self._update_sequence()

    def reload_template_element_dict(self):
        """
        Reloads the dictionary of template elements from the yaml files
        and python files in the ParametricWaveformAnalyser
        pulse_building_folder.

        NB python files are required to define create_template_element
        function
        """
        template_element_dict = {}
        for file in os.listdir(self._parent._pulse_building_folder):
            element_name = os.path.splitext(file)[0]
            if file.endswith(".yaml"):
                yf = yaml.load(file)
                element = read_element(yf)
            elif file.endswith(".py"):
                create_element_fn = importlib.import_module(
                    element_name).create_template_element
            template_element_dict[element_name] = create_element_fn()
        self._template_element_dict = template_element_dict
        self.template_element.vals = vals.Strings(
            *template_element_dict.keys())

    @contextmanager
    def single_sequence_update(self):
        """
        For use when changing multiple PulseBuildingParameters at once
        ensures only one sequence upload.
        """
        initial_supression_value = self.suppress_sequence_upload
        self.suppress_sequence_upload = False
        yield
        self._update_sequence()
        self.suppress_sequence_upload = initial_supression_value


class ParametricWaveformAnalyser(Instrument):
    """
    The PWA represents a composite instrument. It comprises a parametric
    sequencer, an Alazar card, a heterodyne source and a qubit source. The
    idea is that the parametric sequencer is used to sideband the heterodyne
    and qubit sources to create a drive and readout tone per qubit and also
    optionally to vary some parameter in a sequence. The
    setpoints of this sequence and the demodulation frequencies
    calculated from the heterodyne source demodulation frequency and the
    parametric sequencer sideband frequencies are communicated to the Alazar
    controller.
    """

    def __init__(self,
                 name: str,
                 sequencer,
                 alazar,
                 heterodyne_source,
                 qubit_source,
                 pulse_building_folder) -> None:
        super().__init__(name)
        self._sequencer = sequencer
        self._alazar = alazar
        self._heterodyne_source = heterodyne_source
        self._qubit_source = qubit_source
        self._pulse_building_folder = os.path.abspath(pulse_building_folder)
        if not os.path.isdir(self._pulse_building_folder):
            raise ValueError(
                'Pulse building folder {} cannot be found'
                ''.format(self._pulse_building_folder))
        sys.path.append(self._pulse_building_folder)
        self._alazar_controller = ATSChannelController(
            'alazar_controller', alazar.name)
        readout_channel = ReadoutChannel(self, 'readout')
        self.add_submodule('readout', readout_channel)
        drive_channel = DriveChannel(self, 'drive')
        self.add_submodule('drive', drive_channel)
        sequence_channel = SequenceChannel(self, 'sequence')
        self.add_submodule('sequence', sequence_channel)
        self.qubits = {}
        self.sequence.reload_template_element_dict()

    @property
    def _pulse_building_parameters(self):
        pulse_building_parameters = {}
        pulse_building_parameters.update(
            self.readout._pulse_building_parameters)
        pulse_building_parameters.update(self.drive._pulse_building_parameters)
        return pulse_building_parameters

    def add_qubit(self, readout_frequency, drive_frequency):
        """
        Adds a SidebandingChannel for readout and one for drive to the
        ReadoutChannel and DriveChannel respectively and also stores
        these sidebanding channels in the qubits dictionary.
        """
        q_num = len(self.qubits)
        readout_ch = self.readout._add_sidebanding_channel(readout_frequency)
        drive_ch = self.drive._add_sidebanding_channel(drive_frequency)
        qubits['Q' + q_num] = {'readout': readout_ch, 'drive': drive_ch}

    def clear_qubits(self):
        """
        Clears the qubit dictionary, the alazar channels and all
        SidebandingChannels (both from the ReadoutChannel and the DriveChannel)
        """
        qubits.clear()
        self._alazar_controller.alazar_channels.clear()
        self.readout._sidebanding_channels.clear()
        self.drive._sidebanding_channels.clear()


def get_alazar_ch_settings(pwa):
    """
    Based on the current instrument settings calculates the settings
    configuration for an alazar channel as a dictionary with keys:

    buffers: int
    average_buffers: bool
    records: int
    average_records: bool

    and optionally:

    buffer_setpoints: array
    buffer_setpoint_name: str, None
    buffer_setpoint_label: str, None
    buffer_setpoint_unit: str, None
    records_setpoints: array, None
    records_setpoint_name: str, None
    records_setpoint_label: str, None
    records_setpoint_unit: str, None
    """
    seq_mode = pwa.seq_mode()
    num = pwa.readout.num()
    single_shot = pwa.readout.single_shot()
    if not single_shot:
        settings['average_buffers'] = True
        if (seq_mode and
                len(sequencer.get_inner_setpoints().values) > 1):
            if sequencer.get_outer_setpoints() is not None:
                logger.warn('Averaging channel will average over '
                            'outer setpoints of sequencer sequence')
            record_symbol = sequencer.get_inner_setpoints().symbol
            record_setpoints = sequencer.get_inner_setpoints().values
            record_param = getattr(sequencer.repeat, record_symbol)
            settings['records'] = len(record_setpoints)
            settings['buffers'] = num
            settings['average_records'] = False
            settings['record_setpoints'] = record_setpoints
            settings['record_setpoint_name'] = record_symbol
            settings['record_setpoint_label'] = record_param.label
            settings['record_setpoint_unit'] = record_param.unit

        else:
            settings['average_records'] = True
            max_samples = pwa._alazar_controller.board_info['max_samples']
            samples_per_rec = pwa._alazar_controller.samples_per_record()
            tot_samples = num * samples_per_rec
            if tot_samples > max_samples:
                settings['records'] = math.floor(
                    max_samples / samples_per_rec)
                settings['buffers'] = math.ceil(max_samples / records)
            else:
                settings['records'] = num
                settings['buffers'] = 1
    else:
        settings['average_buffers'] = False
        settings['average_records'] = False
        if (seq_mode and
                len(pwa._sequencer.get_inner_setpoints().values) > 1):
            if (pwa._sequencer.get_outer_setpoints() is not None and
                    num > 1):
                raise RuntimeError(
                    'Cannot have outer setpoints and multiple nreps')
            record_symbol = pwa._sequencer.get_inner_setpoints().symbol
            record_setpoints = pwa._sequencer.get_inner_setpoints().values
            records_param = getattr(pwa._sequencer.repeat, record_symbol)
            settings['records'] = len(record_setpoints)
            settings['record_setpoints'] = record_setpoints
            settings['record_setpoint_name'] = record_symbol
            settings['record_setpoint_label'] = records_param.label
            settings['record_setpoint_unit'] = records_param.unit
            if pwa._sequencer.get_outer_setpoints() is not None:
                buffers_symbol = pwa._sequencer.get_outer_setpoints().symbol
                buffers_setpoints = pwa._sequencer.get_outer_setpoints().values
                buffers_param = getattr(
                    pwa._sequencer.repeat, buffers_symbol)
                settings['buffer_setpoints'] = buffers_setpoints
                settings['buffer_setpoint_name'] = buffers_symbol
                settings['buffer_setpoint_label'] = buffers_param.label
                settings['buffer_setpoint_unit'] = buffers_param.unit
                settings['buffers'] = len(buffer_setpoints)
            else:
                settings['buffers'] = num
                settings['buffer_setpoints'] = np.arange(num)
                settings['buffer_setpoint_name'] = 'repetitions'
                settings['buffer_setpoint_label'] = 'Repetitions'
        else:
            max_samples = pwa._alazar_controller.board_info['max_samples']
            samples_per_rec = pwa._alazar_controller.samples_per_record()
            tot_samples = num * samples_per_rec
            if tot_samples > max_samples:
                records = math.floor(max_samples / samples_per_rec)
                buffers = math.ceil(max_samples / records)
            else:
                records = num
                buffers = 1
            settings['records'] = records
            settings['buffers'] = buffers
            settings['record_setpoints'] = np.arange(records)
            settings['record_setpoint_name'] = 'record_repetitions'
            settings['record_setpoint_label'] = 'Record Repetitions'
            settings['buffer_setpoints'] = np.arange(buffers)
            settings['buffer_setpoint_name'] = 'buffer_repetitions'
            settings['buffer_setpoint_label'] = 'Buffer Repetitions'
    return settings
