from . import make_readout_wf, get_calibration_val, ramp_array, \
    cos_array, sin_array, flat_array, gaussian_array, \
    make_time_varying_sequence, make_readout_ssb_wf_I, make_readout_ssb_wf_Q, \
    make_time_multi_varying_sequence, get_calibration_array, \
    cos_gaussian_array, sin_gaussian_array, get_qubit_count, make_pulse_dict
from . import Segment, Waveform, Element

import logging
log = logging.getLogger(__name__)


def _get_required_channels(
        qubit_num=1, control_channels_per_qubit=1, readout_SSB=False,
        one_readout_ch_many_qubits=False):
    channels_required = 0
    readout_channels_per_qubit = 0
    if one_readout_ch_many_qubits:
        channels_required += 1
        if readout_SSB:
            channels_required += 1
    else:
        readout_channels_per_qubit += 1
        if readout_SSB:
            readout_channels_per_qubit += 1
            log.warning('why are you using SSB if you have one '
                        'microwave source per readout resonator '
                        'anyway??')
    channels_required += qubit_num * \
        (control_channels_per_qubit + readout_channels_per_qubit)
    return channels_required


def _make_pulse_mod_markers(**kwargs):
    if kwargs['pulse_mod']:
        pmtime = get_calibration_val('pulse_mod_time')
        pulse_mod_markers = {
            1: {'delay_time': [-1 * pmtime],
                'duration_time': [pmtime]}}
    else:
        pulse_mod_markers = None
    return pulse_mod_markers


def make_i_waveform(**kwargs):
    time_after_qubit = (get_calibration_val('cycle_time') -
                        get_calibration_val('pulse_end'))
    compensating_x_wait_segment = Segment(
        name='compensating_x_wait', gen_func=flat_array, func_args={'amp': 0})
    if kwargs['form'] == 'cos':
        floquet_drive = Segment(
            name='floquet_drive', gen_func=cos_array,
            func_args={'amp': kwargs['amp'], 'freq': kwargs['floquet_freq'],
                       'positive': kwargs['positive']})
    elif kwargs['form'] == 'sin':
        floquet_drive = Segment(
            name='floquet_drive', gen_func=sin_array,
            func_args={'amp': kwargs['amp'], 'freq': kwargs['floquet_freq'],
                       'positive': kwargs['positive']})
    else:
        raise Exception('unrecognised form, should be cos or sin')
    end_wait_x_segment = Segment(
        name='wait', gen_func=flat_array,
        func_args={'amp': 0, 'dur': time_after_qubit},
        time_markers=kwargs['pulse_mod_markers'])
    if all([i in kwargs for i in
            ['pi_half_before', 'pi_half_after', 'pi_half_after_neg',
             'z_ramp_dur']]):
        wait_for_z_ramp = Segment(
            name='wait', gen_func=flat_array,
            func_args={'amp': 0, 'dur': kwargs['z_ramp_dur']},
            time_markers=kwargs['pulse_mod_markers'])
        if kwargs['pi_half_before']:
            before_gate = kwargs['q_pulse_dict']['X/2_I']
        else:
            before_gate = kwargs['q_pulse_dict']['identity']
        if kwargs['pi_half_after']:
            after_gate = kwargs['q_pulse_dict']['X/2_I']
        elif kwargs['pi_half_after_neg']:
            after_gate = kwargs['q_pulse_dict']['-X/2_I']
        else:
            after_gate = kwargs['q_pulse_dict']['identity']
        return Waveform(
            channel=kwargs['channel'],
            segment_list=[compensating_x_wait_segment, before_gate,
                          wait_for_z_ramp, floquet_drive, wait_for_z_ramp,
                          after_gate, end_wait_x_segment])
    elif all([i in kwargs for i in
            ['pi_half_before', 'pi_half_after', 'pi_half_after_neg']]):
        if kwargs['pi_half_before']:
            before_gate = kwargs['q_pulse_dict']['X/2_I']
        else:
            before_gate = kwargs['q_pulse_dict']['identity']
        if kwargs['pi_half_after']:
            after_gate = kwargs['q_pulse_dict']['X/2_I']
        elif kwargs['pi_half_after_neg']:
            after_gate = kwargs['q_pulse_dict']['-X/2_I']
        else:
            after_gate = kwargs['q_pulse_dict']['identity']
        return Waveform(
            channel=kwargs['channel'],
            segment_list=[compensating_x_wait_segment, before_gate,
                          floquet_drive,
                          after_gate, end_wait_x_segment])
    elif 'z_ramp_dur' in kwargs:
        wait_for_z_ramp = Segment(
            name='wait', gen_func=flat_array,
            func_args={'amp': 0, 'dur': kwargs['z_ramp_dur']},
            time_markers=kwargs['pulse_mod_markers'])
        return Waveform(
            channel=kwargs['channel'],
            segment_list=[compensating_x_wait_segment,
                          wait_for_z_ramp, floquet_drive, wait_for_z_ramp,
                          end_wait_x_segment])
    else:
        return Waveform(
            channel=kwargs['channel'],
            segment_list=[compensating_x_wait_segment,
                          floquet_drive, end_wait_x_segment])


def make_q_waveform(**kwargs):
    time_after_qubit = (get_calibration_val('cycle_time') -
                        get_calibration_val('pulse_end'))
    compensating_y_wait_segment = Segment(
        name='compensating_y_wait', gen_func=flat_array, func_args={'amp': 0})
    wait_for_z_ramp = Segment(
        name='wait', gen_func=flat_array,
        func_args={'amp': 0, 'dur': kwargs['z_ramp_dur']},
        time_markers=kwargs['pulse_mod_markers'])
    floquet_wait_segment = Segment(
        name='wait_for_floquet', gen_func=flat_array, func_args={'amp': 0})
    end_wait_x_segment = Segment(
        name='wait', gen_func=flat_array,
        func_args={'amp': 0, 'dur': time_after_qubit},
        time_markers=kwargs['pulse_mod_markers'])
    if all([i in kwargs for i in
            ['pi_half_before', 'pi_half_after', 'pi_half_after_neg']]):
        if kwargs['pi_half_before']:
            before_gate = kwargs['q_pulse_dict']['X/2_Q']
        else:
            before_gate = kwargs['q_pulse_dict']['identity']
        if kwargs['pi_half_after']:
            after_gate = kwargs['q_pulse_dict']['X/2_Q']
        elif kwargs['pi_half_after_neg']:
            after_gate = kwargs['q_pulse_dict']['-X/2_Q']
        else:
            after_gate = kwargs['q_pulse_dict']['identity']
        return Waveform(
            channel=kwargs['channel'],
            segment_list=[compensating_y_wait_segment, before_gate,
                          wait_for_z_ramp, floquet_wait_segment,
                          wait_for_z_ramp, after_gate, end_wait_x_segment])
    else:
        raise RuntimeError("['pi_half_before', 'pi_half_after', "
                           "'pi_half_after_neg'] not all in kwargs")


def make_z_waveform(**kwargs):
    time_after_qubit = (get_calibration_val('cycle_time') -
                        get_calibration_val('pulse_end'))
    compensating_z_wait_segment = Segment(
        name='compensating_z_wait', gen_func=flat_array,
        func_args={'amp': 0})
    z_ramp_segment_up = Segment(
        name='z_ramp_up', gen_func=ramp_array,
        func_args={'start': 0, 'stop': kwargs['z_amp'],
                   'dur': kwargs['z_ramp_dur']})
    z_on = Segment(
        name='z_on', gen_func=flat_array,
        func_args={'amp': kwargs['z_amp']})
    z_ramp_segment_down = Segment(
        name='z_ramp_down', gen_func=ramp_array,
        func_args={'start': kwargs['z_amp'], 'stop': 0,
                   'dur': kwargs['z_ramp_dur']})
    wait_z_segment = Segment(
        name='wait', gen_func=flat_array,
        func_args={'amp': 0, 'dur': time_after_qubit},
        time_markers=kwargs['pulse_mod_markers'])
    if 'gate_duration' in kwargs:
        wait_z_segment = Segment(
            name='wait', gen_func=flat_array,
            func_args={
                'amp': 0,
                'dur': time_after_qubit + kwargs['gate_duration']},
            time_markers=kwargs['pulse_mod_markers'])
    else:
        wait_z_segment = Segment(
            name='wait', gen_func=flat_array,
            func_args={'amp': 0, 'dur': time_after_qubit},
            time_markers=kwargs['pulse_mod_markers'])
    return Waveform(
        channel=kwargs['channel'],
        segment_list=[compensating_z_wait_segment, z_ramp_segment_up,
                      z_on, z_ramp_segment_down, wait_z_segment])


def make_floquet_dur_sequence(
        start, stop, step, qubit_indices=None, amp=1, floquet_freq=1e6,
        channels=[1, 4], form='cos', z_amps=None, z_ramp_dur=0,
        readout_SSBfreqs=None, pulse_mod=False):
    """
    Channels go like [x1, z1, x2, z2, ..., readoutI, readoutQ]
    qubit_SSBfreqs goes like [SSB1, SSB2, ...]
    readout_SSBfreqs goes  [SSB1, SSB2, ...]
    """

    # check channels and z_amps match requirements and set up lists
    # for vary_args and vary_settings
    if qubit_indices is None:
        qubit_num = get_qubit_count() or 1
    else:
        qubit_num = len(qubit_indices)

    ch_per_qubit = 1
    if qubit_num > 1:
        ch_per_qubit += 1
        if z_amps is None or len(z_amps) != qubit_num:
            raise Exception('qubit num is {} but z_amps provided:{}'.format(
                qubit_num, z_amps))
        # [(chan1, seg1, func_arg1), ...]
        vary_args_list = [()] * ch_per_qubit * qubit_num
        # [(start1, stop1, step1), ...]
        vary_settings_list = [(start, stop, step)] * ch_per_qubit * qubit_num
    readout_SSB = (False if readout_SSBfreqs is None else True)
    required_channels = _get_required_channels(
        qubit_num=qubit_num, control_channels_per_qubit=ch_per_qubit,
        readout_SSB=readout_SSB, one_readout_ch_many_qubits=True)
    if len(channels) != required_channels:
        raise Exception('require {} channels, got {}'
                        ''.format(required_channels, len(channels)))

    # set up pulse_mod_markers
    pulse_mod_markers = _make_pulse_mod_markers(pulse_mod=pulse_mod)

    # make qubit x channel waveforms
    if qubit_num == 1:
        qubit_wf = make_i_waveform(
            form=form, amp=amp, floquet_freq=floquet_freq,
            positive=True,
            pulse_mod_markers=pulse_mod_markers, channel=channels[0])
    else:
        qubit_wfs = []
        for i in range(qubit_num):
            vary_args_list[i * ch_per_qubit] = (
                channels[i * ch_per_qubit], 2, 'dur', 0)
            vary_settings_list[i * 2] = (start, stop, step)
            if i % 2 == 0:
                qubit_wfs.append(
                    make_i_waveform(
                        form=form, amp=amp, floquet_freq=floquet_freq,
                        positive=True, z_ramp_dur=z_ramp_dur,
                        pulse_mod_markers=pulse_mod_markers,
                        channel=channels[i * 2]))
            else:
                qubit_wfs.append(
                    make_i_waveform(
                        form=form, amp=amp, floquet_freq=floquet_freq,
                        positive=False, z_ramp_dur=z_ramp_dur,
                        pulse_mod_markers=pulse_mod_markers,
                        channel=channels[i * 2]))

    # make qubit z channel wafevorms
    if qubit_num > 1:
        z_wfs = []
        for i in range(qubit_num):
            vary_args_list[(i * ch_per_qubit) +
                           1] = (channels[(i * ch_per_qubit) + 1], 2, 'dur', 0)
            z_wfs.append(
                make_z_waveform(
                    z_amp=z_amps[i], z_ramp_dur=z_ramp_dur,
                    pulse_mod_markers=pulse_mod_markers,
                    channel=channels[(i * ch_per_qubit) + 1]))

    # add waveforms to blueprint element
    floquet_element = Element(sample_rate=get_calibration_val('sample_rate'))
    if qubit_num == 1:
        floquet_element.add_waveform(qubit_wf)
    else:
        for i in range(qubit_num):
            floquet_element.add_waveform(qubit_wfs[i])
            floquet_element.add_waveform(z_wfs[i])

    # add readout waveform(s)
    if readout_SSBfreqs is not None:
        readout_wf_I = make_readout_ssb_wf_I(readout_SSBfreqs,
                                             channel=channels[-2])
        readout_wf_Q = make_readout_ssb_wf_Q(readout_SSBfreqs,
                                             channel=channels[-1])
        floquet_element.add_waveform(readout_wf_I)
        floquet_element.add_waveform(readout_wf_Q)
        r_ch = channels[-2]
    else:
        readout_wf = make_readout_wf(channel=channels[-1])
        floquet_element.add_waveform(readout_wf)
        r_ch = channels[-1]

    floquet_element.print_segment_lists()
    # make sequence
    marker_points = int(get_calibration_val('marker_time') *
                        get_calibration_val('sample_rate'))
    if qubit_num == 1:
        floquet_sequence = make_time_varying_sequence(
            floquet_element, channels[0], 1, 'dur', start, stop, step,
            0, get_calibration_val('cycle_time'),
            name='floquet_seq',
            variable_name='floquet_drive_dur', variable_unit='s',
            readout_ch=r_ch, marker_points=marker_points)
    else:
        floquet_sequence = make_time_multi_varying_sequence(
            floquet_element, vary_args_list, vary_settings_list,
            get_calibration_val('cycle_time'),
            name='floquet_seq',
            variable_name='floquet_drive_dur', variable_unit='s',
            readout_ch=r_ch, marker_points=marker_points)
    floquet_sequence.labels = {
        'seq_type': 'floquet', 'floquet_freq': floquet_freq,
        'pulse_mod': pulse_mod, 'readoutSSBfreqs': readout_SSBfreqs,
        'z_amps': z_amps, 'z_ramp_dur': z_ramp_dur}
    return floquet_sequence


def make_floquet_dur_seq_gated(
        start, stop, step, qubit_indices=None, amp=1, floquet_freq=1e6,
        channels=[1, 4], z_amps=None, z_ramp_dur=0,
        form='cos', pi_half_before=None, pi_half_after=None,
        gaussian=True, pi_half_after_neg=None, qubit_SSBfreqs=None,
        pi_half_amps=None, pulse_mod=False, readout_SSBfreqs=None):
    """
    Channels go like [x1, z1, x2, z2, ..., readoutI, readoutQ]
    pi_half_X goes like [True, False, False, ...]
    qubit_SSBfreqs goes like [SSB1, SSB2, ...]
    readout_SSBfreqs goes  [SSB1, SSB2, ...]
    """
    if qubit_indices is None:
        raise RuntimeError('must specify qubit indices')

    qubit_num = len(qubit_indices)

    # check length of arrays specifying gates
    if pi_half_before is None:
        pi_half_before = [False] * qubit_num
    elif len(pi_half_before) != qubit_num:
        raise Exception(
            'pi_half_before list length {} is not the same '
            'as the qubit_num {}'.format(len(pi_half_before), qubit_num))

    if pi_half_after is None:
        pi_half_after = [False] * qubit_num
    elif len(pi_half_after) != qubit_num:
        raise Exception(
            'pi_half_after list length {} is not the same '
            'as the qubit_num {}'.format(len(pi_half_after), qubit_num))

    if pi_half_after_neg is None:
        pi_half_after_neg = [False] * qubit_num
    elif len(pi_half_after_neg) != qubit_num:
        raise Exception(
            'pi_half_after_neg list length {} is not the same '
            'as the qubit_num {}'.format(len(pi_half_after_neg), qubit_num))

    if qubit_SSBfreqs is None and qubit_num > 1:
        raise RuntimeError('more than one qubit but no SSB freqs given,'
                           ' use make_floquet_seq for ungated')

    # check channels and z_amps match requirements and set up lists
    # for vary_args and vary_settings
    ch_per_qubit = 2 if qubit_SSBfreqs else 1
    if qubit_num > 1:
        ch_per_qubit += 1
        if z_amps is None or len(z_amps) != qubit_num:
            raise Exception('qubit num is {} but z_amps provided:{}'.format(
                qubit_num, z_amps))
        # vary args for each channel to be varied per element:
        # [(chan1, seg1, func_arg1), ...]
        vary_args_list = [()] * ch_per_qubit * qubit_num
        # vary settings for each channel to be vaied per element:
        # [(start1, stop1, step1), ...]
        vary_settings_list = [(start, stop, step)] * ch_per_qubit * \
            qubit_num
    readout_SSB = (False if readout_SSBfreqs is None else True)
    required_channels = _get_required_channels(
        qubit_num=qubit_num, control_channels_per_qubit=ch_per_qubit,
        readout_SSB=readout_SSB, one_readout_ch_many_qubits=True)
    if len(channels) != required_channels:
        raise Exception('require {} channels, got {}'
                        ''.format(required_channels, len(channels)))

    pulse_mod_markers = _make_pulse_mod_markers(pulse_mod=pulse_mod)
    sample_rate = get_calibration_val('sample_rate')
    gate_dict = make_pulse_dict(qubit_indices=qubit_indices,
                                SSBfreqs=qubit_SSBfreqs, gaussian=gaussian,
                                drag=False, z_gates=False, SR=sample_rate)

    gate_duration = gate_dict[next(iter(gate_dict))]['X/2_I'].duration

    # make qubit x, y and z channel waveforms
    if qubit_num == 1:
        qubit_wf = make_i_waveform(
            form=form, amp=amp, floquet_freq=floquet_freq,
            positive=True, pi_half_before=pi_half_before[0],
            pi_half_after=pi_half_after[0], q_pulse_dict=gate_dict[0],
            pi_half_after_neg=pi_half_after_neg[0],
            pulse_mod_markers=pulse_mod_markers, channel=channels[0])
    else:
        qubit_wfs_I = []
        qubit_wfs_Q = []
        qubit_wfs_Z = []
        for i in range(qubit_num):
            vary_args_list[i * ch_per_qubit] = (
                channels[i * ch_per_qubit], 3, 'dur', 0)
            vary_args_list[i * ch_per_qubit +
                           1] = (channels[i * ch_per_qubit + 1], 3, 'dur', 0)
            vary_args_list[i * ch_per_qubit +
                           2] = (channels[i * ch_per_qubit + 2], 2, 'dur', 0)
            if i % 2 == 0:
                qubit_wfs_I.append(
                    make_i_waveform(
                        form=form, amp=amp, floquet_freq=floquet_freq,
                        positive=True, z_ramp_dur=z_ramp_dur,
                        pi_half_before=pi_half_before[i],
                        pi_half_after=pi_half_after[i],
                        q_pulse_dict=gate_dict[i],
                        pi_half_after_neg=pi_half_after_neg[i],
                        pulse_mod_markers=pulse_mod_markers,
                        channel=channels[i * ch_per_qubit]))
            else:
                qubit_wfs_I.append(
                    make_i_waveform(
                        form=form, amp=amp, floquet_freq=floquet_freq,
                        positive=False, z_ramp_dur=z_ramp_dur,
                        pi_half_before=pi_half_before[i],
                        pi_half_after=pi_half_after[i],
                        q_pulse_dict=gate_dict[i],
                        pi_half_after_neg=pi_half_after_neg[i],
                        pulse_mod_markers=pulse_mod_markers,
                        channel=channels[i * ch_per_qubit]))
            qubit_wfs_Q.append(
                make_q_waveform(
                    z_ramp_dur=z_ramp_dur,
                    pi_half_before=pi_half_before[i],
                    pi_half_after=pi_half_after[i],
                    q_pulse_dict=gate_dict[i],
                    pi_half_after_neg=pi_half_after_neg[i],
                    pulse_mod_markers=pulse_mod_markers,
                    channel=channels[i * ch_per_qubit + 1]))
            if qubit_num > 1:
                qubit_wfs_Z.append(
                    make_z_waveform(
                        z_amp=z_amps[i], z_ramp_dur=z_ramp_dur,
                        gate_duration=gate_duration, q_pulse_dict=gate_dict[i],
                        pulse_mod_markers=pulse_mod_markers,
                        channel=channels[i * ch_per_qubit + 2]))

    # add waveforms to blueprint element
    floquet_element = Element(sample_rate=get_calibration_val('sample_rate'))
    if qubit_num == 1:
        floquet_element.add_waveform(qubit_wf)
    else:
        for i in range(qubit_num):
            floquet_element.add_waveform(qubit_wfs_I[i])
            floquet_element.add_waveform(qubit_wfs_Q[i])
            floquet_element.add_waveform(qubit_wfs_Z[i])

    # add readout waveform(s)
    if readout_SSBfreqs is not None:
        readout_wf_I = make_readout_ssb_wf_I(readout_SSBfreqs,
                                             channel=channels[-2])
        readout_wf_Q = make_readout_ssb_wf_Q(readout_SSBfreqs,
                                             channel=channels[-1])
        floquet_element.add_waveform(readout_wf_I)
        floquet_element.add_waveform(readout_wf_Q)
        r_ch = channels[-2]
    else:
        readout_wf = make_readout_wf(channel=channels[-1])
        floquet_element.add_waveform(readout_wf)
        r_ch = channels[-1]

    # make sequence
    marker_points = int(get_calibration_val('marker_time') *
                        get_calibration_val('sample_rate'))

    floquet_element.print_segment_lists()
    if qubit_num == 1:
        floquet_sequence = make_time_varying_sequence(
            floquet_element, channels[0], 2, 'dur',
            start, stop, step,
            0, get_calibration_val('cycle_time'),
            name='floquet_seq',
            variable_name='floquet_drive_dur', variable_unit='s',
            readout_ch=r_ch, marker_points=marker_points)
    else:
        floquet_sequence = make_time_multi_varying_sequence(
            floquet_element, vary_args_list, vary_settings_list,
            get_calibration_val('cycle_time'),
            name='floquet_seq',
            variable_name='floquet_drive_dur', variable_unit='s',
            readout_ch=r_ch, marker_points=marker_points)
    floquet_sequence.labels = {
        'seq_type': 'floquet', 'floquet_freq': floquet_freq,
        'pulse_mod': pulse_mod, 'readoutSSBfreqs': readout_SSBfreqs,
        'z_amps': z_amps, 'z_ramp_dur': z_ramp_dur,
        'pi_half_before': pi_half_before, 'pi_half_after': pi_half_after,
        'pi_half_after_neg': pi_half_after_neg,
        'qubitSSBfreqs': qubit_SSBfreqs}
    return floquet_sequence
