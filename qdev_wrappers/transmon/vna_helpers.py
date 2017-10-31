from . import sweep1d

"""
This set of convenience functions are used to make measuring with the VNA
faster and easier.
"""

#########################
# General functions
#########################


def sweep2d_vna(v1, startf, stopf, stepf,
                sweep_param2, start2, stop2, step2,
                delay=0.01, do_plots=True):
    """
    Function which fakes doing a 2d sweep by setting up the vna to
    do a 'hard' frequency sweep over the given range and then executing
    a 'soft' sweep over the other parameter

    Args:
        v1 (instrument): VNA instrument
        startf (float): tarting frequency
        stopf (float): final frequency
        stepf (float): frequency increment
        sweep_param2 (qcodes parameter): second parameter to sweep
        start2 (float): starting value for second parameter
        stop2 (float): final value for second parameter
        step2 (float): step value for second parameter
        delay (float): min time to wait between step of second parameter
        do_plots: Default True: If False no plots are produced.
            Data is still saved and can be displayed with show_num.

    Returns:
        dataset, plot
    """
    v1.channels.S21.start(startf)
    v1.channels.S21.stop(stopf)
    npts = int((stopf - startf) / stepf + 1)
    v1.channels.S21.npts(npts)
    dataset, plot = sweep1d(
        v1.channels.S21.trace, sweep_param2, start2, stop2, step2,
        delay=delay, do_plots=do_plots)
    return dataset, plot


def gates_to_zero(dec_chans):
    """
    Sets all gate channels to 0
    """
    for chan in dec_chans:
        chan(0)
