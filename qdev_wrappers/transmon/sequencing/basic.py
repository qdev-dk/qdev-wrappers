from . import make_readout_wf, get_calibration_val, \
    make_time_varying_sequence, make_varying_sequence, \
    cos_array, sin_array, flat_array, gaussian_array, cos_gaussian_array, \
    sin_gaussian_array, make_readout_ssb_wf_I, make_readout_ssb_wf_Q
from . import Segment, Waveform, Element, Sequence

# TODO: T2 echo
# TODO: checks
# TODO: drag
# TODO: Exception types

###############################################################
# Single Element Sequences
###############################################################


def make_readout_single_sequence(channels=[4]):
    seq = Sequence(name='readout_seq')
    element = Element(sample_rate=get_calibration_val('sample_rate'))
    readout_wf = make_readout_wf(first_in_seq=True, channel=channels[0])
    element.add_waveform(readout_wf)
    seq.add_element(element)
    seq.labels = {'seq_type': 'readout'}
    return seq


def make_readout_SSB_single_sequence(freq_list, channels=[3, 4]):
    seq = Sequence(name='readout_SSB_seq')
    element = Element(sample_rate=get_calibration_val('sample_rate'))
    readout_wf_I = make_readout_ssb_wf_I(freq_list, first_in_seq=True,
                                         channel=channels[0])
    readout_wf_Q = make_readout_ssb_wf_Q(freq_list, channel=channels[1])
    element.add_waveform(readout_wf_I)
    element.add_waveform(readout_wf_Q)
    seq.add_element(element)
    seq.labels = {'seq_type': 'readout_SSB', 'freq_list': freq_list}
    return seq


def make_calib_SSB_single_sequence(freq, amp=1, dur=None, channels=[1, 2]):
    dur = dur or get_calibration_val('cycle_time')

    seq = Sequence(name='ssb_calib_seq')
    sr = get_calibration_val('sample_rate')
    element = Element(sample_rate=sr)
    waveform_i = Waveform(channel=channels[0])
    waveform_q = Waveform(channel=channels[1])
    waveform_i.wave = cos_array(
        freq, amp, dur, sr)
    waveform_q.wave = sin_array(
        freq, amp, dur, sr)
    element.add_waveform(waveform_i)
    element.add_waveform(waveform_q)
    seq.add_element(element)
    return seq

################################################################
# Readout SSB sweep
################################################################


def make_readout_SSB_sequence(start, stop, step, channels=[3, 4]):
    if len(channels) < 2:
        raise Exception('2 channels needed for single sideband sequence for'
                        ' I and Q')
    sr = get_calibration_val('sample_rate')
    element = Element(sample_rate=sr)
    readout_wf_I = make_readout_ssb_wf_I([1e-6], channel=channels[0])
    readout_wf_Q = make_readout_ssb_wf_Q([1e-6], channel=channels[1])
    element.add_waveform(readout_wf_I)
    element.add_waveform(readout_wf_Q)
    marker_points = int(get_calibration_val('marker_time') * sr)
    seq = make_varying_sequence(
        element, channels[0], 1, 'freq', start, stop, step,
        channels[1], 1, 'freq', start, stop, step, name="reabout_SSB_sequence",
        variable_name='LSB_drive_detuning', variable_unit='Hz',
        readout_ch=channels[1], marker_points=marker_points)
    seq.labels = {'seq_type': 'readout_SSB'}
    return seq

################################################################
# Spectroscopy
################################################################


def make_spectroscopy_SSB_sequence(start, stop, step, channels=[1, 2, 4],
                                   pulse_mod=False, readout_SSBfreqs=None):
    if len(channels) < 3:
        raise Exception('3 channels needed for single sideband sequence for'
                        ' I, Q and readout')

    if pulse_mod:
        pmtime = get_calibration_val('pulse_mod_time')
        pulse_mod_markers = {
            1: {'delay_time': [-1 * pmtime],
                'duration_time': [pmtime]}}
    else:
        pulse_mod_markers = None

    sr = get_calibration_val('sample_rate')
    spec_time = get_calibration_val('qubit_spec_time')
    pulse_end = get_calibration_val('pulse_end')
    cycle_time = get_calibration_val('cycle_time')
    time_before_qubit = (pulse_end - spec_time)
    time_after_qubit = (cycle_time - pulse_end)
    before_qubit_wait_segment = Segment(
        name='wait', gen_func=flat_array,
        func_args={'amp': 0, 'dur': time_before_qubit})
    variable_qubit_drive_I_segment = Segment(
        name='SSB_drive_I', gen_func=cos_array,
        func_args={'amp': 1, 'dur': spec_time})
    variable_qubit_drive_Q_segment = Segment(
        name='SSB_drive_Q', gen_func=sin_array,
        func_args={'amp': 1, 'dur': spec_time,
                   'positive': False})
    after_qubit_wait_segment = Segment(
        name='wait', gen_func=flat_array,
        func_args={'amp': 0, 'dur': time_after_qubit},
        time_markers=pulse_mod_markers)

    ssb_I_wf = Waveform(
        channel=channels[0],
        segment_list=[before_qubit_wait_segment,
                      variable_qubit_drive_I_segment,
                      after_qubit_wait_segment])
    ssb_Q_wf = Waveform(
        channel=channels[1],
        segment_list=[before_qubit_wait_segment,
                      variable_qubit_drive_Q_segment,
                      after_qubit_wait_segment])

    ssb_element = Element(sample_rate=sr)
    ssb_element.add_waveform(ssb_I_wf)
    ssb_element.add_waveform(ssb_Q_wf)

    if readout_SSBfreqs is not None:
        if len(channels) != 4:
            raise Exception('Not enough channels for SSB readout and qubit')
        readout_wf_I = make_readout_ssb_wf_I(readout_SSBfreqs,
                                             channel=channels[-2])
        readout_wf_Q = make_readout_ssb_wf_Q(readout_SSBfreqs,
                                             channel=channels[-1])
        ssb_element.add_waveform(readout_wf_I)
        ssb_element.add_waveform(readout_wf_Q)
    else:
        readout_wf = make_readout_wf(channel=channels[-1])
        ssb_element.add_waveform(readout_wf)

    marker_time = get_calibration_val('marker_time')
    marker_points = int(marker_time * sr)
    vary_args_list = [(channels[0], 1, 'freq'), (channels[1], 1, 'freq')]
    vary_settings_list = [(start, stop, step)] * 2
    ssb_seq = make_varying_sequence(
        ssb_element, vary_args_list, vary_settings_list, name="ssb_sequence",
        variable_name='LSB_drive_detuning', variable_unit='Hz',
        readout_ch=channels[-1], marker_points=marker_points)
    ssb_seq.labels = {'seq_type': 'spectroscopy', 'pulse_mod': pulse_mod}
    ssb_seq.labels = {'seq_type': 'spectroscopy', 'pulse_mod': pulse_mod,
                      'readoutSSBfreqs': readout_SSBfreqs}
    return ssb_seq


################################################################
# Rabi and T1
################################################################


def _make_rabi_carrier_sequence(start, stop, step, pi_amp=None,
                                channels=[1, 4], pulse_mod=False,
                                gaussian=True, readout_SSBfreqs=None):
    pi_amp = pi_amp or get_calibration_val('pi_pulse_amp')

    time_after_qubit = (get_calibration_val('cycle_time') -
                        get_calibration_val('pulse_end'))

    if pulse_mod:
        pmtime = get_calibration_val('pulse_mod_time')
        pulse_mod_markers = {
            1: {'delay_time': [-1 * pmtime],
                'duration_time': [pmtime]}}
    else:
        pulse_mod_markers = None

    compensating_wait_segment = Segment(
        name='compensating_wait', gen_func=flat_array, func_args={'amp': 0})

    if gaussian:
        variable_pi_segment = Segment(
            name='gaussian_pi_pulse', gen_func=gaussian_array,
            func_args={'sigma_cutoff': get_calibration_val('sigma_cutoff'),
                       'amp': pi_amp})
        variable_arg = 'sigma'
    else:
        variable_pi_segment = Segment(
            name='square_pi_pulse', gen_func=flat_array,
            func_args={'amp': pi_amp})
        variable_arg = 'dur'

    wait_segment = Segment(name='wait', gen_func=flat_array,
                           func_args={'amp': 0, 'dur': time_after_qubit},
                           time_markers=pulse_mod_markers)
    rabi_wf = Waveform(
        channel=channels[0],
        segment_list=[compensating_wait_segment, variable_pi_segment,
                      wait_segment])

    sr = get_calibration_val('sample_rate')
    rabi_element = Element(sample_rate=sr)
    rabi_element.add_waveform(rabi_wf)

    if readout_SSBfreqs is not None:
        if len(channels) != 3:
            raise Exception('Not enough channels for SSB readout')
        readout_wf_I = make_readout_ssb_wf_I(readout_SSBfreqs,
                                             channel=channels[-2])
        readout_wf_Q = make_readout_ssb_wf_Q(readout_SSBfreqs,
                                             channel=channels[-1])
        rabi_element.add_waveform(readout_wf_I)
        rabi_element.add_waveform(readout_wf_Q)
    else:
        readout_wf = make_readout_wf(channel=channels[-1])
        rabi_element.add_waveform(readout_wf)

    vary_args_list = [(channels[0], 1, variable_arg, 0)]
    vary_settings_list = [(start, stop, step)]

    marker_points = int(get_calibration_val('marker_time') * sr)
    rabi_sequence = make_time_varying_sequence(
        rabi_element, vary_args_list, vary_settings_list,
        get_calibration_val('cycle_time'), name='rabi_seq',
        variable_name='pi_pulse_' + variable_arg, variable_unit='s',
        readout_ch=channels[-1], marker_points=marker_points)
    return rabi_sequence


def _make_rabi_SSB_sequence(start, stop, step, SSBfreq, channels=[1, 2, 4],
                            gaussian=True, pulse_mod=False,
                            pi_amp=None, readout_SSBfreqs=None):
    pi_amp = pi_amp or get_calibration_val('pi_pulse_amp')

    time_after_qubit = (get_calibration_val('cycle_time') -
                        get_calibration_val('pulse_end'))

    if pulse_mod:
        pmtime = get_calibration_val('pulse_mod_time')
        pulse_mod_markers = {
            1: {'delay_time': [-1 * pmtime],
                'duration_time': [pmtime]}}
    else:
        pulse_mod_markers = None

    compensating_wait_segment_I = Segment(
        name='compensating_wait', gen_func=flat_array, func_args={'amp': 0})
    compensating_wait_segment_Q = Segment(
        name='compensating_wait', gen_func=flat_array, func_args={'amp': 0})

    if gaussian:
        variable_pi_I_segment = Segment(
            name='gaussian_SSB_pi_I_pulse', gen_func=cos_gaussian_array,
            func_args={
                'sigma_cutoff': get_calibration_val('sigma_cutoff'),
                'amp': pi_amp, 'SSBfreq': SSBfreq})
        variable_pi_Q_segment = Segment(
            name='gaussian_SSB_pi_Q_pulse', gen_func=sin_gaussian_array,
            func_args={
                'sigma_cutoff': get_calibration_val('sigma_cutoff'),
                'amp': pi_amp, 'SSBfreq': SSBfreq, 'positive': False})
        variable_arg = 'sigma'
    else:
        variable_pi_I_segment = Segment(
            name='square_SSB_pi_I_pulse', gen_func=cos_array,
            func_args={'amp': pi_amp, 'freq': SSBfreq})
        variable_pi_Q_segment = Segment(
            name='square__SSB_pi_Q_pulse', gen_func=sin_array,
            func_args={'amp': pi_amp, 'freq': SSBfreq, 'positive': False})
        variable_arg = 'dur'

    wait_segment = Segment(
        name='wait', gen_func=flat_array,
        func_args={'amp': 0, 'dur': time_after_qubit},
        time_markers=pulse_mod_markers)

    rabi_I_wf = Waveform(
        channel=channels[0],
        segment_list=[compensating_wait_segment_I, variable_pi_I_segment,
                      wait_segment])
    rabi_Q_wf = Waveform(
        channel=channels[1],
        segment_list=[compensating_wait_segment_Q, variable_pi_Q_segment,
                      wait_segment])

    rabi_element = Element(sample_rate=get_calibration_val('sample_rate'))
    rabi_element.add_waveform(rabi_I_wf)
    rabi_element.add_waveform(rabi_Q_wf)

    if readout_SSBfreqs is not None:
        if len(channels) != 4:
            raise Exception('Not enough channels for SSB readout and qubit')
        readout_wf_I = make_readout_ssb_wf_I(readout_SSBfreqs,
                                             channel=channels[-2])
        readout_wf_Q = make_readout_ssb_wf_Q(readout_SSBfreqs,
                                             channel=channels[-1])
        rabi_element.add_waveform(readout_wf_I)
        rabi_element.add_waveform(readout_wf_Q)
    else:
        readout_wf = make_readout_wf(channel=channels[-1])
        rabi_element.add_waveform(readout_wf)

    vary_args_list = [(channels[0], 1, variable_arg, 0),
                      (channels[1], 1, variable_arg, 0)]
    vary_settings_list = [(start, stop, step)] * 2

    marker_points = int(get_calibration_val('marker_time') *
                        get_calibration_val('sample_rate'))
    rabi_sequence = make_time_varying_sequence(
        rabi_element, vary_args_list, vary_settings_list,
        get_calibration_val('cycle_time'), name='rabi_ssb_seq',
        variable_name='pi_pulse_' + variable_arg, variable_unit='s',
        readout_ch=channels[-1], marker_points=marker_points)
    return rabi_sequence


def make_rabi_sequence(start, stop, step, SSBfreq=None, channels=[1, 2, 4],
                       pulse_mod=False, pi_amp=None, gaussian=True,
                       readout_SSBfreqs=None):
    if SSBfreq is not None:
        if len(channels) < 3:
            raise Exception('at least 3 channels needed for single sideband '
                            'sequence for I, Q and readout')
        seq = _make_rabi_SSB_sequence(
            start, stop, step, SSBfreq, channels=channels, pulse_mod=pulse_mod,
            pi_amp=pi_amp, gaussian=gaussian,
            readout_SSBfreqs=readout_SSBfreqs)
    else:
        if len(channels) < 2:
            raise Exception('at least 2 channels needed for drive and readout')
        seq = _make_rabi_carrier_sequence(
            start, stop, step, channels=[channels[0], channels[-1]],
            pulse_mod=pulse_mod, pi_amp=pi_amp, gaussian=gaussian)
    seq.labels = {'qubitSSBfreq': SSBfreq, 'seq_type': 'rabi',
                  'gaussian': gaussian, 'drag': False,
                  'pulse_mod': pulse_mod,
                  'readoutSSBfreqs': readout_SSBfreqs}
    return seq


def _make_t1_carrier_sequence(start, stop, step, pi_dur=None, pi_amp=None,
                              channels=[1, 4], gaussian=True, pulse_mod=False,
                              readout_SSBfreqs=None):
    pi_amp = pi_amp or get_calibration_val('pi_pulse_amp')

    time_after_qubit = (get_calibration_val('cycle_time') -
                        get_calibration_val('pulse_end'))

    if pulse_mod:
        pmtime = get_calibration_val('pulse_mod_time')
        pulse_mod_markers = {
            1: {'delay_time': [-1 * pmtime],
                'duration_time': [pmtime]}}
    else:
        pulse_mod_markers = None

    compensating_wait_segment = Segment(
        name='compensating_wait', gen_func=flat_array, func_args={'amp': 0})
    if gaussian:
        pi_sigma = pi_dur or get_calibration_val('pi_pulse_sigma')
        pi_segment = Segment(
            name='gaussian_pi_pulse', gen_func=gaussian_array,
            func_args={
                'sigma_cutoff': get_calibration_val('sigma_cutoff'),
                'amp': pi_amp, 'sigma': pi_sigma})
    else:
        pi_dur = pi_dur or get_calibration_val('pi_pulse_dur')
        pi_segment = Segment(
            name='square_pi_pulse', gen_func=flat_array,
            func_args={'amp': pi_amp, 'dur': pi_dur})

    variable_wait_segment = Segment(
        name='pulse_readout_delay', gen_func=flat_array,
        func_args={'amp': 0})

    wait_segment = Segment(
        name='wait', gen_func=flat_array,
        func_args={'amp': 0, 'dur': time_after_qubit},
        time_markers=pulse_mod_markers)

    t1_wf = Waveform(
        channel=channels[0],
        segment_list=[compensating_wait_segment, pi_segment,
                      variable_wait_segment, wait_segment])

    t1_element = Element(sample_rate=get_calibration_val('sample_rate'))
    t1_element.add_waveform(t1_wf)

    if readout_SSBfreqs is not None:
        if len(channels) != 3:
            raise Exception('Not enough channels for SSB readout')
        readout_wf_I = make_readout_ssb_wf_I(readout_SSBfreqs,
                                             channel=channels[-2])
        readout_wf_Q = make_readout_ssb_wf_Q(readout_SSBfreqs,
                                             channel=channels[-1])
        t1_element.add_waveform(readout_wf_I)
        t1_element.add_waveform(readout_wf_Q)
    else:
        readout_wf = make_readout_wf(channel=channels[-1])
        t1_element.add_waveform(readout_wf)

    marker_points = int(get_calibration_val('marker_time') *
                        get_calibration_val('sample_rate'))

    vary_args_list = [(channels[0], 2, 'dur', 0)]
    vary_settings_list = [(start, stop, step)]

    t1_sequence = make_time_varying_sequence(
        t1_element, vary_args_list, vary_settings_list,
        get_calibration_val('cycle_time'), name='t1_seq',
        variable_name='pi_pulse_readout_delay', variable_unit='s',
        readout_ch=channels[-1], marker_points=marker_points)
    return t1_sequence


def _make_t1_SSB_sequence(start, stop, step, SSBfreq, pi_dur=None,
                          pi_amp=None, channels=[1, 2, 4], gaussian=True,
                          pulse_mod=False, readout_SSBfreqs=None):
    pi_amp = pi_amp or get_calibration_val('pi_pulse_amp')
    time_after_qubit = (get_calibration_val('cycle_time') -
                        get_calibration_val('pulse_end'))

    if pulse_mod:
        pmtime = get_calibration_val('pulse_mod_time')
        pulse_mod_markers = {
            1: {'delay_time': [-1 * pmtime],
                'duration_time': [pmtime]}}
    else:
        pulse_mod_markers = None

    compensating_wait_segment_I = Segment(
        name='compensating_wait', gen_func=flat_array, func_args={'amp': 0})
    compensating_wait_segment_Q = Segment(
        name='compensating_wait', gen_func=flat_array, func_args={'amp': 0})

    if gaussian:
        pi_sigma = pi_dur or get_calibration_val('pi_pulse_sigma')
        pi_I_segment = Segment(
            name='gaussian_SSB_pi_I_pulse', gen_func=cos_gaussian_array,
            func_args={
                'sigma_cutoff': get_calibration_val('sigma_cutoff'),
                'amp': pi_amp, 'SSBfreq': SSBfreq, 'sigma': pi_sigma})
        pi_Q_segment = Segment(
            name='gaussian_SSB_pi_Q_pulse', gen_func=sin_gaussian_array,
            func_args={
                'sigma_cutoff': get_calibration_val('sigma_cutoff'),
                'amp': pi_amp,
                'SSBfreq': SSBfreq, 'sigma': pi_sigma, 'positive': False})
    else:
        pi_dur = pi_dur or get_calibration_val('pi_pulse_dur')
        pi_I_segment = Segment(
            name='square_SSB_pi_I_pulse', gen_func=cos_array,
            func_args={'amp': pi_amp, 'freq': SSBfreq, 'dur': pi_dur})
        pi_Q_segment = Segment(
            name='square_SSB_pi_Q_pulse', gen_func=sin_array,
            func_args={'amp': pi_amp, 'freq': SSBfreq, 'dur': pi_dur,
                       'positive': False})

    variable_wait_segment = Segment(
        name='pulse_readout_delay', gen_func=flat_array,
        func_args={'amp': 0})

    wait_segment = Segment(
        name='wait', gen_func=flat_array,
        func_args={'amp': 0, 'dur': time_after_qubit},
        time_markers=pulse_mod_markers)

    t1_I_wf = Waveform(
        channel=channels[0],
        segment_list=[compensating_wait_segment_I, pi_I_segment,
                      variable_wait_segment, wait_segment])
    t1_Q_wf = Waveform(
        channel=channels[1],
        segment_list=[compensating_wait_segment_Q, pi_Q_segment,
                      variable_wait_segment, wait_segment])

    t1_element = Element(sample_rate=get_calibration_val('sample_rate'))
    t1_element.add_waveform(t1_I_wf)
    t1_element.add_waveform(t1_Q_wf)

    if readout_SSBfreqs is not None:
        if len(channels) != 4:
            raise Exception('Not enough channels for SSB readout and qubit')
        readout_wf_I = make_readout_ssb_wf_I(readout_SSBfreqs,
                                             channel=channels[-2])
        readout_wf_Q = make_readout_ssb_wf_Q(readout_SSBfreqs,
                                             channel=channels[-1])
        t1_element.add_waveform(readout_wf_I)
        t1_element.add_waveform(readout_wf_Q)
    else:
        readout_wf = make_readout_wf(channel=channels[-1])
        t1_element.add_waveform(readout_wf)

    marker_points = int(get_calibration_val('marker_time') *
                        get_calibration_val('sample_rate'))

    vary_args_list = [(channels[0], 2, 'dur', 0),
                      (channels[1], 2, 'dur', 0)]
    vary_settings_list = [(start, stop, step)] * 2

    t1_sequence = make_time_varying_sequence(
        t1_element, vary_args_list, vary_settings_list,
        get_calibration_val('cycle_time'), name='t1_ssb_seq',
        variable_name='pi_pulse_readout_delay', variable_unit='s',
        readout_ch=channels[-1], marker_points=marker_points)
    return t1_sequence


def make_t1_sequence(start, stop, step, SSBfreq=None, pi_dur=None,
                     pi_amp=None, channels=[1, 2, 4], gaussian=True,
                     pulse_mod=False, readout_SSBfreqs=None):
    if SSBfreq is not None:
        if len(channels) < 3:
            raise Exception('at least 3 channels needed for single sideband '
                            'sequence for I, Q and readout')
        seq = _make_t1_SSB_sequence(
            start, stop, step, SSBfreq, channels=channels, pulse_mod=pulse_mod,
            pi_amp=pi_amp, pi_dur=pi_dur, gaussian=gaussian,
            readout_SSBfreqs=readout_SSBfreqs)
    else:
        if len(channels) < 2:
            raise Exception('at least 2 channels needed for drive and readout')
        seq = _make_t1_carrier_sequence(
            start, stop, step, channels=[channels[0], channels[-1]],
            pulse_mod=pulse_mod, pi_amp=pi_amp, pi_dur=pi_dur,
            gaussian=gaussian)
    seq.labels = {'qubitSSBfreq': SSBfreq, 'seq_type': 't1',
                  'gaussian': gaussian, 'drag': False,
                  'pulse_mod': pulse_mod,
                  'readoutSSBfreqs': readout_SSBfreqs}
    return seq


################################################################
# Ramsey and T2
################################################################


def _make_ramsey_carrier_sequence(start, stop, step, pi_half_amp=None,
                                  channels=[1, 4], pulse_mod=False,
                                  gaussian=True, readout_SSBfreqs=None):
    pi_half_amp = pi_half_amp or get_calibration_val('pi_half_pulse_amp')

    time_after_qubit = (get_calibration_val('cycle_time') -
                        get_calibration_val('pulse_end'))

    if pulse_mod:
        pmtime = get_calibration_val('pulse_mod_time')
        pulse_mod_markers = {
            1: {'delay_time': [-1 * pmtime],
                'duration_time': [pmtime]}}
    else:
        pulse_mod_markers = None

    compensating_wait_segment = Segment(
        name='compensating_wait', gen_func=flat_array, func_args={'amp': 0})

    if gaussian:
        pi_half_sigma = get_calibration_val('pi_pulse_sigma')
        pi_half_segment = Segment(
            name='gaussian_pi_pulse', gen_func=gaussian_array,
            func_args={'sigma_cutoff': get_calibration_val('sigma_cutoff'),
                       'amp': pi_half_amp, 'sigma': pi_half_sigma})
    else:
        pi_half_dur = get_calibration_val('pi_pulse_dur')
        pi_half_segment = Segment(
            name='square_pi_pulse', gen_func=flat_array,
            func_args={'amp': pi_half_amp, 'dur': pi_half_dur})

    variable_wait_segment = Segment(
        name='pulse_pulse_delay', gen_func=flat_array,
        func_args={'amp': 0})

    wait_segment = Segment(
        name='wait', gen_func=flat_array,
        func_args={'amp': 0, 'dur': time_after_qubit},
        time_markers=pulse_mod_markers)

    ramsey_wf = Waveform(
        channel=channels[0],
        segment_list=[compensating_wait_segment, pi_half_segment,
                      variable_wait_segment, pi_half_segment,
                      wait_segment])

    ramsey_element = Element(sample_rate=get_calibration_val('sample_rate'))
    ramsey_element.add_waveform(ramsey_wf)

    if readout_SSBfreqs is not None:
        if len(channels) != 3:
            raise Exception('Not enough channels for SSB readout')
        readout_wf_I = make_readout_ssb_wf_I(readout_SSBfreqs,
                                             channel=channels[-2])
        readout_wf_Q = make_readout_ssb_wf_Q(readout_SSBfreqs,
                                             channel=channels[-1])
        ramsey_element.add_waveform(readout_wf_I)
        ramsey_element.add_waveform(readout_wf_Q)
    else:
        readout_wf = make_readout_wf(channel=channels[-1])
        ramsey_element.add_waveform(readout_wf)

    marker_points = int(get_calibration_val('marker_time') *
                        get_calibration_val('sample_rate'))

    vary_args_list = [(channels[0], 2, 'dur', 0)]
    vary_settings_list = [(start, stop, step)]

    ramsey_sequence = make_time_varying_sequence(
        ramsey_element, vary_args_list, vary_settings_list,
        get_calibration_val('cycle_time'), name='ramsey_seq',
        variable_name='pi_half_pulse_pi_half_pulse_delay', variable_unit='s',
        readout_ch=channels[-1], marker_points=marker_points)
    return ramsey_sequence


def _make_ramsey_SSB_sequence(start, stop, step, SSBfreq, pi_half_amp=None,
                              channels=[1, 2, 4], pulse_mod=False,
                              gaussian=True, readout_SSBfreqs=None):
    pi_half_amp = pi_half_amp or get_calibration_val('pi_half_pulse_amp')

    time_after_qubit = (get_calibration_val('cycle_time') -
                        get_calibration_val('pulse_end'))

    if pulse_mod:
        pmtime = get_calibration_val('pulse_mod_time')
        pulse_mod_markers = {
            1: {'delay_time': [-1 * pmtime],
                'duration_time': [pmtime]}}
    else:
        pulse_mod_markers = None

    compensating_wait_segment_I = Segment(
        name='compensating_wait', gen_func=flat_array, func_args={'amp': 0})
    compensating_wait_segment_Q = Segment(
        name='compensating_wait', gen_func=flat_array, func_args={'amp': 0})

    if gaussian:
        pi_half_sigma = get_calibration_val('pi_pulse_sigma')
        pi_half_I_segment = Segment(
            name='gaussian_SSB_pi_half_I_pulse', gen_func=cos_gaussian_array,
            func_args={'sigma_cutoff': get_calibration_val('sigma_cutoff'),
                       'amp': pi_half_amp, 'SSBfreq': SSBfreq,
                       'sigma': pi_half_sigma})
        pi_half_Q_segment = Segment(
            name='gaussian_SSB_pi_half_Q_pulse', gen_func=sin_gaussian_array,
            func_args={'sigma_cutoff': get_calibration_val('sigma_cutoff'),
                       'amp': pi_half_amp, 'SSBfreq': SSBfreq,
                       'sigma': pi_half_sigma, 'positive': False})
    else:
        pi_half_dur = get_calibration_val('pi_pulse_dur')
        pi_half_I_segment = Segment(
            name='square_SSB_pi_half_I_pulse', gen_func=cos_array,
            func_args={'amp': pi_half_amp, 'freq': SSBfreq,
                       'dur': pi_half_dur})
        pi_half_Q_segment = Segment(
            name='square_SSB_pi_half_Q_pulse', gen_func=sin_array,
            func_args={'amp': pi_half_amp, 'freq': SSBfreq,
                       'dur': pi_half_dur, 'positive': False})

    variable_wait_segment = Segment(
        name='pulse_readout_delay', gen_func=flat_array,
        func_args={'amp': 0})

    wait_segment = Segment(
        name='wait', gen_func=flat_array,
        func_args={'amp': 0, 'dur': time_after_qubit},
        time_markers=pulse_mod_markers)

    ramsey_I_wf = Waveform(
        channel=channels[0],
        segment_list=[compensating_wait_segment_I, pi_half_I_segment,
                      variable_wait_segment, pi_half_I_segment, wait_segment])
    ramsey_Q_wf = Waveform(
        channel=channels[1],
        segment_list=[compensating_wait_segment_Q, pi_half_Q_segment,
                      variable_wait_segment, pi_half_Q_segment, wait_segment])

    ramsey_element = Element(sample_rate=get_calibration_val('sample_rate'))
    ramsey_element.add_waveform(ramsey_I_wf)
    ramsey_element.add_waveform(ramsey_Q_wf)

    if readout_SSBfreqs is not None:
        if len(channels) != 4:
            raise Exception('Not enough channels for SSB readout and qubit')
        readout_wf_I = make_readout_ssb_wf_I(readout_SSBfreqs,
                                             channel=channels[-2])
        readout_wf_Q = make_readout_ssb_wf_Q(readout_SSBfreqs,
                                             channel=channels[-1])
        ramsey_element.add_waveform(readout_wf_I)
        ramsey_element.add_waveform(readout_wf_Q)
    else:
        readout_wf = make_readout_wf(channel=channels[-1])
        ramsey_element.add_waveform(readout_wf)

    marker_points = int(get_calibration_val('marker_time') *
                        get_calibration_val('sample_rate'))

    vary_args_list = [(channels[0], 2, 'dur', 0),
                      (channels[1], 2, 'dur', 0)]
    vary_settings_list = [(start, stop, step)] * 2

    ramsey_sequence = make_time_varying_sequence(
        ramsey_element, vary_args_list, vary_settings_list,
        get_calibration_val('cycle_time'), name='ramsey_ssb_seq',
        variable_name='pi_half_pulse_pi_half_pulse_delay', variable_unit='s',
        readout_ch=channels[-1], marker_points=marker_points)
    return ramsey_sequence


def make_ramsey_sequence(start, stop, step, SSBfreq=None, pi_half_amp=None,
                         channels=[1, 2, 4], pulse_mod=False,
                         gaussian=True, readout_SSBfreqs=None):
    if SSBfreq is not None:
        if len(channels) < 3:
            raise Exception('at least 3 channels needed for single sideband '
                            'sequence for I, Q and readout')
        seq = _make_ramsey_SSB_sequence(
            start, stop, step, SSBfreq, channels=channels, pulse_mod=pulse_mod,
            pi_half_amp=pi_half_amp,
            gaussian=gaussian, readout_SSBfreqs=readout_SSBfreqs)
    else:
        if len(channels) < 2:
            raise Exception('at least 2 channels needed for drive and readout')
        seq = _make_ramsey_carrier_sequence(
            start, stop, step, channels=[channels[0], channels[-1]],
            pulse_mod=pulse_mod, pi_half_amp=pi_half_amp, gaussian=gaussian)
    seq.labels = {'qubitSSBfreq': SSBfreq, 'seq_type': 'ramsey',
                  'gaussian': gaussian, 'drag': False,
                  'pulse_mod': pulse_mod,
                  'readoutSSBfreqs': readout_SSBfreqs}
    return seq


################################################################
# T2 echo
################################################################

def _make_echo_carrier_sequence(start, stop, step, pi_half_amp=None,
                                pi_amp=None,
                                channels=[1, 4], pulse_mod=False,
                                gaussian=True, readout_SSBfreqs=None):
    pi_half_amp = pi_half_amp or get_calibration_val('pi_half_pulse_amp')
    pi_amp = pi_amp or get_calibration_val('pi_pulse_amp')

    time_after_qubit = (get_calibration_val('cycle_time') -
                        get_calibration_val('pulse_end'))

    if pulse_mod:
        pmtime = get_calibration_val('pulse_mod_time')
        pulse_mod_markers = {
            1: {'delay_time': [-1 * pmtime],
                'duration_time': [pmtime]}}
    else:
        pulse_mod_markers = None

    compensating_wait_segment = Segment(
        name='compensating_wait', gen_func=flat_array, func_args={'amp': 0})

    if gaussian:
        pi_half_sigma = get_calibration_val('pi_pulse_sigma')
        pi_half_segment = Segment(
            name='gaussian_pi_pulse', gen_func=gaussian_array,
            func_args={'sigma_cutoff': get_calibration_val('sigma_cutoff'),
                       'amp': pi_half_amp, 'sigma': pi_half_sigma})
        pi_sigma = get_calibration_val('pi_pulse_sigma')
        pi_segment = Segment(
            name='gaussian_pi_pulse', gen_func=gaussian_array,
            func_args={
                'sigma_cutoff': get_calibration_val('sigma_cutoff'),
                'amp': pi_amp, 'sigma': pi_sigma})
    else:
        pi_half_dur = get_calibration_val('pi_pulse_dur')
        pi_half_segment = Segment(
            name='square_pi_pulse', gen_func=flat_array,
            func_args={'amp': pi_half_amp, 'dur': pi_half_dur})
        pi_dur = get_calibration_val('pi_pulse_dur')
        pi_segment = Segment(
            name='square_pi_pulse', gen_func=flat_array,
            func_args={'amp': pi_amp, 'dur': pi_dur})

    variable_wait_segment = Segment(
        name='pulse_pulse_delay', gen_func=flat_array,
        func_args={'amp': 0})

    wait_segment = Segment(
        name='wait', gen_func=flat_array,
        func_args={'amp': 0, 'dur': time_after_qubit},
        time_markers=pulse_mod_markers)

    echo_wf = Waveform(
        channel=channels[0],
        segment_list=[compensating_wait_segment, pi_half_segment,
                      variable_wait_segment, pi_segment,
                      variable_wait_segment, pi_half_segment,
                      wait_segment])

    echo_element = Element(sample_rate=get_calibration_val('sample_rate'))
    echo_element.add_waveform(echo_wf)

    if readout_SSBfreqs is not None:
        if len(channels) != 3:
            raise Exception('Not enough channels for SSB readout')
        readout_wf_I = make_readout_ssb_wf_I(readout_SSBfreqs,
                                             channel=channels[-2])
        readout_wf_Q = make_readout_ssb_wf_Q(readout_SSBfreqs,
                                             channel=channels[-1])
        echo_element.add_waveform(readout_wf_I)
        echo_element.add_waveform(readout_wf_Q)
    else:
        readout_wf = make_readout_wf(channel=channels[-1])
        echo_element.add_waveform(readout_wf)

    marker_points = int(get_calibration_val('marker_time') *
                        get_calibration_val('sample_rate'))


    var_name = 'pi_half_pulse_pi_pulse_delay'
    seq_name = 'echo_seq_time_varying_seq'
    echo_sequence = Sequence(
        name=seq_name, variable=var_name, start=start,
        stop=stop, step=step, variable_unit='s')
    for i, val in enumerate(echo_sequence.variable_array):
        elem = echo_element.copy()
        elem[channels[0]].segment_list[2].func_args['dur'] = val
        elem[channels[0]].segment_list[4].func_args['dur'] = val
        compensate_time = get_calibration_val('cycle_time') - elem[channels[0]].duration
        elem[channels[0]].segment_list[0].func_args['dur'] = compensate_time
        echo_sequence.add_element(elem)
        if i == 0:
            elem[channels[-1]].add_marker(2, 0, marker_points)
    echo_sequence.check()
    return echo_sequence


def make_echo_sequence(start, stop, step, SSBfreq=None, pi_half_amp=None,
                         channels=[1, 2, 4], pulse_mod=False,
                         gaussian=True, readout_SSBfreqs=None):
    if SSBfreq is not None:
        raise RuntimeError('ssb echo sequence not implemented')
    else:
        if len(channels) < 2:
            raise Exception('at least 2 channels needed for drive and readout')
        seq = _make_echo_carrier_sequence(
            start, stop, step, channels=[channels[0], channels[-1]],
            pulse_mod=pulse_mod, pi_half_amp=pi_half_amp, gaussian=gaussian)
    seq.labels = {'qubitSSBfreq': SSBfreq, 'seq_type': 'echo',
                  'gaussian': gaussian, 'drag': False,
                  'pulse_mod': pulse_mod,
                  'readoutSSBfreqs': readout_SSBfreqs}
    return seq
