import io
from contextlib import redirect_stdout
import textwrap
import broadbean as bb
from broadbean import Element, PulseAtoms, BluePrint
from typing import Dict


# atom elements
def const(val, SR, npts):
    return PulseAtoms.ramp(val, val, SR, npts)

def zero(SR, npts):
    return PulseAtoms.ramp(0, 0, SR, npts)

# broadbean addtions

# TODO:
# add a test for negative durations

# in element
def pushElement(self, element: Element) -> None:
    self.addElement(self.length_sequenceelements, element)

Element.pushElement = pushElement

def __repr__(self):
    out = type(self).__name__ + '\n'
    for channel_id in self.channels:
        out += channel_id + ':\n'
        f = io.StringIO()
        # this redirction should be replaced by a stream input for showPrint
        # is this a good idea? possibly not
        with redirect_stdout(f):
            self._data[channel_id]['blueprint'].showPrint()
        out += textwrap.indent(f.getvalue(), '    ')
    return out 

Element.__repr__ = __repr__

def getBluePrint(self, channel) -> BluePrint:
    """
    Gets a blueprint of the element from the specified channel.
    """
    return self._data[channel]['blueprint']

Element.getBluePrint = getBluePrint

# global scope
def joinElements(elem1: Element,
                 elem2: Element,
                 zero_pad: bool=True,
                 overlap_time: float=0)->Element:
    """
    joins two elements by appending elem2 to elem1
    and returns a new atomic element:
    |-~-| |~--| |-~-~--|
    |---|+|~--|=|---~--|
    |---| |~--| |---~--|
    If the channels specified in the two elements differ
    one can choose to do zero padding
    |-~-| |~--| |-~-~--|
     +|~--|=|---~--|
    |---|       |------|
    If the channels are disjunct an overlap can be introduced
    |-~-|       |-~--|
      |~--| |-~--|
     +|~--|=|-~--|
    |---|       |----|
    It should also be possible at some point to join elements
    with overlap that share a common channel
    """
    ids_elem1 = set(elem1.channels)
    ids_elem2 = set(elem2.channels)
    has_same_ids =  ids_elem1 == ids_elem2
    has_common_ids = len(ids_elem1 - ids_elem2) != 0
    if has_common_ids and overlap_time is not 0:
        raise Exception("Overlapp is not supported yet for elements with"
                        " common ids/channels")
    if not has_same_ids and zero_pad == False:
        raise Exception("Tried to join two elements with different"
                        " ids/channels but no permission to zero padding "
                        "was given")
    joint_element = Element()
    for channel_id in ids_elem1 | ids_elem2:
        if channel_id in ids_elem1 - ids_elem2:
            bp1  = elem1.getBluePrint(channel_id)
            bp2 = BluePrint()
            bp2.insertSegment(0, zero, dur=bp1.duration)
        elif channel_id in ids_elem2 - ids_elem1:
            bp2  = elem2.getBluePrint(channel_id)
            bp1 = BluePrint()
            bp1.insertSegment(0, zero, dur=bp2.duration)
        else:
            bp1  = elem1.getBluePrint(channel_id)
            bp2  = elem2.getBluePrint(channel_id)
        joint_element.addBluePrint(channel_id, bp1 + bp2)

    return joint_element


def applyChannelMap(self: Element, channel_map:Dict) -> None:
    pass

# def join_pulses(pulses):
#     return lambda x(parameters): joinElements(puls(parameters) for puls in pulses)


def make_readout_waveform(readout_channel_name:str,
                          readout_delay: float,
                          readout_duration: float,
                          readout_amplitude: float,
                          readout_marker_delay: float,
                          readout_marker_duration: float,
                          readout_stage_duration: float,
                          **kwargs) -> Element:
    readout_post_delay = readout_stage_duration - readout_duration - readout_delay
    bpI= BluePrint()
    bpI.insertSegment(0, const, 0, dur=readout_delay)
    bpI.insertSegment(1, const, readout_amplitude, dur=readout_duration)
    bpI.insertSegment(2, const, 0, dur=readout_post_delay)

    marker = [(readout_delay-readout_marker_delay, readout_marker_duration)]
    bpI.marker1 = marker

    bpQ= BluePrint()
    bpQ.insertSegment(0, const, 0, dur=readout_stage_duration)

    elem = Element()
    elem.addBluePrint(readout_channel_name+'_I', bpI)
    elem.addBluePrint(readout_channel_name+'_Q', bpQ)
    return elem

def make_drive_waveform(drive_channel_name:str,
                        drive_stage_duration: float,
                        **kwargs) -> Element:
    bpQ, bpI= BluePrint(), BluePrint()
    bpQ.insertSegment(0, const, 0, dur=drive_stage_duration)
    bpI.insertSegment(0, const, 0, dur=drive_stage_duration)

    elem = Element()
    elem.addBluePrint(drive_channel_name+'_I', bpI)
    elem.addBluePrint(drive_channel_name+'_Q', bpQ)
    return elem

def joint_builder(builder1, builder2):
    return lambda **kwargs: joinElements(builder1(**kwargs),
                                         builder2(**kwargs))

def make_waveform(base_channel_name:str,
                 readout_delay: float,
                 readout_duration: float,
                 readout_amplitude: float,
                 readout_marker_delay: float,
                 readout_marker_duration: float,
                 readout_stage_duration: float,
                 drive_stage_duration) -> Element:

    drive = create_drive_pulse(base_channel_name,
                               drive_stage_duration)
    readout = create_readout_pulse(base_channel_name,
                                   readout_delay,
                                   readout_duration,
                                   readout_amplitude,
                                   readout_marker_delay,
                                   readout_marker_duration,
                                   readout_stage_duration)

    seq = Sequence()
    seq.addElement(1, drive)
    seq.addElement(2, readout)
