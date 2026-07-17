"""
Configure the shared "virtualmouse" logger.

Writes a date-stamped file under logs/ (DEBUG) and mirrors INFO+ to the console.
Every module does `logging.getLogger("virtualmouse")`, so when a gesture misfires
you can open today's log and see exactly which gesture and action fired, in order.
"""

import logging
import os
import time

_ROOT = os.path.dirname(os.path.dirname(__file__))
LOG_DIR = os.path.join(_ROOT, "logs")

LOGGER_NAME = "virtualmouse"


def setup_logging() -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    logfile = os.path.join(LOG_DIR, f"{time.strftime('%Y-%m-%d')}.log")

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    if logger.handlers:  # already configured (e.g. calibrate then run)
        return logger

    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s")

    file_handler = logging.FileHandler(logfile, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console)
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)
