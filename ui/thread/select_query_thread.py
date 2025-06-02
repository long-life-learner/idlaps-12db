from logging import getLogger

from PySide6.QtCore import QThread, Signal
from rfid.exception import ReaderException
from rfid.reader import Reader
from rfid.reader_settings import SelectParameters, QueryParameters
from rfid.response import Status
from util_log import log_traceback


logger = getLogger()


class GetSelectParametersThread(QThread):
    select_parameters_signal = Signal(type)

    def __init__(self, reader: Reader) -> None:
        super().__init__()
        self.reader = reader

    def run(self) -> None:
        try:
            response = self.reader.get_select_parameters()
            logger.info(f"GetSelectParametersThread() > run() > response: {response}")
            self.select_parameters_signal.emit(response)
        except Exception as e:
            log_traceback(logger, e)
            self.select_parameters_signal.emit(e)


class SetSelectParametersThread(QThread):
    result_set_select_parameters_signal = Signal(type)

    def __init__(self, reader: Reader) -> None:
        super().__init__()
        self.reader = reader
        self.__select_parameters: SelectParameters | None = None

    @property
    def select_parameters(self) -> None:
        raise ValueError("No getter for select parameters")

    @select_parameters.setter
    def select_parameters(self, select_parameters: SelectParameters) -> None:
        self.__select_parameters = select_parameters

    def run(self) -> None:
        try:
            response = self.reader.set_select_parameters(self.__select_parameters)
            logger.info(f"SetSelectParametersThread() > run() > response: {response}")
            if response.status == Status.SUCCESS:
                self.result_set_select_parameters_signal.emit(response)
            else:
                self.result_set_select_parameters_signal.emit(ReaderException(response.status.name))
        except Exception as e:
            log_traceback(logger, e)
            self.result_set_select_parameters_signal.emit(e)


class GetQueryParametersThread(QThread):
    query_parameters_signal = Signal(type)

    def __init__(self, reader: Reader) -> None:
        super().__init__()
        self.reader = reader

    def run(self) -> None:
        try:
            response = self.reader.get_query_parameters()
            logger.info(f"GetQueryParametersThread() > run() > response: {response}")
            self.query_parameters_signal.emit(response)
        except Exception as e:
            log_traceback(logger, e)
            self.query_parameters_signal.emit(e)


class SetQueryParametersThread(QThread):
    result_set_query_parameters_signal = Signal(type)

    def __init__(self, reader: Reader) -> None:
        super().__init__()
        self.reader = reader
        self.__query_parameters: QueryParameters | None = None

    @property
    def query_parameters(self) -> None:
        raise ValueError("No getter for query parameters")

    @query_parameters.setter
    def query_parameters(self, query_parameters: QueryParameters) -> None:
        self.__query_parameters = query_parameters

    def run(self) -> None:
        try:
            response = self.reader.set_query_parameters(self.__query_parameters)
            logger.info(f"SetQueryParametersThread() > run() > response: {response}")
            if response.status == Status.SUCCESS:
                self.result_set_query_parameters_signal.emit(response)
            else:
                self.result_set_query_parameters_signal.emit(ReaderException(response.status.name))
        except Exception as e:
            log_traceback(logger, e)
            self.result_set_query_parameters_signal.emit(e)

