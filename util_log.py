import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import traceback


def setup_logging():
    is_exist = os.path.exists('logs')
    if not is_exist:
        os.makedirs('logs')

    log_file_path = f"logs/{os.getenv('FILENAME_LOG')}"
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter(
        '%(name)s: %(levelname)s %(threadName)s %(message)s'))

    rotating_handler = RotatingFileHandler(log_file_path,
                                           maxBytes=10 * 1024 * 1024,
                                           backupCount=3)
    rotating_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(name)s %(levelname)s %(threadName)s %(message)s'
    ))
    logging.basicConfig(level=logging.DEBUG, handlers=[console, rotating_handler])
    sys.excepthook = handle_exception


def log_traceback(logger, exception):
    tb_lines = [line.rstrip('\n') for line in
                traceback.format_exception(exception.__class__, exception, exception.__traceback__)]
    if not tb_lines:
        return

    logger.error("Traceback start >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    for tb_line in tb_lines:
        logger.error(tb_line)
    logger.error("Traceback end >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger = logging.getLogger()
    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
