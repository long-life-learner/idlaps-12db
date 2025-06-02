from logging import getLogger

from PySide6.QtCore import QThread, Signal
from rfid.exception import ReaderException
from rfid.reader import Reader
from rfid.reader_settings import NetworkSettings
from rfid.response import Status
from util_log import log_traceback


logger = getLogger()


class GetNetworkSettingsThread(QThread):
    network_settings_signal = Signal(type)

    def __init__(self, reader: Reader) -> None:
        super().__init__()
        self.reader = reader

    def run(self) -> None:
        try:
            response = self.reader.get_network_settings()
            logger.info(f"GetNetworkSettingsThread() > run() > response: {response}")
            self.network_settings_signal.emit(response)
        except Exception as e:
            log_traceback(logger, e)
            self.network_settings_signal.emit(e)


class SetNetworkSettingsThread(QThread):
    result_set_network_settings_signal = Signal(type)

    def __init__(self, reader: Reader) -> None:
        super().__init__()
        self.reader = reader
        self.__network_settings: NetworkSettings | None = None

    @property
    def network_settings(self) -> None:
        raise ValueError("No getter for network settings")

    @network_settings.setter
    def network_settings(self, network_settings: NetworkSettings) -> None:
        self.__network_settings = network_settings

    def run(self) -> None:
        try:
            response = self.reader.set_network_settings(self.__network_settings)
            logger.info(f"SetNetworkSettingsThread() > run() > response: {response}")
            if response.status == Status.SUCCESS:
                self.result_set_network_settings_signal.emit(self.__network_settings)
            else:
                self.result_set_network_settings_signal.emit(ReaderException(response.status.name))
        except Exception as e:
            log_traceback(logger, e)
            self.result_set_network_settings_signal.emit(e)
