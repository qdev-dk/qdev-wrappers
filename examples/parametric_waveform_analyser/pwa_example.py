import numpy as np
from qdev_wrappers.station_configurator import StationConfigurator
from qdev_wrappers.customised_instruments.heterodyne_source import HeterodyneSource
from qdev_wrappers.customised_instruments.parametric_sequencer import ParametricSequencer
from qdev_wrappers.customised_instruments.parametric_waveform_analyser import ParametricWaveformAnalyser
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
           'pulse_amplitude': 1}

labels = {'total_duration': 'Total Duration',
          'marker_time': 'Marker Time',
          'marker_delay': 'Marker Delay',
          'pulse_duration': 'Pulse Duration',
          'pulse_amplitude': 'Pulse Amplitude'}

units = {'total_duration': 's',
         'marker_time': 's',
         'marker_delay': 's',
         'pulse_duration': 's',
         'pulse_amplitude': ''}

settings_dict = {'context': context, 'units': units, 'labels': labels}

pulse_durations = np.linspace(0e-4, 2.9e-4, 3)

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

pwa.base_demodulation_frequency(15e6)
pwa.carrier_frequency(7e9)
pwa.add_demodulation_channel(7e9)
pwa.add_alazar_channel()

