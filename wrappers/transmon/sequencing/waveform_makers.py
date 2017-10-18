from . import get_calibration_val, flat_array, \
    cos_multi_array, sin_multi_array

from . import Segment, Waveform


def make_readout_wf(first_in_seq=False, channel=4):
    measurement_segment = Segment(
        name='cavity_measurement',
        gen_func=flat_array,
        func_args={'amp': 1, 'dur': get_calibration_val('readout_time')},
        time_markers={
            1: {'delay_time': [get_calibration_val('marker_readout_delay')],
                'duration_time': [get_calibration_val('marker_time')]}})

    time_before_readout = (get_calibration_val('pulse_end') +
                           get_calibration_val('pulse_readout_delay'))
    time_after_readout = (get_calibration_val('cycle_time') -
                          get_calibration_val('pulse_end') -
                          get_calibration_val('pulse_readout_delay') -
                          get_calibration_val('readout_time'))
    wait1_segment = Segment(
        name='wait_before_measurement', gen_func=flat_array,
        func_args={'amp': 0, 'dur': time_before_readout})
    wait2_segment = Segment(
        name='wait_after_measurement', gen_func=flat_array,
        func_args={'amp': 0, 'dur': time_after_readout})
    readout_wf = Waveform(
        channel=channel,
        segment_list=[wait1_segment, measurement_segment, wait2_segment],
        sample_rate=get_calibration_val('sample_rate'))
    if first_in_seq:
        readout_wf.add_marker(
            2, 0, int(get_calibration_val('marker_time') *
                      get_calibration_val('sample_rate')))
    return readout_wf


def make_readout_ssb_wf_I(freq_list, first_in_seq=False, channel=3):
    measurement_segment = Segment(
        name='cavity_measurement_i',
        gen_func=cos_multi_array,
        func_args={'amp': 1, 'dur': get_calibration_val('readout_time'),
                   'freq_list': freq_list},
        time_markers={
            1: {'delay_time': [get_calibration_val('marker_readout_delay')],
                'duration_time': [get_calibration_val('marker_time')]}})
    time_before_readout = (get_calibration_val('pulse_end') +
                           get_calibration_val('pulse_readout_delay'))
    time_after_readout = (get_calibration_val('cycle_time') -
                          get_calibration_val('pulse_end') -
                          get_calibration_val('pulse_readout_delay') -
                          get_calibration_val('readout_time'))
    wait1_segment = Segment(
        name='wait_before_measurement', gen_func=flat_array,
        func_args={'amp': 0, 'dur': time_before_readout})
    wait2_segment = Segment(
        name='wait_after_measurement', gen_func=flat_array,
        func_args={'amp': 0, 'dur': time_after_readout})
    readout_wf = Waveform(
        channel=channel,
        segment_list=[wait1_segment, measurement_segment, wait2_segment],
        sample_rate=get_calibration_val('sample_rate'))
    if first_in_seq:
        readout_wf.add_marker(
            2, 0, int(get_calibration_val('marker_time') *
                      get_calibration_val('sample_rate')))
    return readout_wf


def make_readout_ssb_wf_Q(freq_list, channel=4):
    measurement_segment = Segment(
        name='cavity_measurement_q',
        gen_func=sin_multi_array,
        func_args={'amp': 1, 'dur': get_calibration_val('readout_time'),
                   'freq_list': freq_list, 'positive': False})
    time_before_readout = (get_calibration_val('pulse_end') +
                           get_calibration_val('pulse_readout_delay'))
    time_after_readout = (get_calibration_val('cycle_time') -
                          get_calibration_val('pulse_end') -
                          get_calibration_val('pulse_readout_delay') -
                          get_calibration_val('readout_time'))
    wait1_segment = Segment(
        name='wait_before_measurement', gen_func=flat_array,
        func_args={'amp': 0, 'dur': time_before_readout})
    wait2_segment = Segment(
        name='wait_after_measurement', gen_func=flat_array,
        func_args={'amp': 0, 'dur': time_after_readout})
    readout_wf = Waveform(
        channel=channel,
        segment_list=[wait1_segment, measurement_segment, wait2_segment],
        sample_rate=get_calibration_val('sample_rate'))
    return readout_wf
