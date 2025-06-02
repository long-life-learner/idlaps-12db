from logging import getLogger

from PySide6.QtCore import QThread, Signal
from rfid.exception import ReaderException
from rfid.reader import Reader
from rfid.reader_settings import SelectParameters, QueryParameters
from rfid.response import Status
from util_log import log_traceback


logger = getLogger()


class GetCurrentTemperatureThread(QThread):
    temperature_signal = Signal(type)

    def __init__(self, reader: Reader) -> None:
        super().__init__()
        self.reader = reader

    def run(self) -> None:
        try:
            response = self.reader.get_current_temperature()
            logger.info(f"GetCurrentTemperatureThread() > run() > response: {response}")
            self.temperature_signal.emit(response)
        except Exception as e:
            log_traceback(logger, e)
            self.temperature_signal.emit(e)


class SetMaxTemperatureThread(QThread):
    result_set_max_temperature_signal = Signal(type)

    def __init__(self, reader: Reader) -> None:
        super().__init__()
        self.reader = reader
        self.__max_temperature: int | None = None

    @property
    def max_temperature(self) -> None:
        raise ValueError("No getter for max temperature")

    @max_temperature.setter
    def max_temperature(self, value: int) -> None:
        self.__max_temperature = value

    def run(self) -> None:
        try:
            response = self.reader.set_max_temperature(self.__max_temperature)
            logger.info(f"SetMaxTemperatureThread() > run() > response: {response}")
            if response.status == Status.SUCCESS:
                self.result_set_max_temperature_signal.emit(response)
            else:
                self.result_set_max_temperature_signal.emit(ReaderException(response.status.name))
        except Exception as e:
            log_traceback(logger, e)
            self.result_set_max_temperature_signal.emit(e)

