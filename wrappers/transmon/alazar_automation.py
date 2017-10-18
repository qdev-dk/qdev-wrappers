import numpy as np
import time
import datetime

from . import do_cavity_freq_sweep, find_extreme, set_calibration_val, \
    set_single_demod_freq, get_calibration_val, set_up_sequence, \
    sweep1d, measure, measure_ssb, sweep2d_ssb, check_seq_uploaded, \
    get_demod_freq, get_t1, get_t2

from .sequencing import make_spectroscopy_SSB_sequence, make_rabi_sequence, \
    make_t1_sequence, make_ramsey_sequence

# TODO: find qubit to compare to average
# TODO: complete do_tracking_ssb_gate_sweep
# TODO: allow easy switching between Daniel and own
# TODO: tracking ssb_time_sweep to use last slice of spectrscopy to see if
#     qubit is there and good enough
# TODO: write calibrate pi pulse, get_t1, get_t2s, do_ramsey
# TODO: add rabis, t1, t2 and anharmonicity option to tracking sweeps
# TODO: drag
# TODO: 1 million kwargs to **kwargs
# TODO: check seq uploaded in automated cavity calibration (and then remove from script)
# TODO: docstrings


def calibrate_cavity(cavity, localos, acq_ctrl, alazar, centre_freq=None,
                     demod_freq=None, calib_update=True, cavity_pow=None,
                     localos_pow=None, detuning=3e5, live_plot=True,
                     qubit_index=None):
    """
    Automation function which sweeps the cavity and then detunes sets the
    cavity and local oscillator frequency for readout.

    Args:
        cavity (R&S instrument)
        localos (R&S instrument)
        acq_ctrl (alazar acq controller instrument): to set demod freq on
        alazar (alazar instrument): to set seq mode on
        centre_freq (float) (default None): freq to centre sweep on, default is
            to use the current frequency
        demod_freq (float) (default None): demod freq to set, default is to use
            the current demod freq
        calib_update (bool) (default True): whether to updatre the calibration
            dictionary or not
        cavity_pow (int) (default None): power to set the cavity to, default
            is to use the current power
        localos_pow (int) (default None): power to set the localos to,
            default is to use the current power
        detuning (float) (default 3e5): frequency to detune the cavity from the
            minima of the resonance for for readout
        live_plot (bool) (default True): whether to live plot
    """
    if centre_freq is None:
        centre_freq = cavity.frequency()
    if cavity_pow is not None:
        cavity.power(cavity_pow)
    if localos_pow is not None:
        localos.power(localos_pow)
    alazar_mode = alazar.seq_mode()
    alazar.seq_mode('off')
    cavity.status('on')
    localos.status('on')
    good_demod_freq = demod_freq or get_demod_freq(cavity, localos, acq_ctrl)
    data, plot = do_cavity_freq_sweep(cavity, localos, centre_freq, acq_ctrl,
                                      cavity_pm=3e6, freq_step=0.1e6,
                                      demod_freq=good_demod_freq,
                                      live_plot=True, key="mag", save=True)
    cavity_res, mag = find_extreme(
        data, x_key="frequency_set", y_key="mag", extr="min")
    good_cavity_freq = cavity_res + detuning
    if calib_update:
        set_calibration_val('cavity_freq', good_cavity_freq,
                            qubit_index=qubit_index)
        set_calibration_val('cavity_pow', cavity_pow or cavity.power(),
                            qubit_index=qubit_index)
        set_calibration_val('demod_freq', good_demod_freq,
                            qubit_index=qubit_index)
        set_calibration_val('localos_pow', localos_pow or localos.power(),
                            qubit_index=qubit_index)
    set_single_demod_freq(cavity, localos, [acq_ctrl],
                          demod_freq=good_demod_freq,
                          cavity_freq=good_cavity_freq)
    alazar.seq_mode(alazar_mode)
    print('cavity_freq set to {}, mag = {}'.format(good_cavity_freq, mag))


def find_qubit(awg, alazar, acq_ctrl, qubit, start_freq=4e9, stop_freq=6e9,
               qubit_power=None, calib_update=True, channels=[1, 2, 3, 4],
               pulse_mod=False):
    """
    Automation function which searches in a specified frequency range for a
    qubit.

    Args:
        awg (AWG5014C instrument): to upload ssb seq to
        alazar (alazar instrument): to set seq mode on
        acq_ctrl (alazar acq controller instrument): to set up ssb seq on
        qubit (R&S instrument): qubit microwave source to sweep frequency of
        start_freq (float) (default 4e9): lower frequency for the search to
            start at
        stop_freq (float) (default 6e9): upper frequecy for the seatch to end
            at
        qubit_power (int) (default None): power to drive the qubit at, default
            is to use the spec_pow in the calibration_dict
        calib_update (bool) (default True): whether to update the
            calibration_dict with the qubit_freq and spec_pow

    Returns:
        qubit_freq: assumes detuning on resonator is +ive so returns the
            frequency at which the maximum response is recorded in the
            resonator
        qubit_mag: the magnitude of this response
    """
    old_power = qubit.power()
    old_seq_mode = alazar.seq_mode()
    seq_uploaded = check_seq_uploaded(
        awg, 'spectroscopy', {'pulse_mod': pulse_mod},
        start=0, stop=200e-6, step=1e-6)
    if not seq_uploaded:
        ssb_seq = make_spectroscopy_SSB_sequence(
            0, 200e-6, 1e-6, channels=channels, pulse_mod=pulse_mod)
        set_up_sequence(awg, alazar, [acq_ctrl], ssb_seq, seq_mode='on')
    else:
        alazar.seq_mode('on')
    if qubit_power is None:
        qubit_power = get_calibration_val('spec_pow')
    qubit.status('on')
    qubit.power(qubit_power)
    qubit_freq = None
    qubit_mag = 0
    for centre in np.linspace(start_freq + 100e6, stop_freq - 100e6,
                              num=(stop_freq - start_freq) / 200e6):
        ssb_centre = centre
        data, pl = measure_ssb(qubit, acq_ctrl, ssb_centre, do_plots=True)
        freq, maximum = find_extreme(data, x_key="set", extr="max")
        if maximum > qubit_mag:
            qubit_freq = freq
            qubit_mag = maximum
    if calib_update:
        set_calibration_val('qubit_freq', qubit_freq)
        set_calibration_val('spec_pow', qubit_power)
    qubit.power(old_power)
    alazar.seq_mode(old_seq_mode)
    print('qubit found at {}, mag {}'.format(qubit_freq, qubit_mag))
    return qubit_freq


def do_tracking_ssb_time_sweep(qubit, cavity, time_param, localos,
                               rec_acq_ctrl, ave_acq_ctrl, alazar, awg,
                               outer_loop_number, outer_loop_delay,
                               inner_loop_time, inner_loop_delay_step,
                               initial_cavity_freq=None):
    """
    Automated function which executes qubit spectrocopy, sweeping time,
    with periodic cavity recalibration and qubit finding.

    Args:
        qubit (R&S instrument)
        cavity (R&S instrument)
        localos (R&S instrument)
        rec_acq_ctrl (alazar acq controller instrument)
        ave_acq_ctrl (alazar acq controller instrument)
        alazar (alazar instrument)
        awg (AWG5014C instrument)
        outer_loop_number: numer of times to recalibrate cavity and find qubit
        outer_loop_delay: seconds to wait after each time sweep before
            repeating cavity calibration, qubit finding and time sweep
        inner_loop_time: time to spend on each spectroscopy sweep
        inner_loop_delay_step: step size in s of spectroscopy time sweep
        initial_cavity_freq: starting point for the cavity sweep, if none given
            then current frequency is used
    """
    start_time = time.time()
    duration = (outer_loop_number * (outer_loop_delay + inner_loop_time + 120))
    finish_time = start_time + duration
    print('"do_tracking_ssb_time_sweep started at {}\nExpected duration: {}\n'
          'Expected finish: {}'.format(time.ctime(start_time),
                                       datetime.timedelta(seconds=duration),
                                       time.ctime(finish_time)))
    for i, t in enumerate(np.linspace(1, outer_loop_number,
                                      num=outer_loop_number)):
        qubit.status('off')
        if i == 0:
            cav_freq = initial_cavity_freq
        else:
            cav_freq = None
        calibrate_cavity(cavity, localos, ave_acq_ctrl, alazar,
                         centre_freq=cav_freq)
        qubit_freq, mag = find_qubit(awg, alazar, rec_acq_ctrl, qubit)
        start = time.clock()
        stop = start + inner_loop_time
        data, plots = sweep2d_ssb(qubit, rec_acq_ctrl, qubit_freq, time_param,
                                  start, stop, inner_loop_delay_step,
                                  delay=inner_loop_delay_step, key="mag")
        time.sleep(outer_loop_delay)


def do_tracking_ssb_gate_sweep(qubit, cavity, localos, rec_acq_ctrl,
                               ave_acq_ctrl, gate,
                               initial_qubit_freq, initial_cavity_freq,
                               gate_start, gate_stop,
                               gate_step=0.01, live_plot=True):
    raise NotImplementedError


def do_rabis(awg, alazar, acq_ctrl, qubit, start=0, stop=200e-9,
             step=1e-9, qubit_power=None, SSBfreq=None,
             qubit_freq=None, freq_pm=10e6, freq_step=2e6, gaussian=False,
             pulse_mod=False, channels=[1, 2, 3, 4]):
    """
    Automated function which uploads rabis to the awg and then
    """
    seq_uploaded = check_seq_uploaded(
        awg, 'rabi', {'SSBfreq': SSBfreq, 'gaussian': gaussian,
                      'pulse_mod': pulse_mod},
        start=start, stop=stop, step=step)

    if not seq_uploaded:
        seq_to_upload = make_rabi_sequence(
            start, stop, step, SSBfreq=SSBfreq, channels=channels,
            pulse_mod=pulse_mod, gaussian=gaussian)
        set_up_sequence(awg, alazar, [acq_ctrl], seq_to_upload, seq_mode=1)
    else:
        alazar.seq_mode(1)

    old_power = qubit.power()
    old_frequency = qubit.frequency()
    old_status = qubit.status()
    qubit_power = qubit_power or get_calibration_val('pi_pulse_pow')
    qubit.power(qubit_power)
    qubit.status('on')

    qubit_freq = qubit_freq or get_calibration_val('qubit_freq')
    centre = qubit_freq + SSBfreq if SSBfreq is None else qubit_freq
    freq_start = centre - freq_pm
    freq_stop = centre + freq_pm

    data, plot = sweep1d(acq_ctrl.acquisition, qubit.frequency, freq_start,
                         freq_stop, freq_step, do_plots=True)

    qubit.power(old_power)
    qubit.frequency(old_frequency)
    qubit.status(old_status)

    return data, plot


def do_t1(awg, alazar, acq_ctrl, qubit, start=0, stop=5e-6, step=50e-9,
          qubit_power=None, SSBfreq=None, qubit_freq=None, gaussian=False,
          pulse_mod=False, channels=[1, 2, 3, 4]):
    seq_uploaded = check_seq_uploaded(
        awg, 't1', {'SSBfreq': SSBfreq, 'gaussian': gaussian,
                    'pulse_mod': pulse_mod},
        start=start, stop=stop, step=step)

    if not seq_uploaded:
        seq_to_upload = make_t1_sequence(
            start, stop, step, SSBfreq=SSBfreq, channels=channels,
            pulse_mod=pulse_mod, gaussian=gaussian)
        set_up_sequence(awg, alazar, [acq_ctrl], seq_to_upload, seq_mode=1)
    else:
        alazar.seq_mode(1)

    old_power = qubit.power()
    old_frequency = qubit.frequency()
    old_status = qubit.status()
    qubit_power = qubit_power or get_calibration_val('pi_pulse_pow')
    qubit_freq = qubit_freq or get_calibration_val('qubit_freq')
    qubit.power(qubit_power)
    qubit.status('on')
    centre = qubit_freq + SSBfreq if SSBfreq is None else qubit_freq
    qubit.frequency(centre)

    data, plot1 = measure(acq_ctrl.acquisition, do_plots=True)
    plot2, info, errors = get_t1(data)
    print('T1 fit params: {}, errors: {}'.format(info, errors))
    qubit.power(old_power)
    qubit.frequency(old_frequency)
    qubit.status(old_status)

    return data, plot1, plot2


def do_ramsey(awg, alazar, acq_ctrl, qubit, start=0, stop=2e-6,
              step=20e-9, qubit_power=None, SSBfreq=None,
              qubit_freq=None, freq_pm=10e6, freq_step=2e6, gaussian=False,
              pulse_mod=False, channels=[1, 2, 3, 4]):
    seq_uploaded = check_seq_uploaded(
        awg, 'ramsey', {'SSBfreq': SSBfreq, 'gaussian': gaussian,
                        'pulse_mod': pulse_mod},
        start=start, stop=stop, step=step)

    if not seq_uploaded:
        seq_to_upload = make_ramsey_sequence(
            start, stop, step, SSBfreq=SSBfreq, channels=channels,
            pulse_mod=pulse_mod, gaussian=gaussian)
        set_up_sequence(awg, alazar, [acq_ctrl], seq_to_upload, seq_mode=1)
    else:
        alazar.seq_mode(1)

    old_power = qubit.power()
    old_frequency = qubit.frequency()
    old_status = qubit.status()
    qubit_power = qubit_power or get_calibration_val('pi_pulse_pow')
    qubit.power(qubit_power)
    qubit.status('on')

    qubit_freq = qubit_freq or get_calibration_val('qubit_freq')
    centre = qubit_freq + SSBfreq if SSBfreq is None else qubit_freq
    freq_start = centre - freq_pm
    freq_stop = centre + freq_pm

    data, plot = sweep1d(acq_ctrl.acquisition, qubit.frequency, freq_start,
                         freq_stop, freq_step, do_plots=True)

    qubit.power(old_power)
    qubit.frequency(old_frequency)
    qubit.status(old_status)

    return data, plot


def do_t2_star(awg, alazar, acq_ctrl, qubit, start=0, stop=2e-6, step=20e-9,
               qubit_power=None, SSBfreq=None, qubit_freq=None, gaussian=False,
               pulse_mod=False, channels=[1, 2, 3, 4]):
    seq_uploaded = check_seq_uploaded(
        awg, 'ramsey', {'SSBfreq': SSBfreq, 'gaussian': gaussian,
                        'pulse_mod': pulse_mod},
        start=start, stop=stop, step=step)

    if not seq_uploaded:
        seq_to_upload = make_ramsey_sequence(
            start, stop, step, SSBfreq=SSBfreq, channels=channels,
            pulse_mod=pulse_mod, gaussian=gaussian)
        set_up_sequence(awg, alazar, [acq_ctrl], seq_to_upload, seq_mode=1)
    else:
        alazar.seq_mode(1)

    old_power = qubit.power()
    old_frequency = qubit.frequency()
    old_status = qubit.status()
    qubit_power = qubit_power or get_calibration_val('pi_pulse_pow')
    qubit_freq = qubit_freq or get_calibration_val('qubit_freq')
    qubit.power(qubit_power)
    qubit.status('on')
    qubit.frequency(qubit_freq)

    data, plot1 = measure(acq_ctrl.acquisition, do_plots=True)
    plot2, info, errors = get_t2(data)
    print('T2 fit params: {}, errors: {}'.format(info, errors))
    qubit.power(old_power)
    qubit.frequency(old_frequency)
    qubit.status(old_status)

    return data, plot1, plot2


def calibrate_pi_pulse(awg, alazar, acq_ctrl, qubit, start_dur=0,
                       stop_dur=200e-9, step_dur=1e-9, pi_pulse_amp=None,
                       qubit_power=None, freq_centre=None, freq_pm=10e6,
                       freq_step=2e6, live_plot=True, calib_update=True,
                       gaussian=False, sigma_cutoff=None, pulse_mod=False):
    raise NotImplementedError


def do_t2_echo(awg, alazar, acq_ctrl, qubit, start_delay=0, stop_delay=10e-6,
               step_dur=1e-9, pi_pulse_amp=None, qubit_power=None,
               freq_centre=None, freq_pm=10e6, freq_step=2e6, live_plot=True,
               calib_update=True, gaussian=False, sigma_cutoff=None,
               pulse_mod=False):
    raise NotImplementedError
