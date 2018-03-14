import io
from contextlib import redirect_stdout, suppress, contextmanager
from functools import partial
import textwrap
import broadbean as bb
from broadbean import Element, PulseAtoms, BluePrint
from custom_pulse_atoms import const, zero
import custom_pulse_atoms
from typing import Dict



# broadbean addtions

# TODO:
# add a test for negative durations
# document insertSegment better -1 for insert


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
import yaml
def waveform_builder_from_file(filename, waveform_name):
    with open(filename, 'r') as f:
        collection = yaml.load(f)
        wave_description = collection[waveform_name]
    # this is the naïve way of building the blueprint
    # might needs replacement for speed
    def builder(**kwargs):
        def val(field, prefix=''):
            if type(field) in (float, int):
                return field
            else:
                return kwargs[prefix + field]
            
        @contextmanager
        def prefixed_val(val, additional_prefix):
            yield lambda field, prefix='': val(field, prefix=additional_prefix+prefix)

        def get_prefix(the_dict, default, prefix='prefix'):
            if prefix in the_dict:
                ret = the_dict[prefix]
                if ret is not None:
                    ret += '_'
                else:
                    ret = ''
            else:
                ret = default + '_'
            return ret
            
        elem = Element()

        with prefixed_val(val, get_prefix(wave_description, default=waveform_name)) as val:
            for channel in wave_description['channels']:
                name_args = channel.get('name_args', None)
                name_args = val(name_args) if name_args else None
                channel_name = channel['name'].format(name_args)
                # create BluePrint
                bp = BluePrint()
                with prefixed_val(val, get_prefix(channel, default=channel_name)) as val:
                    segments = channel['segments']
                    # change out the fill property:
                    i_fill_segment = [i for i,s in enumerate(segments) if 'fill' in s]
                    if len(i_fill_segment) > 1:
                        raise Exception("There can only be one fill segment")
                    elif len(i_fill_segment) == 1:
                        fill_segment = segments[i_fill_segment[0]]
                        if 'dur' in fill_segment:
                            raise Exception("You cannot specify a duration for a fill segment")

                        total_dur = sum(val(s['dur']) for s in segments if 'fill' not in s)
                        fill_segment['dur'] = val(wave_description['dur']) - total_dur
                        del fill_segment['fill']

                    # build blueprint for every segment
                    for segment in channel['segments']:
                        name = segment['atom']
                        with suppress(AttributeError):
                            atom_function = getattr(PulseAtoms, name, None)
                            atom_function = getattr(custom_pulse_atoms, name, atom_function)
                        if atom_function is None:
                            raise Exception(("Could not find pulse atom {}, neither in "
                                            "Broadbean pulse atoms nor in custom "
                                            "pulse atoms").format(name))
                        args = {k:val(v) for k,v in segment.items() if k not in ('atom', 'dur', 'fill')}
                        bp.insertSegment(pos=-1, func=atom_function, args=args, dur=val(segment['dur']))
                elem.addBluePrint(channel_name, bp)
        return elem

    return builder


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
