import qcodes as qc
import pickle
from os import listdir
from wrappers.sweep_functions import _do_measurement, \
    _select_plottables
from . import get_calibration_val, get_pulse_location


# TODO: rount -> int/ciel
# TODO: test segments
# TODO: make_save_send_load_awg_file -> not doing same thing twice!
# TODO: docstrings
# TODO: checks
# TODO: floquet

#################################################################
# General AWG and Sequence functions
#################################################################


def get_current_seq(awg):
    seq_num = awg.current_seq()
    path = get_pulse_location()
    seq_file_name = next(f for f in listdir(
        path) if (f[-1] is 'p' and str(seq_num) in f))
    seq = pickle.load(open(path + seq_file_name, "rb"))
    return seq


def get_current_seq_multi_qubit(awg_list):
    seq_nums = [awg.current_seq() for awg in awg_list]
    if len(set(seq_nums)) > 1:
        raise Exception('current_seq values are not the same on all awgs: '
                        '{}'.format(seq_nums))
    path = get_pulse_location()
    seq_file_name = next(f for f in listdir(
        path) if (f[-1] is 'p' and str(seq_nums[0]) in f))
    seq = pickle.load(open(path + seq_file_name, "rb"))
    return seq


def make_save_send_load_awg_file(awg, sequence, file_name):
    """
    WYSIYWYG

    Args:
        awg instrument for upload
        unwrapped_sequence to be uploaded
    """
    unwrapped_seq = sequence.unwrap()[0]
    awg.make_and_save_awg_file(*unwrapped_seq, filename=file_name)
    awg.make_send_and_load_awg_file(*unwrapped_seq)


def check_sample_rate(awg):
    """
    Checks sample rate in pulse dict against that on awg

    Args:
        awg instrument for checking
    """
    sr = get_calibration_val('sample_rate')
    if sr != awg.clock_freq():
        awg.clock_freq(sr)
    print('awg clock freq set to {}'.format(sr))


def check_seq_uploaded(awg, seq_type, dict_to_check,
                       start=None, stop=None, step=None):
    uploaded_seq = get_current_seq(awg)
    if uploaded_seq.labels['seq_type'] is not seq_type:
        return False
    for k in dict_to_check:
        if k not in uploaded_seq.labels:
            return False
        elif uploaded_seq.labels[k] != dict_to_check[k]:
            return False
    try:
        if ([start, stop, step] !=
                [uploaded_seq.start, uploaded_seq.stop, uploaded_seq.step]):
            return False
    except AttributeError:
        return False
    return True


def sweep_awg_chans(meas_param, awg_ch_1, awg_ch_2, start, stop, step,
                    delay=0.01, do_plots=True):
    """
    Sweeps two awg channels at once and is otherwise the same as sweep1d

    Args:
        meas_param: parameter which we want the value of at each point
        awg_ch_1: one of the awg channels to vary
        awg_ch_2: one of the awg channels to vary
        start: starting value for awg channels
        stop: final value for awg channels
        step: value to step awg channels
        delay (default 0.01): mimimum time to spend on each point
        do_plots: Default True: If False no plots are produced.
            Data is still saved and can be displayed with show_num.

    Returns:
        data (qcodes dataset)
        plot: QT plot
    """
    loop = qc.Loop(awg_ch_1.sweep(start, stop, step)).each(
        qc.Task(awg_ch_2.set, awg_ch_1.get),
        meas_param)
    set_params = ((awg_ch_1, start, stop, step),)
    meas_params = _select_plottables(meas_param)

    plot, data = _do_measurement(loop, set_params, meas_params,
                                 do_plots=do_plots)

    return data, plot
