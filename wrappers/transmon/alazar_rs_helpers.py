import qcodes as qc
from wrappers.sweep_functions import _do_measurement, \
    _select_plottables
from . import sweep1d, measure, get_calibration_val

# TODO: exception types
# TODO: TWPA settings
# TODO: _ ?
# TODO: write set_demod_freqs


def get_demod_freq(cavity, localos, acq_ctrl, SSBfreq=0):
    """
    Gets demodulation frequency based on cavity and
    local oscilator and checks that aqc controller is demodulating
    at this frequency.

    Args:
        cavity instrument (r&s SGS100)
        localos instrument (r&s SGS100)
        acq_ctrl instrument (alazar acq controller)

    Returns:
        demod freq
    """
    lo, cav = localos.frequency(), cavity.frequency()
    demod = lo - (cav - SSBfreq)
    acq_freqs = acq_ctrl.demod_freqs()
    if demod not in acq_freqs:
        raise Exception('demod freq {} (from cavity freq {} and localos '
                        'freq {}) not in acq controller demodulation '
                        'frequencies: {}.'.format(demod, cav, lo, acq_freqs))
    else:
        return demod


def set_single_demod_freq(cavity, localos, acq_ctrls, demod_freq=None,
                          cavity_freq=None, localos_freq=None, SSBfreq=0):
    if all([i is not None for i in [demod_freq, cavity_freq, localos_freq]]):
        raise Exception('Set up demodulation by setting max 2 out of '
                        '[demod_freq, cavity_freq, localos_freq], not all '
                        'three')
    if localos_freq is None:
        if cavity_freq is None:
            cavity_freq = cavity.frequency()
        else:
            cavity.frequency(cavity_freq)
        if demod_freq is None:
            demod_freq = localos.frequency() - (cavity_freq - SSBfreq)
        else:
            localos.frequency(cavity_freq - SSBfreq + demod_freq)
    elif cavity_freq is None:
        localos.frequency(localos_freq)
        if demod_freq is None:
            demod_freq = localos_freq - (cavity.frequency() - SSBfreq)
        else:
            cavity.frequency(localos_freq - demod_freq + SSBfreq)
    else:
        localos.frequency(localos_freq)
        cavity.frequency(cavity_freq)
        demod_freq = localos_freq - (cavity_freq - SSBfreq)
    for ctrl in acq_ctrls:
        remove_demod_freqs(ctrl)
        ctrl.demod_freqs.add_demodulator(demod_freq)
    cavity.status('on')
    localos.status('on')


def set_demod_freqs(cavity_list, localos, acq_ctrls,
                    localos_freq=None, cavity_freqs=None,
                    demod_freqs=None):
    if all([i is not None for
            i in [demod_freqs, cavity_freqs, localos_freq]]):
        raise Exception('Set up demodulation by setting max 2 out of '
                        '[demod_freqs, cavity_freqs, localos_freq], not all '
                        'three')
    if any(i is not None for i in [demod_freqs, cavity_freqs]):
        length = len(cavity_list)
        if not all(len(x) == length for x in [cavity_freqs, demod_freqs]):
            raise Exception(
                'cavity list length not equal to cavity freqs list length '
                'and demod_freqs lengths: {}'.format(
                    [length, len(cavity_freqs), len(demod_freqs)]))

    if all([i is not None for i in [cavity_freqs, demod_freqs]]):
        localos_freq = cavity_freqs[0] + demod_freqs[0]
        for i, cav_f in enumerate(cavity_freqs):
            if cav_f[i] + demod_freqs[i] != localos_freq:
                raise Exception(
                    'Cavity frequencies and demod frequencies set'
                    ' but these do not all correspond to the same value for '
                    'the local oscillator. This is unphsyical')
            cavity_list[i].frequency(cav_f)
        localos.frequency(localos_freq)
    elif localos_freq is None:
        localos_freq = localos.frequency()
        if cavity_freqs is not None:
            for i, cavity in enumerate(cavity_list):
                cavity.frequency(cavity_freqs[i])
                demod_freqs[i] = localos_freq - cavity_freqs[i]
        elif demod_freqs is not None:
            for i, cavity in enumerate(cavity_list):
                cavity.frequency(localos_freq + demod_freqs[i])
        else:
            demod_freqs = [localos_freq - c.frequency() for c in cavity_list]

    for ctrl in acq_ctrls:
        remove_demod_freqs(ctrl)

    for i, cav in enumerate(cavity_list):
        cav.status('on')
        for ctrl in acq_ctrls:
            ctrl.demod_freqs.add_demodulator(demod_freqs[i])
    localos.status('on')


def set_demod_freqs_SSB(cavity, localos, acq_ctrls, SSBfreqs,
                        localos_freq=None, cavity_freq=None,
                        demod_freqs=None):
    if all([i is not None for
            i in [demod_freqs, cavity_freq, localos_freq]]):
        raise Exception('Set up demodulation by setting max 2 out of '
                        '[demod_freqs, cavity_freq, localos_freq], '
                        'not all three')
    if demod_freqs is not None:
        if len(demod_freqs) != len(SSBfreqs):
            raise Exception(
                'demod_freqs list length not equal to SSBfreqs freqs list '
                'length: {}'.format(
                    [len(demod_freqs), len(SSBfreqs)]))

    if localos_freq is None:
        if cavity_freq is None:
            cavity_freq = cavity.frequency()
        else:
            cavity.frequency(cavity_freq)
        if demod_freqs is None:
            localos_freq = localos.frequency()
            demod_freqs = [(localos_freq - (cavity_freq + SSBfreq))
                           for SSBfreq in SSBfreqs]
        else:
            localos_freq = cavity_freq - SSBfreqs[0] + demod_freqs[0]
            for i, SSBfreq in enumerate(SSBfreqs):
                if cavity_freq - SSBfreq + demod_freqs[i] != localos_freq:
                    raise Exception(
                        'SSB frequencies and demod frequencies set'
                        ' but these do not all correspond to the same value '
                        'for the local oscillator and cavity.')
            localos.frequency(localos_freq)
    elif cavity_freq is None:
        localos.frequency(localos_freq)
        if demod_freqs is None:
            cavity_freq = cavity.frequency()
            demod_freqs = [(localos_freq - (cavity_freq + SSBfreq))
                           for SSBfreq in SSBfreqs]
        else:
            cavity_freq = localos_freq + SSBfreqs[0] - demod_freqs[0]
            for i, SSBfreq in enumerate(SSBfreqs):
                if cavity_freq - SSBfreq + demod_freqs[i] != localos_freq:
                    raise Exception(
                        'SSB frequencies and demod frequencies set'
                        ' but these do not all correspond to the same value '
                        'for the local oscillator and cavity.')
            cavity.frequency(cavity_freq)
    else:
        cavity.frequency(cavity_freq)
        localos.frequency(localos_freq)
        demod_freqs = [(localos_freq - (cavity_freq + SSBfreq))
                       for SSBfreq in SSBfreqs]

    for ctrl in acq_ctrls:
        remove_demod_freqs(ctrl)

    for i, demod_freq in enumerate(demod_freqs):
        for ctrl in acq_ctrls:
            ctrl.demod_freqs.add_demodulator(demod_freqs[i])
    localos.status('on')
    cavity.status('on')


def remove_demod_freqs(acq_ctrl):
    """
    Function whish removes demod freqs from acquisition controller

    Args:
        acq_ctrl (alazar acq controller)
    """
    freqs = acq_ctrl.demod_freqs.get()
    for freq in freqs:
        acq_ctrl.demod_freqs.remove_demodulator(freq)


def do_cavity_freq_sweep(cavity, localos, cavity_freq, acq_ctrl,
                         cavity_pm=10e6, freq_step=1e6, demod_freq=None,
                         delay=0.01, do_plots=True):
    """
    Function which sweeps the cavity frequency around central value by pm_range
    and measures using given acq_ctr, also steps local os to keep same demod
    freq.

    Args:
        cavity instrument (r&s SGS100)
        localos instrument (r&s SGS100)
        cavity_freq: central cavity drive freq
        acq_ctrl instrument (alazar acq controller)
        cavity_pm (float) (default 10e6): sweep range will be cavity_freq +-
            this value
        freq_step (float) (default 1e6)
        demod_freq (float) (default None): default uses the current value
        delay (default 0.01): mimimum time to spend on each point
        do_plots: Default True: If False no plots are produced.
            Data is still saved and can be displayed with show_num.

    Returns:
        data (qcodes dataset)
        plot: QT plot
    """
    if demod_freq is None:
        demod_freq = get_demod_freq(cavity, localos, acq_ctrl)
    start = cavity_freq - cavity_pm
    stop = cavity_freq + cavity_pm
    loop = qc.Loop(cavity.frequency.sweep(start,
                                          stop,
                                          freq_step), delay).each(
        qc.Task(localos.frequency.set,
                (cavity.frequency + demod_freq)),
        acq_ctrl.acquisition)

    set_params = ((cavity.frequency, start, stop),)
    meas_params = _select_plottables(acq_ctrl.acquisition)

    plot, data = _do_measurement(loop, set_params, meas_params,
                                 do_plots=do_plots)

    return data, plot
   
def do_cavity_freq_sweep2d(cavity, localos, other_param, cavity_freq, acq_ctrl,
                           start, stop, step,
                         cavity_pm=10e6, freq_step=1e6, demod_freq=None,
                         delay=0.01, do_plots=True):
    """
    Function which sweeps the cavity frequency around central value by pm_range
    and measures using given acq_ctr, also steps local os to keep same demod
    freq.

    Args:
        cavity instrument (r&s SGS100)
        localos instrument (r&s SGS100)
        cavity_freq: central cavity drive freq
        acq_ctrl instrument (alazar acq controller)
        cavity_pm (float) (default 10e6): sweep range will be cavity_freq +-
            this value
        freq_step (float) (default 1e6)
        demod_freq (float) (default None): default uses the current value
        delay (default 0.01): mimimum time to spend on each point
        do_plots: Default True: If False no plots are produced.
            Data is still saved and can be displayed with show_num.

    Returns:
        data (qcodes dataset)
        plot: QT plot
    """
    if demod_freq is None:
        demod_freq = get_demod_freq(cavity, localos, acq_ctrl)
    freq_start = cavity_freq - cavity_pm
    freq_stop = cavity_freq + cavity_pm
    loop = qc.Loop(
            other_param.sweep(start, stop, step)).loop(
                    cavity.frequency.sweep(freq_start, freq_stop, freq_step), delay).each(
            qc.Task(localos.frequency.set,
                    (cavity.frequency + demod_freq)),
        acq_ctrl.acquisition)

    set_params = ((other_param, start, stop), (cavity.frequency, freq_start, freq_stop))
    meas_params = _select_plottables(acq_ctrl.acquisition)

    plot, data = _do_measurement(loop, set_params, meas_params,
                                 do_plots=do_plots)

    return data, plot

def set_cavity_from_calib_dict(cavity, localos, acq_ctrls, num_avg=1000):
    """
    Funtion which sets the cavity, local oscillator and the acq controllers to
    have correct demodulation settings for single qubit readout as well as
    averaging settings and int_time, int_delay and cavity power, localos_power

    Args:
        cavity (R&S instrument)
        localos (R&S instrument)
        acq_ctrls (list of alazar acq controller instruments)
        num_avg (int): num of averages for acq controller
    """
    for acq_ctrl in acq_ctrls:
        acq_ctrl.int_time(get_calibration_val('int_time'))
        acq_ctrl.int_delay(get_calibration_val('int_delay'))
        acq_ctrl.num_avg(num_avg)
    cavity.power(get_calibration_val('cavity_pow'))
    localos.power(get_calibration_val('localos_pow'))
    set_single_demod_freq(cavity, localos, acq_ctrls,
                          get_calibration_val('demod_freq'),
                          cavity_freq=get_calibration_val('cavity_freq'))


def sweep2d_ssb(qubit, acq_ctrl, centre_freq, sweep_param,
                start, stop, step, delay=0.01, do_plots=True):
    """
    Function which sets up a ssb spectroscopy 'hardware controlled sweep'
    +-100MHz around cenre_freq on one axis and sweeps another parameter on
    the other axis. Assumes correct awg upload. Produces a 2d plot.

    Args:
        qubit (R&S instrument)
        acq_ctrls(alazar acq controller instrument)
        centre_freq (float): freq to centre ssb spectoscopy around
        sweep_param (qcodes parameter): param top sweep on y axis
        start: start value for sweep_param
        stop: stop value for sweep param
        step: step value for sweep param
        delay (default 0.01): delay value beween step of sweep param
        do_plots: Default True: If False no plots are produced.
            Data is still saved and can be displayed with show_num.


    Returns:
        sweep1d result
    """
    qubit.frequency(centre_freq + 100e6)
    acq_ctrl.acquisition.set_base_setpoints(
        base_name='ssb_qubit_drive_freq',
        base_label='Qubit Drive Frequency',
        base_unit='Hz',
        setpoints_start=centre_freq + 100e6,
        setpoints_stop=centre_freq - 100e6)
    return sweep1d(acq_ctrl.acquisition, sweep_param, start,
                   stop, step, delay=delay, do_plots=do_plots)


def measure_ssb(qubit, acq_ctrl, centre_freq,
                do_plots=True):
    """
    Function which does a 'hardware controlled sweep' for single sideband
    spectroscopy uploaded to the awg +-100MHz around the centre_freq.
    Produces a 3d plot.

    Args:
        qubit (R&S instrument)
        acq_ctrls(alazar acq controller instrument)
        centre_freq (float): freq to centre ssb spectoscopy around
        do_plots: Default True: If False no plots are produced.
            Data is still saved and can be displayed with show_num.

    Returns:
        measure result
    """
    qubit.frequency(centre_freq + 100e6)
    acq_ctrl.acquisition.set_base_setpoints(
        base_name='ssb_qubit_drive_freq',
        base_label='Qubit Drive Frequency',
        base_unit='Hz',
        setpoints_start=centre_freq + 100e6,
        setpoints_stop=centre_freq - 100e6)
    return measure(acq_ctrl.acquisition)
