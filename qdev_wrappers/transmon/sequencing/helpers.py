import numpy as np
import pickle
import os
from . import get_calibration_dict, get_allowed_keys, gaussian_array, \
    gaussian_derivative_array, flat_array, cos_gaussian_array, \
    sin_gaussian_array, cos_array, sin_array, get_calibration_val, \
    get_current_qubit

from . import Segment, Waveform, Element, Sequence

# TODO: marker on gate list sequence
# TODO: refactor sequence making functions to have less than a million args
# TODO: square pulses
# TODO: docstrings
# TODO: test make_sequence_from_gate_lists


def save_sequence(sequence, file_name):
    if os.path.exists(file_name):
        raise Exception('File already exists at this location with this '
                        'name: {}'.format(file_name))
    else:
        pickle.dump(sequence, open(file_name, 'wb'))


####################################################################
# Sequence building functions (vary param over sequence)
####################################################################

def make_varying_sequence(element_template, vary_args_list,
                          vary_settings_list,
                          name=None, variable_name=None,
                          variable_label=None,
                          variable_unit=None,
                          readout_ch=4, marker_points=100):
    """
    vary_args list goes like
        [(vary_ch_1, vary_seg_1, vary_arg_1), (vary_ch_2...)...]
    vary_settings list goes like
        [(start1, stop1, step1), (start2, stop2, ...)...]
    """
    var_name = variable_name or ''.join([d[3] for d in vary_args_list])
    seq_name = name or variable_name + '_varying_seq'
    sequence = Sequence(
        name=seq_name, variable=var_name, start=vary_settings_list[0][0],
        stop=vary_settings_list[0][1], step=vary_settings_list[0][2],
        variable_label=variable_label, variable_unit=variable_unit)
    variable_arrays = []
    elemnums = []
    for ch_i, v in enumerate(vary_args_list):
        elemnum = int(round(
            abs(vary_settings_list[ch_i][1] - vary_settings_list[ch_i][0]) /
            vary_settings_list[ch_i][2] + 1))
        elemnums.append(elemnum)
        variable_arrays.append(np.linspace(
            vary_settings_list[ch_i][0], vary_settings_list[ch_i][1],
            num=elemnum))
    if len(set(elemnums)) != 1:
        raise Exception('variable arrays do not all have same length: {}'
                        ''.format(elemnums))
    for j in range(elemnum):
        elem = element_template.copy()
        for ch_i, vary_args in enumerate(vary_args_list):
            elem[vary_args[0]].segment_list[vary_args[1]].func_args[
                vary_args[2]] = variable_arrays[ch_i][j]
        if j == 0:
            elem[readout_ch].add_marker(2, 0, marker_points)
        sequence.add_element(elem)
    sequence.check()
    return sequence


def make_time_varying_sequence(element_template, vary_args_list,
                               vary_settings_list,
                               total_time, name=None,
                               variable_name=None,
                               variable_label=None, variable_unit=None,
                               readout_ch=4, marker_points=100):
    """
    vary_args list goes like
        [(vary_ch_1, vary_seg_1, vary_arg_1, compensate_seg_1), ...]
    vary_settings list goes like
        [(start1, stop1, step1), (start2, stop2, ...)...]
    """
    var_name = variable_name or ''.join([d[2] for d in vary_args_list])
    seq_name = (name or variable_name or 'general') + '_time_varying_seq'
    sequence = Sequence(
        name=seq_name, variable=var_name, start=vary_settings_list[0][0],
        stop=vary_settings_list[0][1], step=vary_settings_list[0][2],
        variable_label=variable_label, variable_unit=variable_unit)
    variable_arrays = [[]] * len(vary_args_list)
    elemnums = [[]] * len(vary_args_list)
    for ch_i, v in enumerate(vary_args_list):
        elemnum = int(round(
            abs(vary_settings_list[ch_i][1] - vary_settings_list[ch_i][0]) /
            vary_settings_list[ch_i][2] + 1))
        elemnums[ch_i] = elemnum
        variable_arrays[ch_i] = np.linspace(
            vary_settings_list[ch_i][0], vary_settings_list[ch_i][1],
            num=elemnum)
    if len(set(elemnums)) != 1:
        raise Exception('variable arrays do not all have same length: {}'
                        ''.format(elemnums))
    for j in range(elemnum):
        elem = element_template.copy()
        for ch_i, vary_args in enumerate(vary_args_list):
            elem[vary_args[0]].segment_list[vary_args[1]].func_args[
                vary_args[2]] = variable_arrays[ch_i][j]
            c_dur = total_time - elem[vary_args[0]].duration
            elem[vary_args[0]].segment_list[vary_args[3]].func_args[
                "dur"] = c_dur
        if j == 0:
            elem[readout_ch].add_marker(2, 0, marker_points)
        sequence.add_element(elem)
    sequence.check()
    return sequence


#################################################################
# Element building functions (for use executing gates)
#################################################################

def make_x_y_carrier_gaussian_pulses(params, drag=False, SR=None):
    q_pulse_dict = {}
    x_y_wait = Segment(
        name='XY_wait', gen_func=flat_array,
        func_args={
            'amp': 0,
            'dur': 2 * params['pi_pulse_sigma'] * params['sigma_cutoff']})

    x_y_pi = Segment(
        name='pi', gen_func=gaussian_array,
        func_args={'sigma': params['pi_pulse_sigma'],
                   'sigma_cutoff': params['sigma_cutoff'],
                   'amp': params['pi_pulse_amp']})

    x_y_pi_half = Segment(
        name='pi/2', gen_func=gaussian_array,
        func_args={'sigma': params['pi_pulse_sigma'],
                   'sigma_cutoff': params['sigma_cutoff'],
                   'amp': params['pi_half_pulse_amp']})

    x_y_pi_half_neg = Segment(
        name='-pi/2', gen_func=gaussian_array,
        func_args={'sigma': params['pi_pulse_sigma'],
                   'sigma_cutoff': params['sigma_cutoff'],
                   'amp': params['pi_half_pulse_amp'],
                   'positive': False})

    if SR is not None:
        for s in [x_y_wait, x_y_pi, x_y_pi_half, x_y_pi_half_neg]:
            s.func_args['SR'] = SR

    q_pulse_dict['XY_wait'] = x_y_wait
    q_pulse_dict['X_I'] = x_y_pi
    q_pulse_dict['X/2_I'] = x_y_pi_half
    q_pulse_dict['-X/2_I'] = x_y_pi_half_neg
    q_pulse_dict['Y_Q'] = x_y_pi
    q_pulse_dict['Y/2_Q'] = x_y_pi_half
    q_pulse_dict['-Y/2_Q'] = x_y_pi_half_neg
    if drag:
        x_y_pi_drag = Segment(
            name='pi_drag',
            gen_func=gaussian_derivative_array,
            func_args={'sigma': params['pi_pulse_sigma'],
                       'sigma_cutoff': params['sigma_cutoff'],
                       'amp': (params['pi_pulse_amp'] *
                               params['drag_coef'])})

        x_y_pi_half_drag = Segment(
            name='pi/2_drag',
            gen_func=gaussian_derivative_array,
            func_args={'sigma': params['pi_pulse_sigma'],
                       'sigma_cutoff': params['sigma_cutoff'],
                       'amp': (params['pi_half_pulse_amp'] *
                               params['drag_coef'])})

        x_y_pi_half_neg_drag = Segment(
            name='-pi/2_drag',
            gen_func=gaussian_derivative_array,
            func_args={'sigma': params['pi_pulse_sigma'],
                       'sigma_cutoff': params['sigma_cutoff'],
                       'amp': (params['pi_half_pulse_amp'] *
                               params['drag_coef']),
                       'positive': False})
        if SR is not None:
            for s in [x_y_pi_drag, x_y_pi_half_drag, x_y_pi_half_neg_drag]:
                s.func_args['SR'] = SR

        q_pulse_dict['X_Q'] = x_y_pi_drag
        q_pulse_dict['X/2_Q'] = x_y_pi_half_drag
        q_pulse_dict['-X/2_Q'] = x_y_pi_half_neg_drag
        q_pulse_dict['Y_I'] = x_y_pi_drag
        q_pulse_dict['Y/2_I'] = x_y_pi_half_drag
        q_pulse_dict['-Y/2_I'] = x_y_pi_half_neg_drag
    else:
        q_pulse_dict['X_Q'] = x_y_wait
        q_pulse_dict['X/2_Q'] = x_y_wait
        q_pulse_dict['-X/2_Q'] = x_y_wait
        q_pulse_dict['Y_I'] = x_y_wait
        q_pulse_dict['Y/2_I'] = x_y_wait
        q_pulse_dict['-Y/2_I'] = x_y_wait
    return q_pulse_dict


def make_x_y_carrier_flat_pulses(params, SR=None):
    q_pulse_dict = {}
    x_y_wait = Segment(
        name='XY_wait', gen_func=flat_array,
        func_args={
            'amp': 0,
            'dur': params['pi_pulse_dur']})

    x_y_pi = Segment(
        name='pi', gen_func=flat_array,
        func_args={'dur': params['pi_pulse_dur'],
                   'amp': params['pi_pulse_amp']})

    x_y_pi_half = Segment(
        name='pi/2', gen_func=flat_array,
        func_args={'dur': params['pi_pulse_dur'],
                   'amp': params['pi_half_pulse_amp']})

    x_y_pi_half_neg = Segment(
        name='-pi/2', gen_func=flat_array,
        func_args={'dur': params['pi_pulse_dur'],
                   'amp': -1 * params['pi_half_pulse_amp']})

    if SR is not None:
        for s in [x_y_wait, x_y_pi, x_y_pi_half, x_y_pi_half_neg]:
            s.func_args['SR'] = SR

    q_pulse_dict['XY_wait'] = x_y_wait
    q_pulse_dict['X_I'] = x_y_pi
    q_pulse_dict['X_Q'] = x_y_wait
    q_pulse_dict['X/2_I'] = x_y_pi_half
    q_pulse_dict['X/2_Q'] = x_y_wait
    q_pulse_dict['-X/2_I'] = x_y_pi_half_neg
    q_pulse_dict['-X/2_Q'] = x_y_wait
    q_pulse_dict['Y_I'] = x_y_wait
    q_pulse_dict['Y_Q'] = x_y_pi
    q_pulse_dict['Y/2_I'] = x_y_wait
    q_pulse_dict['Y/2_Q'] = x_y_pi_half
    q_pulse_dict['-Y/2_I'] = x_y_wait
    q_pulse_dict['-Y/2_Q'] = x_y_pi_half_neg
    return q_pulse_dict


def make_x_y_ssb_gaussian_pulses(params, SSBfreq, SR=None):
    q_pulse_dict = {}
    x_y_wait = Segment(
        name='XY_wait', gen_func=flat_array,
        func_args={
            'amp': 0,
            'dur': 2 * params['pi_pulse_sigma'] * params['sigma_cutoff']})
    ssb_pi_x_I = Segment(
        name='X_I', gen_func=cos_gaussian_array,
        func_args={'sigma': params['pi_pulse_sigma'],
                   'sigma_cutoff': params['sigma_cutoff'],
                   'SSBfreq': SSBfreq,
                   'amp': params['pi_pulse_amp']})
    ssb_pi_x_Q = Segment(
        name='X_Q', gen_func=sin_gaussian_array,
        func_args={'sigma': params['pi_pulse_sigma'],
                   'sigma_cutoff': params['sigma_cutoff'],
                   'SSBfreq': SSBfreq,
                   'amp': params['pi_pulse_amp'],
                   'positive': False})
    ssb_pi_half_x_I = Segment(
        name='X/2_I', gen_func=cos_gaussian_array,
        func_args={'sigma': params['pi_pulse_sigma'],
                   'sigma_cutoff': params['sigma_cutoff'],
                   'SSBfreq': SSBfreq,
                   'amp': params['pi_half_pulse_amp']})
    ssb_pi_half_x_Q = Segment(
        name='X/2_Q', gen_func=sin_gaussian_array,
        func_args={'sigma': params['pi_pulse_sigma'],
                   'sigma_cutoff': params['sigma_cutoff'],
                   'SSBfreq': SSBfreq,
                   'amp': params['pi_half_pulse_amp'],
                   'positive': False})
    ssb_pi_half_neg_x_I = Segment(
        name='-X/2_I', gen_func=cos_gaussian_array,
        func_args={'sigma': params['pi_pulse_sigma'],
                   'sigma_cutoff': params['sigma_cutoff'],
                   'SSBfreq': SSBfreq,
                   'amp': params['pi_half_pulse_amp'],
                   'positive': False})
    ssb_pi_half_neg_x_Q = Segment(
        name='-X/2_Q', gen_func=sin_gaussian_array,
        func_args={'sigma': params['pi_pulse_sigma'],
                   'sigma_cutoff': params['sigma_cutoff'],
                   'SSBfreq': SSBfreq,
                   'amp': params['pi_half_pulse_amp']})
    ssb_pi_y_I = Segment(
        name='Y_I', gen_func=sin_gaussian_array,
        func_args={'sigma': params['pi_pulse_sigma'],
                   'sigma_cutoff': params['sigma_cutoff'],
                   'SSBfreq': SSBfreq,
                   'amp': params['pi_pulse_amp']})
    ssb_pi_y_Q = Segment(
        name='Y_Q', gen_func=cos_gaussian_array,
        func_args={'sigma': params['pi_pulse_sigma'],
                   'sigma_cutoff': params['sigma_cutoff'],
                   'SSBfreq': SSBfreq,
                   'amp': params['pi_pulse_amp']})
    ssb_pi_half_y_I = Segment(
        name='Y/2_I', gen_func=sin_gaussian_array,
        func_args={'sigma': params['pi_pulse_sigma'],
                   'sigma_cutoff': params['sigma_cutoff'],
                   'SSBfreq': SSBfreq,
                   'amp': params['pi_half_pulse_amp']})
    ssb_pi_half_y_Q = Segment(
        name='Y/2_Q', gen_func=cos_gaussian_array,
        func_args={'sigma': params['pi_pulse_sigma'],
                   'sigma_cutoff': params['sigma_cutoff'],
                   'SSBfreq': SSBfreq,
                   'amp': params['pi_half_pulse_amp']})
    ssb_pi_half_neg_y_I = Segment(
        name='-Y/2_I', gen_func=sin_gaussian_array,
        func_args={'sigma': params['pi_pulse_sigma'],
                   'sigma_cutoff': params['sigma_cutoff'],
                   'SSBfreq': SSBfreq,
                   'amp': params['pi_half_pulse_amp'],
                   'positive': False})
    ssb_pi_half_neg_y_Q = Segment(
        name='-Y/2_Q', gen_func=cos_gaussian_array,
        func_args={'sigma': params['pi_pulse_sigma'],
                   'sigma_cutoff': params['sigma_cutoff'],
                   'SSBfreq': SSBfreq,
                   'amp': params['pi_half_pulse_amp'],
                   'positive': False})

    if SR is not None:
        for s in [x_y_wait, ssb_pi_x_I, ssb_pi_x_Q, ssb_pi_half_x_I,
                  ssb_pi_half_x_Q, ssb_pi_half_neg_x_I, ssb_pi_half_neg_x_Q,
                  ssb_pi_y_I, ssb_pi_y_Q, ssb_pi_half_y_I, ssb_pi_half_y_Q,
                  ssb_pi_half_neg_y_I, ssb_pi_half_neg_y_Q]:
            s.func_args['SR'] = SR

    q_pulse_dict['XY_wait'] = x_y_wait
    q_pulse_dict['X_I'] = ssb_pi_x_I
    q_pulse_dict['X_Q'] = ssb_pi_x_Q
    q_pulse_dict['X/2_I'] = ssb_pi_half_x_I
    q_pulse_dict['X/2_Q'] = ssb_pi_half_x_Q
    q_pulse_dict['-X/2_I'] = ssb_pi_half_neg_x_I
    q_pulse_dict['-X/2_Q'] = ssb_pi_half_neg_x_Q
    q_pulse_dict['Y_I'] = ssb_pi_y_I
    q_pulse_dict['Y_Q'] = ssb_pi_y_Q
    q_pulse_dict['Y/2_I'] = ssb_pi_half_y_I
    q_pulse_dict['Y/2_Q'] = ssb_pi_half_y_Q
    q_pulse_dict['-Y/2_I'] = ssb_pi_half_neg_y_I
    q_pulse_dict['-Y/2_Q'] = ssb_pi_half_neg_y_Q

    return q_pulse_dict


def make_x_y_ssb_flat_pulses(params, SSBfreq, SR=None):
    q_pulse_dict = {}
    x_y_wait = Segment(
        name='XY_wait', gen_func=flat_array,
        func_args={
            'amp': 0,
            'dur': 2 * params['pi_pulse_sigma'] * params['sigma_cutoff']})
    ssb_pi_x_I = Segment(
        name='X_I', gen_func=cos_array,
        func_args={'freq': SSBfreq,
                   'dur': params['pi_pulse_dur'],
                   'amp': params['pi_pulse_amp']})
    ssb_pi_x_Q = Segment(
        name='X_Q', gen_func=sin_array,
        func_args={'freq': SSBfreq,
                   'dur': params['pi_pulse_dur'],
                   'amp': params['pi_pulse_amp'],
                   'positive': False})
    ssb_pi_half_x_I = Segment(
        name='X/2_I', gen_func=cos_array,
        func_args={'freq': SSBfreq,
                   'dur': params['pi_pulse_dur'],
                   'amp': params['pi_half_pulse_amp']})
    ssb_pi_half_x_Q = Segment(
        name='X/2_Q', gen_func=sin_array,
        func_args={'freq': SSBfreq,
                   'dur': params['pi_pulse_dur'],
                   'amp': params['pi_half_pulse_amp'],
                   'positive': False})
    ssb_pi_half_neg_x_I = Segment(
        name='-X/2_I', gen_func=cos_array,
        func_args={'freq': SSBfreq,
                   'dur': params['pi_pulse_dur'],
                   'amp': params['pi_half_pulse_amp'],
                   'positive': False})
    ssb_pi_half_neg_x_Q = Segment(
        name='-X/2_Q', gen_func=sin_array,
        func_args={'freq': SSBfreq,
                   'dur': params['pi_pulse_dur'],
                   'amp': params['pi_half_pulse_amp']})
    ssb_pi_y_I = Segment(
        name='Y_I', gen_func=sin_array,
        func_args={'freq': SSBfreq,
                   'dur': params['pi_pulse_dur'],
                   'amp': params['pi_pulse_amp']})
    ssb_pi_y_Q = Segment(
        name='Y_Q', gen_func=cos_array,
        func_args={'freq': SSBfreq,
                   'dur': params['pi_pulse_dur'],
                   'amp': params['pi_pulse_amp']})
    ssb_pi_half_y_I = Segment(
        name='Y/2_I', gen_func=sin_array,
        func_args={'freq': SSBfreq,
                   'dur': params['pi_pulse_dur'],
                   'amp': params['pi_pulse_amp']})
    ssb_pi_half_y_Q = Segment(
        name='Y/2_Q', gen_func=cos_array,
        func_args={'freq': SSBfreq,
                   'dur': params['pi_pulse_dur'],
                   'amp': params['pi_half_pulse_amp']})
    ssb_pi_half_neg_y_I = Segment(
        name='-Y/2_I', gen_func=sin_array,
        func_args={'freq': SSBfreq,
                   'dur': params['pi_pulse_dur'],
                   'amp': params['pi_pulse_amp'],
                   'positive': False})
    ssb_pi_half_neg_y_Q = Segment(
        name='-Y/2_Q', gen_func=cos_array,
        func_args={'freq': SSBfreq,
                   'dur': params['pi_pulse_dur'],
                   'amp': params['pi_half_pulse_amp'],
                   'positive': False})
    if SR is not None:
        for s in [x_y_wait, ssb_pi_x_I, ssb_pi_x_Q, ssb_pi_half_x_I,
                  ssb_pi_half_x_Q, ssb_pi_half_neg_x_I, ssb_pi_half_neg_x_Q,
                  ssb_pi_y_I, ssb_pi_y_Q, ssb_pi_half_y_I, ssb_pi_half_y_Q,
                  ssb_pi_half_neg_y_I, ssb_pi_half_neg_y_Q]:
            s.func_args['SR'] = SR

    q_pulse_dict['XY_wait'] = x_y_wait
    q_pulse_dict['X_I'] = ssb_pi_x_I
    q_pulse_dict['X_Q'] = ssb_pi_x_Q
    q_pulse_dict['X/2_I'] = ssb_pi_half_x_I
    q_pulse_dict['X/2_Q'] = ssb_pi_half_x_Q
    q_pulse_dict['-X/2_I'] = ssb_pi_half_neg_x_I
    q_pulse_dict['-X/2_Q'] = ssb_pi_half_neg_x_Q
    q_pulse_dict['Y_I'] = ssb_pi_y_I
    q_pulse_dict['Y_Q'] = ssb_pi_y_Q
    q_pulse_dict['Y/2_I'] = ssb_pi_half_y_I
    q_pulse_dict['Y/2_Q'] = ssb_pi_half_y_Q
    q_pulse_dict['-Y/2_I'] = ssb_pi_half_neg_y_I
    q_pulse_dict['-Y/2_Q'] = ssb_pi_half_neg_y_Q

    return q_pulse_dict


def make_z_pulses(params, SR=None):
    q_pulse_dict = {}
    z_pi = Segment(
        name='Z', gen_func=flat_array,
        func_args={'dur': params['z_pulse_dur'],
                   'amp': params['z_pulse_amp']})

    z_pi_half = Segment(
        name='Z/2', gen_func=flat_array,
        func_args={'dur': params['z_pulse_dur'],
                   'amp': params['z_half_pulse_amp']})
    z_pi_half_neg = Segment(
        name='-Z/2', gen_func=flat_array,
        func_args={'dur': params['z_pulse_dur'],
                   'amp': -1 * params['z_half_pulse_amp']})
    z_wait = Segment(
        name='Z_wait', gen_func=flat_array,
        func_args={'amp': 0, 'dur': params['z_pulse_dur']})

    if SR is not None:
        for s in [z_pi, z_pi_half, z_pi_half_neg, z_wait]:
            s.func_args['SR'] = SR

    q_pulse_dict['Z'] = z_pi
    q_pulse_dict['Z/2'] = z_pi_half
    q_pulse_dict['-Z/2'] = z_pi_half_neg
    q_pulse_dict['Z_wait'] = z_wait

    return q_pulse_dict


def make_pulse_dict(pulse_params=None, qubit_indices=None,
                    SSBfreqs=None, gaussian=True,
                    drag=False, z_gates=False, SR=None):
    """
    Function which returns a dictionary of pulses for gates based on the
    current calibration dictionary values (or optionally those specified in a
    dictionary given).

    Args:
        pulse_params (dict) (default {}): values for the pulse params to
            override those in the calibration dictionary
        qubit_indices (list of ints) (default None): the indicates the qubits
            for which to make pulses, if None then current_qubit is used
        SSBfreqs (list of floats) (default None): sideband frequencies of the
            qubit drive pulses. Lower sideband by default
        gaussian (bool) (default True): whether pulses should be gaussian shape
        drag (bool) (default False): whether drag pulses should be applied to
            other qubit control channel during pulse
        z_gates (bool) (default False): whether z gates should be generated
        SR (float) (default None): optional sample rate to be provided to
            segments so they will have duration as standalone objects

    Returns:
        pulse_dict (dict): dictionary containing segments of pulses
            {qubit_index:
                {gate1: segment1}}
            for gates of form 'X_I', 'Y/2_I', 'Z_wait' etc
    """
    # TODO: allow for SSB measurement
    if drag and SSBfreqs is not None:
        raise Exception('Cannot use drag pulse and ssb pulses.')
    if drag and not gaussian:
        raise Exception('Cannot use drag and square pulses.')

    qubit_indices = qubit_indices or [get_current_qubit()]
    pulse_params = pulse_params or {}
    SSBfreqs = SSBfreqs or [None] * len(qubit_indices)

    if len(SSBfreqs) != len(qubit_indices):
        raise RuntimeError('{} qubit indeices provided but {} SSB freqs'
                           ''.format(len(qubit_indices), len(SSBfreqs)))
    pulse_dict = {}
    for i, qubit_index in enumerate(qubit_indices):
        params = {}
        SSBfreq = SSBfreqs[i]
        pulse_keys = get_allowed_keys('calib', section='Pulse')
        for k in pulse_keys:
            if k in pulse_params:
                params[k] = pulse_params[k]
            else:
                params[k] = get_calibration_val(k, qubit_index=qubit_index)

        q_pulse_dict = {}

        measurement = Segment(
            name='cavity_measurement', gen_func=flat_array,
            func_args={'amp': params['readout_amp'],
                       'dur': params['readout_time']},
            time_markers={
                1: {'delay_time': [-1 * params['marker_readout_delay']],
                    'duration_time': [params['marker_time']]}})

        measurement_wait = Segment(
            name='wait_measurement', gen_func=flat_array,
            func_args={'amp': 0, 'dur': params['readout_time']})

        if gaussian:
            id_dur = 2 * params['pi_pulse_sigma'] * params['sigma_cutoff']
        else:
            id_dur = params['pi_pulse_dur']

        identity = Segment(
            name='identity', gen_func=flat_array,
            func_args={'amp': 0, 'dur': id_dur})

        wait = Segment(name='wait', gen_func=flat_array, func_args={'amp': 0})

        if SR is not None:
            measurement.func_args['SR'] = SR
            measurement_wait.func_args['SR'] = SR
            identity.func_args['SR'] = SR
            wait.func_args['SR'] = SR

        q_pulse_dict['measurement'] = measurement
        q_pulse_dict['measurement_wait'] = measurement_wait
        q_pulse_dict['wait_template'] = wait
        q_pulse_dict['identity'] = identity

        if SSBfreq is not None and gaussian:
            pulses = make_x_y_ssb_gaussian_pulses(
                params, SSBfreq, SR=SR)
        elif SSBfreq is not None:
            pulses = make_x_y_ssb_flat_pulses(
                params, SSBfreq, SR=SR)
        elif gaussian:
            pulses = make_x_y_carrier_gaussian_pulses(
                params, drag=drag, SR=SR)
        else:
            pulses = make_x_y_carrier_flat_pulses(
                params, SR=SR)
        q_pulse_dict.update(pulses)

        if z_gates:
            z_pulses = make_z_pulses(params, SR=SR)
            q_pulse_dict.update(z_pulses)

        pulse_dict[qubit_index] = q_pulse_dict

    return pulse_dict


def do_x_pi(element, q_pulse_dict, channels=[1, 2, 3, 4]):
    i_pulse = q_pulse_dict['X_I']
    q_pulse = q_pulse_dict['X_Q']
    identity = q_pulse_dict['XY_wait']
    element[channels[0]].add_segment(i_pulse)
    element[channels[1]].add_segment(q_pulse)
    element[channels[2]].add_segment(identity)
    element[channels[3]].add_segment(identity)


def do_x_pi_half(element, q_pulse_dict, channels=[1, 2, 3, 4], positive=True):
    identity = q_pulse_dict['XY_wait']
    if positive:
        i_pulse = q_pulse_dict['X/2_I']
        q_pulse = q_pulse_dict['X/2_Q']
    else:
        i_pulse = q_pulse_dict['-X/2_I']
        q_pulse = q_pulse_dict['-X/2_Q']
    element[channels[0]].add_segment(i_pulse)
    element[channels[1]].add_segment(q_pulse)
    element[channels[2]].add_segment(identity)
    element[channels[3]].add_segment(identity)


def do_y_pi(element, q_pulse_dict, channels=[1, 2, 3, 4]):
    i_pulse = q_pulse_dict['Y_I']
    q_pulse = q_pulse_dict['Y_Q']
    identity = q_pulse_dict['XY_wait']
    element[channels[0]].add_segment(i_pulse)
    element[channels[1]].add_segment(q_pulse)
    element[channels[2]].add_segment(identity)
    element[channels[3]].add_segment(identity)


def do_y_pi_half(element, q_pulse_dict, channels=[1, 2, 3, 4], positive=True):
    identity = q_pulse_dict['XY_wait']
    if positive:
        i_pulse = q_pulse_dict['Y/2_I']
        q_pulse = q_pulse_dict['Y/2_Q']
    else:
        i_pulse = q_pulse_dict['-Y/2_I']
        q_pulse = q_pulse_dict['-Y/2_Q']
    element[channels[0]].add_segment(i_pulse)
    element[channels[1]].add_segment(q_pulse)
    element[channels[2]].add_segment(identity)
    element[channels[3]].add_segment(identity)


def do_z_pi(element, q_pulse_dict, channels=[1, 2, 3, 4]):
    identity = q_pulse_dict['Z_wait']
    z_pulse = q_pulse_dict['Z']
    element[channels[0]].add_segment(identity)
    element[channels[1]].add_segment(identity)
    element[channels[2]].add_segment(z_pulse)
    element[channels[3]].add_segment(identity)


def do_z_pi_half(element, q_pulse_dict, channels=[1, 2, 3, 4], positive=True):
    identity = q_pulse_dict['Z_wait']
    if positive:
        z_pulse = q_pulse_dict['Z/2']
    else:
        z_pulse = q_pulse_dict['-Z/2']
    element[channels[0]].add_segment(identity)
    element[channels[1]].add_segment(identity)
    element[channels[2]].add_segment(z_pulse)
    element[channels[3]].add_segment(identity)


def do_identity(element, q_pulse_dict, channels=[1, 2, 3, 4]):
    identity = q_pulse_dict['XY_wait']
    element[channels[0]].add_segment(identity)
    element[channels[1]].add_segment(identity)
    element[channels[2]].add_segment(identity)
    element[channels[3]].add_segment(identity)


def measure(element, q_pulse_dict, channels=[1, 2, 3, 4]):
    identity = q_pulse_dict['measurement_wait']
    measurement = q_pulse_dict['measurement']
    element[channels[0]].add_segment(identity)
    element[channels[1]].add_segment(identity)
    element[channels[2]].add_segment(identity)
    element[channels[3]].add_segment(measurement)


def wait(element, q_pulse_dict, dur, channels=[1, 2, 3, 4]):
    identity = q_pulse_dict['wait_template'].copy()
    identity.func_args['dur'] = dur
    element[channels[0]].add_segment(identity)
    element[channels[1]].add_segment(identity)
    element[channels[2]].add_segment(identity)
    element[channels[3]].add_segment(identity)


def prepend_compensating_wait_to_element(element, q_pulse_dict, total_time):
    identity = q_pulse_dict['wait_template'].copy()
    identity.func_args['dur'] = total_time - element.duration
    for w in element.keys():
        element[w].add_segment(identity, position=0)


def execute_gates(element, q_pulse_dict, gate_list,
                  channels=[1, 2, 3, 4], spacing=None):
    for i in gate_list:
        if i == 'I':
            do_identity(element, q_pulse_dict, channels=channels)
        if i == 'X':
            do_x_pi(element, q_pulse_dict, channels=channels)
        elif i == 'X/2':
            do_x_pi_half(element, q_pulse_dict, channels=channels)
        elif i == '-X/2':
            do_x_pi_half(element, q_pulse_dict, channels=channels,
                         positive=False)
        elif i == 'Y':
            do_y_pi(element, q_pulse_dict, channels=channels)
        elif i == 'Y/2':
            do_y_pi_half(element, q_pulse_dict, channels=channels)
        elif i == '-Y/2':
            do_y_pi_half(element, q_pulse_dict, channels=channels,
                         positive=False)
        elif i == 'Z':
            do_z_pi(element, q_pulse_dict, channels=channels)
        elif i == 'Z/2':
            do_z_pi_half(element, q_pulse_dict, channels=channels)
        if spacing is not None:
            wait(element, q_pulse_dict, spacing, channels=channels)
        elif i == '-Z/2':
            do_z_pi_half(element, q_pulse_dict, channels=channels,
                         positive=False)


###########################################################
# Sequence building function (with gates)
###########################################################

def make_element_from_gate_list(
        gate_list, SSBfreq=None, drag=False, gaussian=True,
        channels=[1, 2, 3, 4], spacing=None, calib_dict=None,
        qubit_index=None, q_pulse_dict=None):
    # TODO: extend this to multiqubit
    qubit_index = qubit_index or get_current_qubit()
    q_pulse_dict = q_pulse_dict or make_pulse_dict(
        qubit_indices=[qubit_index], SSBfreq=SSBfreq, drag=drag,
        gaussian=gaussian)[qubit_index]
    element = Element(sample_rate=get_calibration_val('sample_rate'))
    i_wf = Waveform(channel=channels[0])
    q_wf = Waveform(channel=channels[1])
    z_wf = Waveform(channel=channels[2])
    measure_wf = Waveform(channel=channels[3])
    element.add_waveform(i_wf)
    element.add_waveform(q_wf)
    element.add_waveform(z_wf)
    element.add_waveform(measure_wf)
    execute_gates(element, q_pulse_dict, gate_list,
                  spacing=spacing)
    wait(element, q_pulse_dict, get_calibration_val('pulse_readout_delay'),
         channels=channels)
    measure(element, q_pulse_dict, channels=channels)
    time_after_readout = (get_calibration_val('cycle_time') -
                          get_calibration_val('pulse_end') -
                          get_calibration_val('pulse_readout_delay') -
                          get_calibration_val('readout_time'))
    wait(element, q_pulse_dict, time_after_readout, channels=channels)
    prepend_compensating_wait_to_element(element, q_pulse_dict,
                                         get_calibration_val('cycle_time'))
    return element


def make_sequence_from_gate_lists(
        gate_lists, SSBfreq=None, drag=False, gaussian=True,
        channels=[1, 2, 3, 4], name=None, variable_label=None, spacing=None,
        qubit_index=None):
    qubit_index = qubit_index or get_current_qubit()
    calib_dict = get_calibration_dict()
    SSBfreqs = None if SSBfreq is None else [SSBfreq]
    q_pulse_dict = make_pulse_dict(
        SSBfreqs=SSBfreqs, drag=drag, gaussian=gaussian)[qubit_index]
    seq = Sequence(name=name or 'seq_from_gates',
                   variable_label=variable_label)

    for i, gate_list in enumerate(gate_lists):
        element = make_element_from_gate_list(
            gate_list, SSBfreq=SSBfreq, drag=drag, gaussian=gaussian,
            channels=channels, spacing=spacing, q_pulse_dict=q_pulse_dict,
            calib_dict=calib_dict, qubit_index=qubit_index)
        if i == 0:
            marker_points = int(get_calibration_val('marker_time') *
                                get_calibration_val('sample_rate'))
            element[channels[3]].add_marker(2, 0, marker_points)
        seq.add_element(element)
    seq.check()
    return seq
