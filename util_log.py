import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import traceback
from ui.utils import get_app_data_dir


def setup_logging():
    app_data_dir = get_app_data_dir()
    log_dir = os.path.join(app_data_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    log_file_path = os.path.join(log_dir, os.getenv('FILENAME_LOG', 'app.log'))
    console = logging.StreamHandler()
    # console.setLevel(logging.NOTSET)
    console.setLevel(logging.WARNING)  # hanya WARNING ke atas yg muncul di console
    
    console.setFormatter(logging.Formatter(
        '%(name)s: %(levelname)s %(threadName)s %(message)s'))

    rotating_handler = RotatingFileHandler(log_file_path,
                                           maxBytes=10 * 1024 * 1024,
                                           backupCount=3)
    rotating_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(name)s %(levelname)s %(threadName)s %(message)s'
    ))
    logging.basicConfig(level=logging.DEBUG, handlers=[console])
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
