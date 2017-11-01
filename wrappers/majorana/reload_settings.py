import logging
import qcodes as qc
from qcodes.utils.validators import Numbers
from qcodes.instrument_drivers.devices import VoltageDivider

from wrappers.configreader import Config

log = logging.getLogger(__name__)


def bias_channels():
    """
    A convenience function returning a list of bias channels.
    """

    configs = Config.default
    configs.reload()

    bias_chan1 = configs.get('Channel Parameters', 'topo bias channel')
    # bias_chan2 = configs.get('Channel Parameters', 'left sensor bias channel')
    # bias_chan3 = configs.get('Channel Parameters', 'right sensor bias channel')

    # return [int(bias_chan1), int(bias_chan2), int(bias_chan3)]
    return [int(bias_chan1)]


def used_channels():
    """
    Return a list of currently labelled channels as ints.
    """

    configs = Config.default
    configs.reload()

    l_chs = configs.get('QDac Channel Labels')
    return sorted([int(key) for key in l_chs.keys()])


def used_voltage_params():
    """
    Returns a list of qdac voltage parameters for the used channels
    """
    station = qc.Station.default

    qdac = station['qdac']

    chans = sorted(used_channels())
    voltages = [qdac.channels[ii - 1] for ii in chans]

    return voltages


def channel_labels():
    """
    Returns a dict of the labelled channels. Key: channel number (int),
    value: label (str)
    """
    configs = Config.default
    configs.reload()

    labs = configs.get('QDac Channel Labels')
    output = dict(zip([int(key) for key in labs.keys()], labs.values()))

    return output


def print_voltages_all():
    """
    Convenience function for printing all qdac voltages
    """

    station = qc.Station.default
    qdac = station['qdac']

    for channel in qdac.channels:
        print('{}: {} V'.format(channel.name, channel.v.get()))

    check_unused_qdac_channels()


def qdac_slopes():
    """
    Returns a dict with the QDac slopes defined in the config file
    """

    configs = Config.default
    configs.reload()

    qdac_slope = float(configs.get('Ramp speeds',
                                   'max rampspeed qdac'))
    bg_slope = float(configs.get('Ramp speeds',
                                 'max rampspeed bg'))
    bias_slope = float(configs.get('Ramp speeds',
                                   'max rampspeed bias'))

    QDAC_SLOPES = dict(zip(used_channels(),
                           len(used_channels()) * [qdac_slope]))

#    QDAC_SLOPES[int(configs.get('Channel Parameters',
#                                'backgate channel'))] = bias_slope
    for ii in bias_channels():
        QDAC_SLOPES[ii] = bias_slope

    return QDAC_SLOPES


def check_unused_qdac_channels():
    """
    Check whether any UNASSIGNED QDac channel has a non-zero voltage
    """
    station = qc.Station.default

    qdac = station['qdac']

    qdac._get_status()
    for ch in [el for el in range(1, 48) if el not in used_channels()]:
        temp_v = qdac.channels[ch - 1].v.get_latest()
        if temp_v != 0.0:
            log.warning('Unused qDac channel not zero: channel '
                        '{:02}: {}'.format(ch, temp_v))


def reload_DMM_settings():
    """
    Function to reload DMMs.
    """

    # Get the two global objects containing the instruments and settings
    station = qc.Station.default
    configs = Config.default
    configs.reload()

    dmm_top = station['keysight_dmm_top']

    dmm_top.iv_conv = float(configs.get('Gain Settings', 'iv topo gain'))


def reload_SR830_settings():
    """
    Function to update the SR830 voltage divider values based on the conf. file
    """

    # Get the two global objects containing the instruments and settings
    configs = Config.default
    configs.reload()
    station = qc.Station.default

    # one could put in some validation here if wanted

    lockin = station['lockin_2']

    # Update the voltage dividers
    lockin.acfactor = float(configs.get('Gain Settings',
                                        'ac factor'))

    lockin.ivgain = float(configs.get('Gain Settings',
                                      'iv gain'))


def reload_QDAC_settings():
    """
    Function to update the qdac based on the configuration file
    """

    configs = Config.default
    configs.reload()
    station = qc.Station.default

    # Update the voltage dividers
    topo_dc = float(configs.get('Gain Settings',
                                'dc factor topo'))
    # sens_r_dc = float(configs.get('Gain Settings',
    #                               'dc factor right'))
    # sens_l_dc = float(configs.get('Gain Settings',
    #                               'dc factor left'))
    qdac = station['qdac']
    qdac.topo_bias.division_value = topo_dc
    # qdac.sens_r_bias.division_value = sens_r_dc
    # qdac.sens_l_bias.division_value = sens_l_dc

    # Set the range validators
    # NB: This is the voltage AT the QDac, BEFORE votlage dividers
    ranges = configs.get('Channel ranges')
    for chan in range(1, 49):
        try:
            chan_range = ranges[str(chan)]
        except KeyError:
            continue

        minmax = chan_range.split(" ")
        if len(minmax) != 2:
            raise ValueError("Expected: min max. Got {}".format(chan_range))
        else:
            rangemin = float(minmax[0])
            rangemax = float(minmax[1])

        vldtr = Numbers(rangemin, rangemax)
        qdac.channels[chan - 1].v.set_validator(vldtr)

    # Update the channels' labels
    labels = channel_labels()
    for chan, label in labels.items():
        qdac.channels[chan - 1].v.label = label


def reload_Decadac_settings():
    """
    Function to update the decadac based on the configuration file
    """
    configs = Config.default
    configs.reload()
    station = qc.Station.default

    deca = station['Decadac']

    # Update voltage and ramp safetly limits in software
    ranges = configs.get('Decadac Channel Limits')
    ramp_settings = configs.get('Decadac Channel Ramp Setttings')

    for chan in range(20):
        try:
            chan_range = ranges[str(chan)]
        except KeyError:
            continue
        range_minmax = chan_range.split(" ")
        if len(range_minmax) != 2:
            raise ValueError("Expected: min max. Got {}".format(chan_range))
        else:
            rangemin = float(range_minmax[0])
            rangemax = float(range_minmax[1])
        vldtr = Numbers(rangemin, rangemax)
        deca.channels[chan].volt.set_validator(vldtr)

        try:
            chan_ramp_settings = ramp_settings[str(chan)]
        except KeyError:
            continue
        ramp_stepdelay = chan_ramp_settings.split(" ")
        if len(ramp_stepdelay) != 2:
            raise ValueError(
                "Expected: step delay. Got {}".format(chan_ramp_settings))
        else:
            step = float(ramp_stepdelay[0])
            delay = float(ramp_stepdelay[1])
        deca.channels[chan].volt.set_step(step)
        deca.channels[chan].volt.set_delay(delay)

    # Update the channels' labels
    labels = configs.get('Decadac Channel Labels')
    for chan, label in labels.items():
        deca.channels[int(chan)].volt.label = label

    # Update variable names to channel number mapping
    lcut = configs.get('Channel Parameters', 'left cutter')
    deca.lcut = deca.channels[int(lcut)].volt

    rcut = configs.get('Channel Parameters', 'right cutter')
    deca.rcut = deca.channels[int(rcut)].volt

    jj = configs.get('Channel Parameters', 'central cutter')
    deca.jj = deca.channels[int(jj)].volt

    rplg = configs.get('Channel Parameters', 'right plunger')
    deca.rplg = deca.channels[int(rplg)].volt

    lplg = configs.get('Channel Parameters', 'left plunger')
    deca.lplg = deca.channels[int(lplg)].volt

    # Update voltage divider of source drain
    dcbias_i = int(configs.get('Channel Parameters',
                               'source channel'))
    dcbias = deca.channels[dcbias_i].volt
    deca.dcbias = VoltageDivider(dcbias,
                                 float(configs.get('Gain Settings',
                                                   'dc factor')))
    deca.dcbias.label = configs.get('Decadac Channel Labels', dcbias_i)

