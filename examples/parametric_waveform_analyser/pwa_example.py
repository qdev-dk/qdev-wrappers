import numpy as np
from qdev_wrappers.station_configurator import StationConfigurator
from qdev_wrappers.customised_instruments.heterodyne_source import HeterodyneSource
from qdev_wrappers.customised_instruments.parametric_sequencer import ParametricSequencer
from qdev_wrappers.customised_instruments.parametric_waveform_analyser import ParametricWaveformAnalyser
from qdev_wrappers.sweep_functions_new import do0d
from broadbean.atoms import flat, zero, marker_on, marker_off
from broadbean import SegmentGroup, Element


#%% importing the necessary 'basic' instruments

scfg = StationConfigurator('config.yaml')

cavity = scfg.load_instrument('cavity_rs')
localos = scfg.load_instrument('localos_rs')
awg = scfg.load_instrument('awg')
awg_interface = AWG5014Interface(awg)
alazar = scfg.load_instrument('alazar')


#%% making a template element

seg1 = zero(duration='flex_time')
seg2 = flat(duration='pulse_duration', amplitude='pulse_amplitude')
seg3 = zero(duration='flex_time')

pi_pulse = SegmentGroup(seg1, seg2, seg3,
                        duration='total_duration')

m1 = marker_off(duration='pre_marker_time')
m2 = marker_on(duration='marker_time')
m3 = marker_off(duration='post_marker_time')

markers = SegmentGroup(m1, m2, m3,
                       duration='total_duration')


def mytransformation(context):
    context['flex_time'] = 0.5 * \
        (context['total_duration'] - context['pulse_duration'])
    context['pre_marker_time'] = context['flex_time'] + context['marker_delay']
    context['post_marker_time'] = context['total_duration'] - \
        context['marker_time'] - context['pre_marker_time']


template_element = Element(segments={1: pi_pulse,
                                     '3M2': markers},
                           sequencing={'nrep': 2},
                           transformation=mytransformation)

context = {'total_duration': 3e-4,
           'marker_time': 2e-5,
           'marker_delay': 5e-5,
           'pulse_duration': 0.5e-4,
           'pulse_amplitude': 1,
           'readout_sideband_0': 0}

labels = {'total_duration': 'Total Duration',
          'marker_time': 'Marker Time',
          'marker_delay': 'Marker Delay',
          'pulse_duration': 'Pulse Duration',
          'pulse_amplitude': 'Pulse Amplitude',
          'readout_sideband_0': 'Qubit 0 Readout Sideband'}

units = {'total_duration': 's',
         'marker_time': 's',
         'marker_delay': 's',
         'pulse_duration': 's',
         'pulse_amplitude': '',
         'readout_sideband_0': 'Hz'}

settings_dict = {'context': context, 'units': units, 'labels': labels}

pulse_durations = np.linspace(1e-4, 2.9e-4, 3)

#%% importing 'meta' instruments

heterodyne_source = HeterodyneSource('heterodyne_source',
                                     cavity=cavity,
                                     localos=localos,
                                     demodulation_frequency=15e6)

sequencer = ParametricSequencer('parametric_sequencer',
                                awg=awg_interface,
                                template_element=template_element,
                                inner_setpoints=(
                                    'pulse_duration', pulse_durations),
                                context=context,
                                labels=labels,
                                units=units)

pwa = ParametricWaveformAnalyser('parametric_waveform_analyser',
                                 sequencer=sequencer,
                                 alazar=alazar,
                                 heterodyne_source=heterodyne_source,
                                 initial_sequence_settings=settings_dict)

#%% setting up the readout settings
# sets the heterodyne_source to output 7GHz on the 'carrier' and 7.015GHZ
# on the 'localos'.  

pwa.base_demodulation_frequency(15e6)
pwa.carrier_frequency(7e9)

# Adding a demodulation channel sets up a sideband on
# the awg so that the actual 'drive' created is 6.9GHz (sideband of 100MHz).
pwa.add_demodulation_channel(6.9e9)

#%% Set up awg and alazar settings
# Seq mode on set awg to run through the sequence so measurments are
# taken for all the sequencer setpoint values. A trigger to the aux/io
# input of the alazar is required to signal the start of the sequence.
# This is in addition to the trigger into trig which triggers each aqusition
pwa.seq_mode(1)
pwa.int_time(1e-6)  # time for alazar acquisition
pwa.int_delay(0)  # time to wait after trigger before saving aquisition data


# Adding an alazar channel to demodulation channel 0 will inherit the
# demodulation settings of this channel so it will demodulate at
# 100MHz + 15MHz, ie the actual difference betweeen the 'drive' and the
# 'localos'. These two channels are set up to find the magnitude of the signal
# and to average 1000 times, the first as a function of time, the second
# will average over the time samples 1000 times
pwa.add_alazar_channel(0, 'm', integrate_time=False, num=1000)
pwa.add_alazar_channel(0, 'm', integrate_time=True, num=1000)

#%% take data
# this will produce a 2d trace with time and pulse_duration the setpoints
do0d(pwa.alazar_channels.ch_0_m_time.data) # TODO: can I actually get this?

#%%
# this will produce a 1d trace with pulse_duration as the setpoints
do0d(pwa.alazar_channels.ch_0_m.data)

#%% change seq mode
# This will clear the alazar channels and reinstate them (it is not possible
# currently to change the averaging settings as required so clearing is
# necessary). The sequencer will output the default values of the sequence
# if they are present TODO: what does it do otherwise!!??
# (here pulse_duration = 0.5e-4)
pwa.seq_mode(0)

# this is now a 1d as pulse_duration is fixed
do0d(pwa.alazar_channels.ch_0_m_time.data)

#%%
pwa.sequencer.sequence.pulse_duration(1e-4)
do0d(pwa.alazar_channels.ch_0_m_time.data)

# NB these two channels can in theory be measured simulatenously but this is
# not yet implemented, CAN get multple channels if they have the same averaging
# settings, eg:
pwa.clear_alazar_channels()
pwa.add_alazar_channel(0, 'm', integrate_time=True, num=1000)
pwa.add_alazar_channel(0, 'p', integrate_time=True, num=1000)
do0d(pwa.alazar_channels.data)

#%% other things you can do
pwa.clear_demodulation_channels()

# add single shot channel, num is now number of reps and will take up
# one dimension, no averaging. Demod types allowed are 'r', 'm', 'i' and 'p'
pwa.add_demodulation_channel(6.9e9)
pwa.add_alazar_channel(0, 'i', integrate_time=False, num=1000, single_shot=True)

# change the template element
pwa.set_sequencer_template(template_element,
    inner_setpoints=('pulse_duration', pulse_durations),
    context={'qubit_marker_duration': 1e-6})

# In general the context (wich together with labels and units comprises the
# sequence_settings)is just updated when a new template is added and this
# context is used to forge all elements, to change or clear it these functions
# exist:
pwa.clear_sequence_settings()
pwa.update_sequence_settings(context={'pulse_pulse_delay': 10e-9},
                             units={'pulse_pulse_delay': 's'})

#%% multiple demod freqs
pwa.clear_demodulation_channels()
pwa.add_demodulation_channel(6.9e9)
pwa.add_demodulation_channel(6.95e9)
pwa.add_alazar_channel(0, 'p', integrate_time=True, num=1000)
pwa.add_alazar_channel(1, 'p', integrate_time=True, num=1000)
do0d(pwa.alazar_channels.data)

# change the drive frequency
pwa.demodulation_channels.ch_0.drive_frequency(6.91e9)
# see what this gives as a sideband
pwa.demodulation_channels.ch_0.sideband_frequency()
# see what this gives as 'total' demodulation_frequency
pwa.demodulation_channels.ch_0.demodulation_frequency()

# change the carrier frequency but keep the drives the same. This
# is slow if we update them one by one as each update requires
# reuploading the sequence to the awg

with pwa.sideband_update():
    pwa.carrier_frequency(7.01e9)
