import broadbean as bb
from broadbean import Element

# broadbean addtions
def const(val, SR, npts):
    return bb.PulseAtoms.ramp(val, val, SR, npts)

def joinElements(elems: Iterable[Elemenent],
                 zero_pad_channels: bool=True)
                 -> Element:
    # same ids in all elements
    same_ids = len(set(set(id) for ids in elems.channels())) == 1
    if not same_ids and not zero_pad_channels:
        # find a more precise exception
        raise Exception("The given sets cannot be joined")
    # validate sample rate?
    # handle description
    ret = Element()
    for elem in elems:
        ret

def applyChannelMap(self: Element, channel_map:Dict) -> None:
    pass

def join_pulses(pulses):
    return lambda x(parameters): joinElements(puls(parameters) for puls in pulses)

build(**mydict)

def build_readout_waveform(base_channel_name:str,
                         readout_delay: float,
                         readout_duration: float,
                         readout_amplitude: float,
                         readout_marker_delay: float,
                         readout_marker_duration: float,
                           readout_stage_duration: float,
                           kwargs) -> bb.Element:
    bpI= bb.BluePrint()
    bpI.insertSegment(0, const, 0, dur=delay)
    bpI.insertSegment(1, const, amplitude, dur=duration)
    bpI.insertSegment(2, const, 0, dur=post_delay)

    marker = (delay-marker_delay, marker_duration)
    bp.marker1 = marker

    bpQ= bb.BluePrint()
    bpQ.insertSegment(0, const, 0, dur=stage_duration)

    elem = bb.Element()

    elem.addBluePrint(base_channel_name+'_I', bpI)
    elem.addBluePrint(base_channel_name+'_Q', bpQ)
    return elem

def build_drive_waveform(base_channel_name:str,
                       drive_stage_duration: float) -> bb.Element:
    bpQ, bpI= bb.BluePrint(), bb.BluePrint()
    bpQ.insertSegment(0, const, 0, dur=stage_duration)
    bpI.insertSegment(0, const, 0, dur=stage_duration)

    elem.addBluePrint(base_channel_name+'_I', bpI)
    elem.addBluePrint(base_channel_name+'_Q', bpQ)
    return elem

def create_pulse(base_channel_name:str,
                 readout_delay: float,
                 readout_duration: float,
                 readout_amplitude: float,
                 readout_marker_delay: float,
                 readout_marker_duration: float,
                 readout_stage_duration: float,
                 drive_stage_duration) -> bb.Element:

    drive = create_drive_pulse(base_channel_name,
                               drive_stage_duration)
    readout = create_readout_pulse(base_channel_name,
                                   readout_delay,
                                   readout_duration,
                                   readout_amplitude,
                                   readout_marker_delay,
                                   readout_marker_duration,
                                   readout_stage_duration) -> bb.Element:

    seq = bb.Sequence()
    seq.addElement(1, drive)
    seq.addElement(2, readout)
