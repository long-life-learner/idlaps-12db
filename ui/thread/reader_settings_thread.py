from logging import getLogger

from PySide6.QtCore import QThread, Signal
from rfid.exception import ReaderException
from rfid.reader import Reader
from rfid.reader_settings import ReaderSettings
from rfid.response import Status
from util_log import log_traceback


logger = getLogger()


class GetReaderSettingsThread(QThread):
    reader_settings_signal = Signal(type)

    def __init__(self, reader: Reader) -> None:
        super().__init__()
        self.reader = reader

    def run(self) -> None:
        try:
            response = self.reader.get_reader_settings()
            logger.info(f"GetReaderSettingsThread() > run() > response: {response}")
            self.reader_settings_signal.emit(response)
        except Exception as e:
            log_traceback(logger, e)
            self.reader_settings_signal.emit(e)


class SetReaderSettingsThread(QThread):
    result_set_reader_settings_signal = Signal(type)

    def __init__(self, reader: Reader) -> None:
        super().__init__()
        self.reader = reader
        self.__reader_settings: ReaderSettings | None = None

    @property
    def reader_settings(self) -> None:
        raise ValueError("No getter for reader settings")

    @reader_settings.setter
    def reader_settings(self, reader_settings: ReaderSettings) -> None:
        self.__reader_settings = reader_settings

    def run(self) -> None:
        try:
            response = self.reader.set_reader_settings(self.__reader_settings)
            logger.info(f"SetReaderSettingsThread() > run() > response: {response}")
            if response.status == Status.SUCCESS:
                self.result_set_reader_settings_signal.emit(self.__reader_settings)
            else:
                self.result_set_reader_settings_signal.emit(ReaderException(response.status.name))
        except Exception as e:
            log_traceback(logger, e)
            self.result_set_reader_settings_signal.emit(e)


class ResetSettingsAndRebootThread(QThread):
    result_reset_settings_and_reboot_signal = Signal(type)

    def __init__(self, reader: Reader) -> None:
        super().__init__()
        self.reader = reader

    def run(self) -> None:
        try:
            response = self.reader.reset_factory()
            logger.info(f"ResetSettingsAndRebootThread() > run() > response: {response}")
            self.result_reset_settings_and_reboot_signal.emit(response)
        except Exception as e:
            log_traceback(logger, e)
            self.result_reset_settings_and_reboot_signal.emit(e)
