import pytest
import numpy as np

from broadbean import Segment, SegmentGroup, Element, Sequence
from broadbean.atoms import sine, ramp, flat, zero, on, off
from broadbean.types import ForgedSequenceType

from qdev_wrappers.customised_instruments.parametric_sequencer import (ParametricSequencer, AWGInterface)


class VerboseAWGInterface(AWGInterface):

    def upload(self, forged_sequence: ForgedSequenceType):
        print(forged_sequence)

    def step(self):
        print('stepping')

    def get_SR(self):
        return 1e6

@pytest.fixture
def awg():
    return VerboseAWGInterface()


@pytest.fixture
def elem():
    seg1 = zero(duration='flex_time')
    seg2 = flat(duration='pulse_duration', amplitude=1)
    seg3 = zero(duration='flex_time')

    pi_pulse = SegmentGroup(seg1, seg2, seg3,
                            duration='total_duration')

    m1 = off(duration='pre_marker_time')
    m2 = on(duration='marker_time')
    m3 = off(duration='post_marker_time')

    markers = SegmentGroup(m1, m2, m3,
                           duration='total_duration')

    def mytransformation(context):
        context['flex_time'] = 0.5*(context['total_duration'] - context['pulse_duration'])
        context['pre_marker_time'] = context['flex_time'] + context['marker_delay']
        context['post_marker_time'] = context['total_duration'] - context['marker_time'] - context['pre_marker_time']

    e = Element({1: pi_pulse,
                '1M1': markers},
                transformation=mytransformation)
    return e


@pytest.fixture
def context():
    return {'total_duration': 3e-3,
            'marker_time': 2e-4,
            'marker_delay': 5e-4,
            'pulse_duration': 0.5e-3}
@pytest.fixture
def setpoints():
    return {'symbol': 'pulse_duration',
            'label': 'Pulse Duration',
            'unit': 's',
            'values': np.linspace(0.5e-3,2e-3,5)}


@pytest.fixture
def ps(awg, elem, context, setpoints):
    return ParametricSequencer(name='PS',
                               awg=awg,
                               template_element=elem,
                               context=context,
                               setpoints=setpoints)
 
def test_initialization(ps):
    print(ps.name)

def test_upload(ps):
    ps._upload_sequence()
