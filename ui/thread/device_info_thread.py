from logging import getLogger
from PySide6.QtCore import QThread, Signal
from rfid.reader import Reader
from util_log import log_traceback

logger = getLogger()


class GetDeviceInfoThread(QThread):
    device_info_signal = Signal(type)

    def __init__(self, reader: Reader) -> None:
        super().__init__()
        self.reader = reader

    def run(self) -> None:
        try:
            response = self.reader.get_device_info()
            logger.info(f"GetDeviceInfoThread() > run() > response: {response}")
            self.device_info_signal.emit(response)
        except Exception as e:
            log_traceback(logger, e)
            self.device_info_signal.emit(e)
