from . import check_sample_rate, make_save_send_load_awg_file, \
    get_pulse_location, get_latest_counter
from .sequencing import save_sequence


def set_up_sequence(awg, alazar, acq_controllers, sequence, seq_mode='on'):
    """
    Function which checks sample rate compatability between sequence and awg
    setting, uploads sequence to awg, sets the alazar instrument to the
    relevant sequence mode and sets the acquisition controller aquisiion
    parameter to have setpoints based on the sequence variable.

    Args:
        awg instrument (AWG5014)
        alazar instrument
        acq_controllers list
        sequence for upload
        seq_mode (default 'on')
    """
    check_sample_rate(awg)
    pulse_location = get_pulse_location()
    try:
        num = get_latest_counter(pulse_location) + 1
    except (FileNotFoundError, OSError):
        num = 0
    if awg.current_seq() is not None:
        num = awg.current_seq() + 1
    else:
        num = 1
    name = '{0:03d}_{name}'.format(num, name=sequence.name)
    awg_file_name = pulse_location + name + '.awg'
    seq_file_name = pulse_location + name + '.p'
    make_save_send_load_awg_file(awg, sequence.unwrap(), awg_file_name)
    save_sequence(sequence, seq_file_name)
    awg.current_seq(num)
    alazar.seq_mode(seq_mode)
    record_num = len(sequence)
    if seq_mode is 'on':
        for ctrl in acq_controllers:
            try:
                ctrl.records_per_buffer(record_num)
                try:
                    start = sequence.variable_array[0]
                    stop = sequence.variable_array[-1]
                except Exception:
                    start = 0
                    stop = len(sequence) - 1

                ctrl.acquisition.set_base_setpoints(
                    base_name=sequence.variable,
                    base_label=sequence.variable_label,
                    base_unit=sequence.variable_unit,
                    setpoints_start=start,
                    setpoints_stop=stop)
            except NotImplementedError:
                pass
    awg.all_channels_on()
    awg.run()


def set_up_sequence_multi_qubit(awg_list, alazar, acq_controllers, sequence,
                                seq_mode='on'):
    """
    Function which checks sample rate compatability between sequence and awg
    setting, uploads sequence to awg, sets the alazar instrument to the
    relevant sequence mode and sets the acquisition controller aquisiion
    parameter to have setpoints based on the sequence variable.

    Args:
        awg_list instrument (AWG5014)
        alazar instrument
        acq_controllers list
        sequence for upload
        seq_mode (default 'on')
    """
    pulse_location = get_pulse_location()
    try:
        num = get_latest_counter(pulse_location) + 1
    except (FileNotFoundError, OSError):
        num = 0
    for awg in awg_list:
        check_sample_rate(awg)
    current_seqs = [awg.current_seq()
                    for awg in awg_list if awg.current_seq() is not None]
    if len(current_seqs) > 0:
        num = max(current_seqs) + 1
    else:
        num = 1
    name = '{0:03d}_{name}'.format(num, name=sequence.name)
    seq_file_name = pulse_location + name + '.p'
    unwrapped_seq = sequence.unwrap()
    for i, awg in enumerate(awg_list):
        awg_file_name = pulse_location + name + '_' + awg.id_letter() + '.awg'
        make_save_send_load_awg_file(awg, unwrapped_seq[i], awg_file_name)
        awg.current_seq(num)
        awg.all_channels_on()
        awg.run()
    save_sequence(sequence, seq_file_name)
    alazar.seq_mode(seq_mode)
    record_num = len(sequence)
    if seq_mode is 'on':
        for ctrl in acq_controllers:
            try:
                ctrl.records_per_buffer(record_num)
                try:
                    start = sequence.variable_array[0]
                    stop = sequence.variable_array[-1]
                except Exception:
                    start = 0
                    stop = len(sequence) - 1

                ctrl.acquisition.set_base_setpoints(
                    base_name=sequence.variable,
                    base_label=sequence.variable_label,
                    base_unit=sequence.variable_unit,
                    setpoints_start=start,
                    setpoints_stop=stop)
            except NotImplementedError:
                pass
