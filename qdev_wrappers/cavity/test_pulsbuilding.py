# from unittest import TestCase
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Qt5Agg')

from broadbean import Element, BluePrint
from pulsbuilding import joinElements, make_drive_waveform, make_readout_waveform, joint_builder, waveform_builder_from_file
from custom_pulse_atoms import const, zero


def test_joining_elements():
    bpI= BluePrint()
    bpI.insertSegment(0, zero, dur=1)
    bpI.insertSegment(1, const, 1, dur=1)
    bpI.insertSegment(2, zero, dur=1)
    bpI.setSR(10)


    bpQ= BluePrint()
    bpQ.insertSegment(0, zero, dur=1)
    bpQ.insertSegment(1, const, 2, dur=1)
    bpQ.insertSegment(2, zero, dur=1)
    bpQ.setSR(10)

    elem1 = Element()
    elem1.addBluePrint('I', bpI)
    elem1.addBluePrint('Q', bpQ)
    elem2 = Element()
    elem2.addBluePrint('I2', bpI)
    elem2.addBluePrint('Q2', bpQ)
    return joinElements(elem1, elem2)


def testing(**kwargs):
    for k,v in kwargs.items():
        print('{}:{}'.format(k,v))

pulse_parameters = {'readout_delay': 1,
                    'readout_duration': 1,
                    'readout_amplitude': 1,
                    'readout_marker_delay': 1,
                    'readout_marker_duration': 1,
                    'readout_stage_duration': 1,
                    'readout_channel_name' : 'readout_channel',
                    'drive_channel_name' : 'drive_channel',
                    'drive_stage_duration': 1}

def test_make_drive_waveform():
    return make_drive_waveform('testname',**pulse_parameters)

def test_make_readout_waveform():
    return make_readout_waveform('testname_readout',**pulse_parameters)

def test_joint_builder():
    jb = joint_builder(make_drive_waveform, make_readout_waveform)
    return jb(**pulse_parameters)

def test_waveform_builder_from_file():
    # testdict = {delay: 1 }
    testdict = {'readout_delay': 1,
                'readout_duration': 2,
                'readout_frequency': 10,
                'readout_amplitude': 12,
                'readout_stage_duration': 4 ,
                'readout_basename': 'readout_basename_val'}
    func = waveform_builder_from_file('./experimental_puls_description.yml', 'simple_readout')
    print(func(**testdict))


test_waveform_builder_from_file()
