from logging import getLogger

from PySide6.QtCore import QThread, Signal

from rfid.reader import Reader
from rfid.reader_settings import OutputControl
from util_log import log_traceback

logger = getLogger()


class SetManualRelayThread(QThread):
    result_set_manual_relay_signal = Signal(type)

    def __init__(self, reader: Reader) -> None:
        super().__init__()
        self.reader = reader
        self.__release: bool | None = None
        self.__valid_time: int | None = None

    @property
    def release(self) -> None:
        raise ValueError("No getter for release")

    @release.setter
    def release(self, release: bool) -> None:
        self.__release = release

    @property
    def valid_time(self) -> None:
        raise ValueError("No getter for valid_time")

    @valid_time.setter
    def valid_time(self, valid_time: bool) -> None:
        self.__valid_time = valid_time

    def run(self) -> None:
        try:
            response = self.reader.set_relay(self.__release, self.__valid_time)
            logger.info(f"SetManualRelayThread() > run() > response: {response}")
            self.result_set_manual_relay_signal.emit(response)
        except Exception as e:
            log_traceback(logger, e)
            self.result_set_manual_relay_signal.emit(e)


class GetOutputControlThread(QThread):
    result_get_output_control_signal = Signal(type)

    def __init__(self, reader: Reader) -> None:
        super().__init__()
        self.reader = reader

    def run(self) -> None:
        try:
            response = self.reader.get_output_control()
            logger.info(f"GetOutputControlThread() > run() > response: {response}")
            self.result_get_output_control_signal.emit(response)
        except Exception as e:
            log_traceback(logger, e)
            self.result_get_output_control_signal.emit(e)


class SetAutoRelayThread(QThread):
    result_set_auto_relay_signal = Signal(type)

    def __init__(self, reader: Reader) -> None:
        super().__init__()
        self.reader = reader
        self.__output_control: OutputControl | None = None

    @property
    def output_control(self) -> None:
        raise ValueError("No getter for output_control")

    @output_control.setter
    def output_control(self, output_control: OutputControl) -> None:
        self.__output_control = output_control

    def run(self) -> None:
        try:
            response = self.reader.set_output_control(self.__output_control)
            logger.info(f"SetAutoRelayThread() > run() > response: {response}")
            self.result_set_auto_relay_signal.emit(response)
        except Exception as e:
            log_traceback(logger, e)
            self.result_set_auto_relay_signal.emit(e)

