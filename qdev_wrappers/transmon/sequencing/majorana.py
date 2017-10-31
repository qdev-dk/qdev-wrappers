import numpy as np
from . import segment_functions
from . import Segment, Waveform, Element, Sequence


def make_stairs_segment(start, stop, step, marker_dur, cycle_time, channel=1):
    step_num = int(round(2 / step) + 1)
    step_dur = cycle_time / step_num
    stairs_segment = Segment(
        name='stairs_ramp',
        gen_func=segment_functions.stairs,
        func_args={'start': -1, 'stop': 1,
                   'step': step, 'dur': cycle_time, 'SR': 10e6},
        time_markers={
            1: {'delay_time': list(np.linspace(0, cycle_time - step_dur, num=step_num)),
                'duration_time': list(np.ones(step_num) * marker_dur)},
            2: {'delay_time': [0], 'duration_time': [marker_dur]}})
    return stairs_segment


def make_stairs_sequence(start, stop, step,
                         marker_dur=1e-6, cycle_time=1e-3, channel=1):
    stairs_segment = make_stairs_segment(start, stop, step, marker_dur,
                                         cycle_time, channel=channel)
    stairs_wf = Waveform(channel=channel, segment_list=[stairs_segment])
    stairs_elem = Element()
    stairs_elem.add_waveform(stairs_wf)
    stairs_seq = Sequence(name='stairs_seq')
    stairs_seq.add_element(stairs_elem)
    return stairs_seq
