from IPython import get_ipython
import atexit
import os
from os.path import sep
import logging
import qcodes as qc
import sys
import warnings

from qdev_wrappers.device_annotator.qcodes_device_annotator import DeviceImage
from qdev_wrappers.configreader import Config
from qdev_wrappers.logger import (
    start_python_logger,
    start_command_history_logger)

log = logging.getLogger(__name__)
CURRENT_EXPERIMENT = {}
CURRENT_EXPERIMENT["logging_enabled"] = False
CURRENT_EXPERIMENT["init"] = False
pdfdisplay = {}

# aliases for keeping logging functions compatible
def _set_up_ipython_logging():
    warnings.warn("The function _set_up_ipython_logging is deprecated and " +
                  "will be removed in the " +
                  "future. For general logging simply import the wrappers " +
                  "logging module via:\n" +
                  ">>> from qdev_wrappers import logger\n" +
                  "as the first line of your script.\n" +
                  "For only command histroy logging call:\n"
                  "start_command_history_logger")
    start_command_history_logger()

def init_python_logger() -> None:
    warnings.warn("This function init_python_logger is deprecated and will " +
                  "be removed in the " +
                  "future. For general logging simply import the wrappers " +
                  "logging module via:\n" +
                  ">>> from qdev_wrappers import logger\n" +
                  "as the first line of your script.\n" +
                  "For only python logging call:\n"
                  "start_python_logger")
    start_python_logger()

def close_station(station):
    for comp in station.components:
        log.debug("Closing connection to {}".format(comp))
        try:
            qc.Instrument.find_instrument(comp).close()
        except KeyError:
            pass


def _set_up_exp_folder(sample_name: str, mainfolder: str= None, datafolder: str= "", plot_x_position=0.66):
    """
    Args:
        sample_name:  name of the sample (required)
        mainfolder:  base location for the data. (optional, otherwise pulled from qcodesrc.json)
    """
    if os.path.sep in sample_name:
        raise TypeError("Use relative names. That is without {}".format(sep))

    if os.path.sep in datafolder:
        raise TypeError("Use relative names. That is without {}".format(sep))

    if mainfolder is None:
        try:
            mainfolder = qc.config.user.mainfolder
        except KeyError:
            raise KeyError('mainfolder not set in qc.config, see '
                           '"https://github.com/QCoDeS/Qcodes/blob/master'
                           '/docs/examples/Configuring_QCoDeS.ipynb"')

    # always remove trailing sep in the main folder
    if mainfolder[-1] == sep:
        mainfolder = mainfolder[:-1]
    mainfolder = os.path.abspath(mainfolder)

    CURRENT_EXPERIMENT["mainfolder"] = mainfolder
    CURRENT_EXPERIMENT["sample_name"] = sample_name
    CURRENT_EXPERIMENT['init'] = True

    if datafolder != "":
        _set_up_subfolder(datafolder)

    path_to_experiment_folder = sep.join([mainfolder, sample_name, datafolder, ""])
    CURRENT_EXPERIMENT["exp_folder"] = path_to_experiment_folder
    
    # try:
    #     os.makedirs(path_to_experiment_folder)
    # except FileExistsError:
    #     pass

    loc_provider = qc.FormatLocation(
        fmt=path_to_experiment_folder + '{counter}')
    qc.data.data_set.DataSet.location_provider = loc_provider
    CURRENT_EXPERIMENT["provider"] = loc_provider

    CURRENT_EXPERIMENT['plot_x_position'] = plot_x_position
    log.info("experiment started at {}".format(path_to_experiment_folder))


def _set_up_station(station):
    CURRENT_EXPERIMENT['station'] = station
    log.info('station set up')


def _set_up_subfolder(subfolder_name: str):
    mainfolder = CURRENT_EXPERIMENT["mainfolder"]
    sample_name = CURRENT_EXPERIMENT["sample_name"]
    CURRENT_EXPERIMENT[subfolder_name + '_subfolder'] = subfolder_name
    try:
        os.makedirs(sep.join([mainfolder, sample_name, subfolder_name]))
    except FileExistsError:
        pass
    log.info("{} subfolder set up".format(subfolder_name))


def _init_device_image(station):
    di = DeviceImage(CURRENT_EXPERIMENT["exp_folder"], station)

    success = di.loadAnnotations()
    if not success:
        di.annotateImage()
    CURRENT_EXPERIMENT['device_image'] = di
    log.info('device image initialised')

def _set_up_pdf_preferences(subfolder_name: str = 'pdf', display_pdf=True,
                            display_individual_pdf=False):
    if display_pdf or display_individual_pdf:
        _set_up_subfolder(subfolder_name)
        pdfdisplay['individual'] = display_individual_pdf
        pdfdisplay['combined'] = display_pdf

def _set_up_config_file(cfg_name: str):
    local_cfg_file = sep.join([
        CURRENT_EXPERIMENT["mainfolder"],
        CURRENT_EXPERIMENT["sample_name"],
        CURRENT_EXPERIMENT['local_scripts_subfolder'],
        "{}.config".format(cfg_name)])
    if os.path.isfile(local_cfg_file):
        CURRENT_EXPERIMENT["{}_config".format(cfg_name)] = 'local'
        log.info('set up config file at {}'.format(local_cfg_file))
    else:
        log.warning('no config file found at {}, will try general'
                    ''.format(local_cfg_file))
        try:
            script_folder = CURRENT_EXPERIMENT["scriptfolder"]
        except KeyError:
            raise KeyError('scriptfolder not found in CURRENT_EXPERIMENT, '
                           'check that init function calls '
                           '_set_up_script_folder before _set_up_config_file')
        general_cfg_file = sep.join([script_folder,
                                     "{}.config".format(cfg_name)])
        if os.path.isfile(general_cfg_file):
            CURRENT_EXPERIMENT["{}_config".format(cfg_name)] = 'general'
            log.info('set up config file at {}'.format(general_cfg_file))
        else:
            log.error('no config file found at {}'
                        ''.format(general_cfg_file))

def _set_up_script_folder(scriptfolder: str=None):
    """
    Add the scriptfolder to the sys.path. This should be dropped ASAP
    Args:
        scriptfolder: Absolute path to a folder containing scripts.
    """

    if scriptfolder is None:
        try:
            scriptfolder = qc.config.user.scriptfolder
        except KeyError:
            raise KeyError('scriptfolder not set in qc.config, see '
                           '"https://github.com/QCoDeS/Qcodes/blob/master'
                           '/docs/examples/Configuring_QCoDeS.ipynb"')

    # always remove trailing sep in the main folder
    if scriptfolder[-1] == sep:
        scriptfolder = scriptfolder[:-1]
    scriptfolder = os.path.abspath(scriptfolder)

    if not os.path.isdir(scriptfolder):
        raise RuntimeError('{} is not a folder, make folder or update '
                           'config settings at qc.config.user.scriptfolder'
                           '"https://github.com/QCoDeS/Qcodes/blob/master'
                           '/docs/examples/Configuring_QCoDeS.ipynb"'
                           ''.format(scriptfolder))
    CURRENT_EXPERIMENT["scriptfolder"] = scriptfolder
    if scriptfolder not in sys.path:
        sys.path.insert(0, scriptfolder)
    log.info("general scripts folder set up at {}".format(scriptfolder))

########################################################################
# Actual init functions
########################################################################


def basic_init(sample_name: str, station, mainfolder: str= None, datafolder: str= ""):
    _set_up_exp_folder(sample_name, mainfolder, datafolder)
    _set_up_station(station)


def all_init(sample_name: str, station, mainfolder: str= None, datafolder: str= "",
              display_png=True, display_pdf=True, display_individual_pdf=False,
              annotate_image=False, subfolders=[]):
    """Advanced experiment initialization.
    
    This function allows you to configure the initialization of an experiments.
    Args:
        sample_name (str): Will also become the subfolder name under mainfolder and becomes the
            root of the experiment
        station (:obj:'qc.Station'): reference to the qc.Station to be used. Can be asked from 
            the StationConfigurator.
        mainfolder (str, optional): absolution path to the mainfolder hosting the experiments. Defaults to 
            the qcodesrc.json directive.
        datafolder (str, optional): relative location (cannot be a path) of the data. Defaults to the 
            experiment root folder.
        display_png (boolean, optional): Whether to create png graphs in the png subfolder.
        display_pdf (boolean, optional): Whether to create pdf graphs in the pdf subfolder.
        annotate_image (booloan, optional): Whether to create device annotation images.
        subfolders (:obj:`list` of :obj:`str` , optional): List of additional subfolders to add. Default to [].
     """
    basic_init(sample_name, station, mainfolder, datafolder)

    if display_png:
        _set_up_subfolder('png')
        # CURRENT_EXPERIMENT['png_subfolder'] = 'png'

    _set_up_pdf_preferences(display_pdf=display_pdf,
                            display_individual_pdf=display_individual_pdf)

    for sf_name in subfolders:
        _set_up_subfolder(sf_name)

    if annotate_image:
        _init_device_image(station)

    CURRENT_EXPERIMENT


def my_init(sample_name: str, station, qubit_count=None,
            pdf_folder=True, png_folder=True, analysis_folder=True,
            calib_config=False, instr_config=True,
            waveforms_folder=True,
            local_scripts_folder=True,
            mainfolder: str= None,
            annotate_image=False,
            display_pdf=True,
            display_individual_pdf=False,
            plot_x_position=0.66):
    basic_init(sample_name, station, mainfolder)
    CURRENT_EXPERIMENT['plot_x_position'] = plot_x_position
    _set_up_script_folder()
    if pdf_folder:
        _set_up_pdf_preferences(display_pdf=display_pdf,
                                display_individual_pdf=display_individual_pdf)
    if png_folder:
        _set_up_subfolder('png')
        CURRENT_EXPERIMENT['png_subfolder'] = 'png'
    if analysis_folder:
        _set_up_subfolder('analysis')
    if waveforms_folder:
        _set_up_subfolder('waveforms')
    if any([local_scripts_folder, instr_config, calib_config]):
        _set_up_subfolder('local_scripts')
        f = '{}{}'.format(CURRENT_EXPERIMENT['exp_folder'],
                          CURRENT_EXPERIMENT['local_scripts_subfolder'])
        if f not in sys.path:
            sys.path.insert(0, f)
    if instr_config:
        _set_up_config_file('instr')
    if calib_config:
        _set_up_config_file('calib')
    if annotate_image:
        _init_device_image(station)
    if qubit_count is not None:
        CURRENT_EXPERIMENT['qubit_count'] = qubit_count
