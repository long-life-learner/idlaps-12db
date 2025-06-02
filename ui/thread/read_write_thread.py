from logging import getLogger
from PySide6.QtCore import QThread, Signal
from rfid.reader import Reader
from rfid.reader_settings import MemoryBank, LockMemoryBank, LockAction
from rfid.status import Status
from util_log import log_traceback

logger = getLogger()


class SetFilterThread(QThread):
    result_set_signal = Signal(type)

    def __init__(self, reader: Reader) -> None:
        super().__init__()
        self.reader = reader
        self.__mask: bytes | None = None

    @property
    def mask(self) -> None:
        raise ValueError("No getter for mask")

    @mask.setter
    def mask(self, value: bytes) -> None:
        self.__mask = value

    def run(self) -> None:
        try:
            response = self.reader.select_mask(self.__mask)
            logger.info(f"SetFilterThread() > run() > response: {response}")
            self.result_set_signal.emit(response)
        except Exception as e:
            log_traceback(logger, e)
            self.result_set_signal.emit(e)


class ReadThread(QThread):
    result_read_signal = Signal(type)
    result_read_finished_signal = Signal(list)

    def __init__(self, reader: Reader) -> None:
        super().__init__()
        self.reader = reader
        self.__memory_bank: MemoryBank | None = None
        self.__start_address: int | None = None
        self.__length: int | None = None
        self.__access_password: bytes | None = None
        self.request_stop: bool = False

    @property
    def memory_bank(self) -> None:
        raise ValueError("No getter for memory bank")

    @memory_bank.setter
    def memory_bank(self, value: bytes) -> None:
        self.__memory_bank = value

    @property
    def start_address(self) -> None:
        raise ValueError("No getter for start address")

    @start_address.setter
    def start_address(self, value: bytes) -> None:
        self.__start_address = value

    @property
    def length(self) -> None:
        raise ValueError("No getter for length")

    @length.setter
    def length(self, value: bytes) -> None:
        self.__length = value

    @property
    def access_password(self) -> None:
        raise ValueError("No getter for access password")

    @access_password.setter
    def access_password(self, value: bytes) -> None:
        self.__access_password = value

    def run(self) -> None:
        responses = []

        try:

            response = self.reader.read_memory(
                memory_bank=self.__memory_bank,
                start_address=self.__start_address,
                length=self.__length,
                access_password=self.__access_password,
            )

            for res in response:
                logger.info(f"ReadThread() > run() > res: {res}")
                if res is None:
                    break

                if self.request_stop:  # Request stop Read memory
                    self.reader.stop_inventory()
                    break

                self.result_read_signal.emit(res)
                if res.status == Status.NO_COUNT_LABEL:
                    break
                responses.append(res)

            self.result_read_finished_signal.emit(responses)
        except Exception as e:
            log_traceback(logger, e)
            self.result_read_signal.emit(e)


class WriteThread(QThread):
    result_write_signal = Signal(type)
    result_write_finished_signal = Signal(list)

    def __init__(self, reader: Reader) -> None:
        super().__init__()
        self.reader = reader
        self.__memory_bank: MemoryBank | None = None
        self.__data: bytes | None = None
        self.__start_address: int | None = None
        self.__length: int | None = None
        self.__access_password: bytes | None = None
        self.request_stop: bool = False

    @property
    def memory_bank(self) -> None:
        raise ValueError("No getter for memory bank")

    @memory_bank.setter
    def memory_bank(self, value: bytes) -> None:
        self.__memory_bank = value

    @property
    def data(self) -> None:
        raise ValueError("No getter for data")

    @data.setter
    def data(self, value: bytes) -> None:
        self.__data = value

    @property
    def start_address(self) -> None:
        raise ValueError("No getter for start address")

    @start_address.setter
    def start_address(self, value: bytes) -> None:
        self.__start_address = value

    @property
    def length(self) -> None:
        raise ValueError("No getter for length")

    @length.setter
    def length(self, value: bytes) -> None:
        self.__length = value

    @property
    def access_password(self) -> None:
        raise ValueError("No getter for access password")

    @access_password.setter
    def access_password(self, value: bytes) -> None:
        self.__access_password = value

    def run(self) -> None:
        responses = []

        try:
            response = self.reader.write_memory(
                memory_bank=self.__memory_bank,
                data=self.__data,
                start_address=self.__start_address,
                length=self.__length,
                access_password=self.__access_password,
            )

            for res in response:
                logger.info(f"WriteThread() > run() > res: {res}")
                if res is None:
                    break

                if self.request_stop:  # Request stop Write memory
                    self.reader.stop_inventory()
                    break

                self.result_write_signal.emit(res)
                if res.status == Status.NO_COUNT_LABEL:
                    break
                responses.append(res)

            self.result_write_finished_signal.emit(responses)
        except Exception as e:
            log_traceback(logger, e)
            self.result_write_signal.emit(e)


class LockThread(QThread):
    result_lock_signal = Signal(type)
    result_lock_finished_signal = Signal(list)

    def __init__(self, reader: Reader) -> None:
        super().__init__()
        self.reader = reader
        self.__lock_memory_bank: LockMemoryBank | None = None
        self.__lock_action: LockAction | None = None
        self.__access_password: bytes | None = None
        self.request_stop: bool = False

    @property
    def lock_memory_bank(self) -> None:
        raise ValueError("No getter for lock memory bank")

    @lock_memory_bank.setter
    def lock_memory_bank(self, value: bytes) -> None:
        self.__lock_memory_bank = value

    @property
    def lock_action(self) -> None:
        raise ValueError("No getter for lock action")

    @lock_action.setter
    def lock_action(self, value: bytes) -> None:
        self.__lock_action = value

    @property
    def access_password(self) -> None:
        raise ValueError("No getter for access password")

    @access_password.setter
    def access_password(self, value: bytes) -> None:
        self.__access_password = value

    def run(self) -> None:
        responses = []

        try:
            response = self.reader.lock_memory(
                lock_memory_bank=self.__lock_memory_bank,
                lock_action=self.__lock_action,
                access_password=self.__access_password,
            )

            for res in response:
                logger.info(f"LockThread() > run() > res: {res}")
                if res is None:
                    break

                if self.request_stop:  # Request stop Lock memory
                    self.reader.stop_inventory()
                    break

                self.result_lock_signal.emit(res)
                if res.status == Status.NO_COUNT_LABEL:
                    break
                responses.append(res)

            self.result_lock_finished_signal.emit(responses)
        except Exception as e:
            log_traceback(logger, e)
            self.result_lock_signal.emit(e)


class KillThread(QThread):
    result_kill_signal = Signal(type)
    result_kill_finished_signal = Signal(list)

    def __init__(self, reader: Reader) -> None:
        super().__init__()
        self.reader = reader
        self.__kill_password: bytes | None = None
        self.request_stop: bool = False

    @property
    def kill_password(self) -> None:
        raise ValueError("No getter for kill password")

    @kill_password.setter
    def kill_password(self, value: bytes) -> None:
        self.__kill_password = value

    def run(self) -> None:
        responses = []

        try:
            response = self.reader.kill_tag(kill_password=self.__kill_password)

            for res in response:
                logger.info(f"KillThread() > run() > res: {res}")
                if res is None:
                    break

                if self.request_stop:  # Request stop Kill memory
                    self.reader.stop_inventory()
                    break

                self.result_kill_signal.emit(res)
                if res.status == Status.NO_COUNT_LABEL:
                    break
                responses.append(res)

            self.result_kill_finished_signal.emit(responses)
        except Exception as e:
            log_traceback(logger, e)
            self.result_kill_signal.emit(e)
