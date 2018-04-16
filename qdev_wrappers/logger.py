import logging
import logging.handlers

import os
from IPython import get_ipython
from qcodes import config

log = logging.getLogger(__name__)

logging_dir = "logs"
history_log_name = "history.log"
python_log_name = 'pythonlog.log'


def start_python_logger() -> None:
    """
    Logging of messages passed throug the python logging module
    This sets up logging to a time based logging.
    This means that all logging messages on or above
    filelogginglevel will be written to pythonlog.log
    All logging messages on or above consolelogginglevel
    will be written to stderr.
    """
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    try:
        filelogginglevel = config.core.file_loglevel
    except KeyError:
        filelogginglevel = "Info"
    consolelogginglevel = config.core.loglevel
    ch = logging.StreamHandler()
    ch.setLevel(consolelogginglevel)
    ch.setFormatter(formatter)
    filename = os.path.join(config.user.mainfolder,
                            logging_dir,
                            python_log_name)
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    fh1 = logging.handlers.TimedRotatingFileHandler(filename,
                                                    when='midnight')
    fh1.setLevel(filelogginglevel)
    fh1.setFormatter(formatter)
    logging.basicConfig(handlers=[ch, fh1], level=logging.DEBUG)
    # capture any warnings from the warnings module
    logging.captureWarnings(capture=True)
    log.info("QCoDes python logger setup")


def start_command_history_logger():
    """
    logging of the history of the interactive command shell
    works only with ipython
    """
    ipython = get_ipython()
    if ipython is None:
        raise RuntimeError("History can't be saved. "
                           "-Refusing to proceed (use IPython/jupyter)")
    ipython.magic("%logstop")
    filename = os.path.join(config.user.mainfolder,
                            logging_dir,
                            python_log_name)
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    ipython.magic("%logstart -t -o {} {}".format(filename, "append"))
    log.info("Started logging IPython history")


def start_logging():
    start_python_logger()
    start_command_history_logger()
