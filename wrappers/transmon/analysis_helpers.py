import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from scipy import signal
from . import exp_decay, exp_decay_sin, get_calibration_dict, get_title, \
    save_fig, smooth_data_butter, smooth_data_SG, plot_cf_data, \
    get_sample_name, g_from_qubit, set_calibration_val, get_calibration_val

# TODO: write fit functions: qubit_from_ssb_measure,
#                            qubit_from_ssb_power_sweep,
#                            qubit_from_ssb_volt_sweep
# TODO: write fit for resonance and use this to find resonance
#    not argmin

###########################
# VNA
###########################


def find_peaks(dataset, fs, x_key="set", y_key="mag", cutoff=5e-6, order=2,
               subplot=None, widths=np.linspace(50, 150)):
    """
    Function which given a 1d array smoothes the data, finds resonances
    and plots results

    Args:
        dataset (qcodes DataSet)
        fs (float): frequency of sampling, passed to smoothed_data_butter
        x_key (str): string to look for data array on x axis
                        default "set"
        y_key (str): string to look for data array on y axis
                        default "mag"
        cutoff (float): used for smoothing passed to smooth_data_butter
                    default 5e-6
        order (int): used for smoothing passed to smooth_data_butter, default 5
        subplot (matplotlib AxesSubplot): subplot which this data should be
                    plotted on, default None will create new one
        widths (array): array peak widths to search for, passed to
                    signal.find_peaks_cwt, default np.linspace(50, 150)

    Returns:
        peakind (array): indices of resonances found
        frequencies (array): frequencies of resonances found
        subplot (matplotlib AxesSubplot): plot of results
    """
    try:
        setpoints = next(getattr(dataset, key)
                         for key in dataset.arrays.keys() if x_key in key)
        unsmoothed_data = next(getattr(dataset, key)
                               for key in dataset.arrays.keys()
                               if y_key in key)
    except Exception:
        raise Exception('could not get {} and {} arrays from dataset, check '
                        'dataset has these keys array names'.format(x_key,
                                                                    y_key))

    # smooth data
    smoothed_data = smooth_data_butter(
        unsmoothed_data, fs, cutoff=cutoff, order=order)

    # find peak indices
    peakind = signal.find_peaks_cwt(np.multiply(smoothed_data, -1), widths)

    try:
        num = dataset.data_num
    except AttributeError:
        num = dataset.location_provider.counter
        print('warning: check title, could be wrong datanum')

    # plot: unsmoothed data, smoothed data and add peak estimate values
    fig, subplot = plot_cf_data([unsmoothed_data, smoothed_data],
                                xdata=setpoints,
                                data_num=num,
                                axes_labels=['frequency(Hz)', 'S21'])
    subplot.plot(setpoints[peakind], smoothed_data[peakind], 'gs')
    txt = '{} resonances found at {}'.format(len(peakind), setpoints[peakind])

    fig.suptitle('{}_{}_find_peaks'.format(num, get_sample_name()),
                 fontsize=12)

    print(txt)
    return peakind, setpoints[peakind], subplot


def get_resonator_push(dataset, x_key="freq", y_key="pow", z_key="mag"):
    """
    Function which gets the change in resonance frequency from a power
    sweep dataset.

    Args:
        dataset (qcodes DataSet)
        x_key (str): string to look for data array on x axis
                        default "set"
        y_key (str): string to look for data array on y axis
                        default "pow"
        z_key (str): string to look for data arrays on z axis
                        default "mag"
    Returns:
        low_res (float): calculated resonance freq at low power
        high_res (float): calculated resonance freq at low power
        dif (float): value of push in Hz
        axarr (numpy.ndarray): subplot array
    """
    # get data for high and low power from dataset
    try:
        freq_array = next(getattr(dataset, key)
                          for key in dataset.arrays.keys() if x_key in key)[0]
        pow_array = next(getattr(dataset, key)
                         for key in dataset.arrays.keys() if y_key in key)
        mag_arrays = next(getattr(dataset, key)
                          for key in dataset.arrays.keys() if z_key in key)
    except Exception:
        raise Exception('could not get {}, {} and {} arrays from dataset, '
                        'check dataset has these keys array names'.format(
                            x_key, y_key, z_key))
    mag_high = mag_arrays[0]
    mag_low = mag_arrays[-1]
    smoothed_mag_low = smooth_data_SG(mag_low, 15, 6)
    smoothed_mag_high = smooth_data_SG(mag_high, 15, 6)

    # get freqeuncy of resonances for low and high power and power values
    low_res = freq_array[smoothed_mag_low.argmin()]
    high_res = freq_array[smoothed_mag_high.argmin()]
    low_pow = pow_array[-1]
    high_pow = pow_array[0]
    dif = low_res - high_res

    # for all pow sweeps smooth and get resonance
    res_data = np.zeros(len(mag_arrays))
    for i, sweep in enumerate(mag_arrays):
        smoothed_data = smooth_data_SG(sweep, 15, 6)
        res_data[i] = freq_array[smoothed_data.argmin()]

    # plot
    fig, axarr = plt.subplots(2)

    # subplot 1: high and low power cuts, smoothed and unsmoothed
    plot_cf_data([smoothed_mag_high, mag_high, smoothed_mag_low, mag_low],
                 subplot=axarr[0], xdata=freq_array,
                 legend_labels=['pow={}'.format(high_pow),
                                'pow={},smoothed'.format(high_pow),
                                'pow={}'.format(low_pow),
                                'pow={}, smoothed'.format(low_pow)],
                 axes_labels=['frequency (Hz)', 'S21'])

    # subplot 2: resonance for all power sweep with max and min lines plotted
    axarr[1].plot(pow_array, res_data, 'k-')
    axarr[1].plot([high_pow, low_pow], [high_res, high_res], 'r', lw=2,
                  label='high power res = {}'.format(high_res))
    axarr[1].plot([high_pow, low_pow], [low_res, low_res], 'b', lw=2,
                  label='low power res = {}'.format(low_res))
    axarr[1].set_xlabel('power (dBm)')
    axarr[1].set_ylabel('frequency (Hz)')
    axarr[1].legend(loc='upper right', fontsize=10)

    plt.tight_layout()

    try:
        fig.data_num = dataset.data_num
        fig.suptitle('dataset {}'.format(fig.data_num), fontsize=12)
        fig.text(0, 0, 'bare res: {}, pushed res: {}, push: {}'.format(
            high_res, low_res, dif))
    except AttributeError as e:
        fig.data_num = dataset.location_provider.counter
        print('dataset has no data_num set: {}'.format(e))

    return low_res, high_res, fig

###########################
# Alazar
###########################


def find_extreme(data, x_key="freq", y_key="mag", extr="min"):
    """
    Function which finds the min or max along the y axis and returns the
    x and y values at this point

    Args:
        data (qcodes dataset)
        x_key (string) (default 'freq'): string to search data arrays keys
            for to find x data
        y_key (string) (default 'mag'): string to search data arrays keys
            for to find y data
        extr ('min' or 'max') (default 'min'): whether to find max or min
            along this axis

    Returns:
        extr_x, y
    """
    try:
        x_key_array_name = [v for v in data.arrays.keys() if x_key in v][0]
    except IndexError:
        raise KeyError('keys: {} not in data array '
                       'names: {}'.format(x_key,
                                          list(data.arrays.keys())))
    try:
        y_key_array_name = [v for v in data.arrays.keys() if y_key in v][0]
    except IndexError:
        raise KeyError('keys: {} not in data array '
                       'names: {}'.format(y_key,
                                          list(data.arrays.keys())))

    x_data = getattr(data, x_key_array_name)
    y_data = getattr(data, y_key_array_name)
    if extr is "min":
        index = np.argmin(y_data)
        extr_y = np.amin(y_data)
    elif extr is "max":
        index = np.argmax(y_data)
        extr_y = np.amax(y_data)
    else:
        raise ValueError('extr must be set to "min" or "max", given'
                         ' {}'.format(extr))
    extr_x = x_data[index]
    return extr_x, extr_y


def recalculate_g(calib_update=False):
    """
    Function which uses the values in the calibration dictionary for expected
    qubit position, actual position, resonator push and g value to recalculate
    the g value for the current qubit and compare it to the old value.
    value

    Args:
        calib_update: whether to update the calibration dictionary value of the
            current qubit for g_value
    """
    qubit_freq = get_calibration_val('qubit_freq')
    expected_qubit_freq = get_calibration_val('expected_qubit_freq')
    old_g = get_calibration_val('g_value')
    bare_res = get_calibration_val('bare_res_freq')
    old_pushed_res = get_calibration_val('pushed_res_freq')
    new_pushed_res = get_calibration_val('cavity_freq')
    old_push = old_pushed_res - bare_res
    new_push = new_pushed_res - bare_res
    new_g = g_from_qubit(qubit_freq, bare_res, new_pushed_res)
    if calib_update:
        set_calibration_val('g_value', new_g)
    print('expected qubit freq: {}\n (from g of {}, push on resonator {})\n'
          'actual qubit freq: {}\n (gives g of {}, push on resonator {})'
          ''.format(
              expected_qubit_freq, old_g, old_push,
              qubit_freq, new_g, new_push))
    return new_g


def qubit_from_ssb_measure(dataset, gradient_sign=1, min_res_width=4e6):
    raise NotImplementedError


def qubit_from_ssb_power_sweep(dataset, gradient_sign=1, min_res_width=4e6):
    raise NotImplementedError


def qubit_from_ssb_volt_sweep(dataset, gradient_sign=1, min_res_width=4e6,
                              high_voltage=True):
    raise NotImplementedError


def get_t2(data, x_name='delay', y_name='magnitude',
           plot=True, subplot=None,
           initial_fit_params=[0.003, 1e-7, 10e7, 0, 0.01]):
    """
    Function which fits results of a data set to a sine wave modulated
    by an exponential decay and returns the fit parameters and the standard
    deviation errors on them.

    Args:
        data (qcodes dataset): 1d sweep to be fit to
        x_name (str) (default 'delay'): x axis key used to search data.arrays
            for corresponding data
        y_name (str) (default 'magnitude'): y axis key
        plot (default True)
        subplot (default None): subplot to plot in otherwise makes new figure
        expected_vals (default [0.003, 1e-7, 10e7, 0, 0.01]): initial values
            for fit function
    """
    x_data = getattr(getattr(data, x_name), 'ndarray')
    y_data = getattr(getattr(data, y_name), 'ndarray')
    x_units = getattr(getattr(data, x_name), 'unit')
    y_units = getattr(getattr(data, y_name), 'unit')
    popt, pcov = curve_fit(exp_decay_sin, x_data, y_data,
                           p0=initial_fit_params)
    errors = np.sqrt(np.diag(pcov))
    print('fit to equation of form y = a * exp(-x / b) * sin(c * x + d) + e'
          'gives:\na {}, b {}, c {}, d {}, e{}\n'
          'with one standard deviation errors:\n'
          'a {}, b {}, c {}, d {}, e{}'.format(popt[0], popt[1], popt[2],
                                               popt[3], popt[4], errors[0],
                                               errors[1], errors[2],
                                               errors[3], errors[4]))
    if plot:
        if subplot is None:
            fig, ax = plt.subplots()
        else:
            ax = subplot
            fig = ax.figure
        num = data.data_num
        try:
            qubit = get_calibration_dict()['current_qubit']
            title = '{}_{}_T2'.format(get_title(num), qubit)
            name = '{}_{}_T2'.format(num, qubit)
        except Exception:
            title = '{}_T2'.format(get_title(num))
            name = '{}_T2'.format(num)

        if not hasattr(fig, "data_num"):
            fig.data_num = num
        ax.plot(x_data,
                exp_decay_sin(x_data, *popt),
                label='fit: T2 {}{}'.format(popt[1],
                                            x_units))
        ax.plot(x_data, y_data, label='data')
        ax.set_xlabel('{} ({})'.format(x_name, x_units))
        ax.set_ylabel('{} ({})'.format(y_name, y_units))
        ax.set_title(title)
        ax.legend(loc='upper right', fontsize=10)
        save_fig(ax, name=name)
        return ax, popt, errors
    else:
        return popt, errors


def get_t1(data, x_name='delay', y_name='magnitude',
           plot=True, subplot=None, initial_fit_params=[0.05, 1e-6, 0.01]):
    """
    Function which fits results of a data set to an exponential decay and
    returns the fit parameters and the standard deviation errors on them.

    Args:
        data (qcodes dataset): 1d sweep to be fit to
        x_name (str) (default 'delay'): x axis key used to search data.arrays
            for corresponding data
        y_name (str) (default 'magnitude'): y axis key
        plot (default True)
        subplot (default None): subplot to plot in otherwise makes new figure
        expected_vals (default 0.05, 1e-6, 0.01]): initial values
            for fit function
    """
    x_data = getattr(getattr(data, x_name), 'ndarray')
    y_data = getattr(getattr(data, y_name), 'ndarray')
    x_units = getattr(getattr(data, x_name), 'unit')
    y_units = getattr(getattr(data, y_name), 'unit')
    popt, pcov = curve_fit(exp_decay, x_data, y_data, p0=initial_fit_params)
    errors = np.sqrt(np.diag(pcov))
    print('fit to equation of form y = a * exp(-x / b) + c gives:\n'
          'a {}, b {}, c {}\n'
          'with one standard deviation errors:\n'
          'a {}, b {}, c {}'.format(popt[0], popt[1], popt[2],
                                    errors[0], errors[1], errors[2]))
    if plot:
        if subplot is None:
            fig, ax = plt.subplots()
        else:
            ax = subplot
            fig = ax.figure
        num = data.data_num
        try:
            qubit = get_calibration_dict()['current_qubit']
            title = '{}_{}_T1'.format(get_title(num), qubit)
            name = '{}_{}_T1'.format(num, qubit)
        except Exception:
            title = '{}_T1'.format(get_title(num))
            name = '{}_T1'.format(num)

        if not hasattr(fig, "data_num"):
            fig.data_num = num
        ax.plot(x_data,
                exp_decay(x_data, *popt),
                label='fit: T1 {}{}'.format(popt[1],
                                            x_units))
        ax.plot(x_data, y_data, label='data')
        ax.set_xlabel('{} ({})'.format(x_name, x_units))
        ax.set_ylabel('{} ({})'.format(y_name, y_units))
        ax.xaxis.set_major_formatter(mtick.FormatStrFormatter('%.1e'))
        ax.set_title(title)
        ax.legend(loc='upper right', fontsize=10)
        save_fig(ax, name=name)
        return ax, popt, errors
    else:
        return popt, errors
