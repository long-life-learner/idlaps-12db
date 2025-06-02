from logging import getLogger
from time import sleep
from PySide6.QtCore import QThread, Signal
from rfid.reader import Reader
from rfid.reader_settings import AnswerModeInventoryParameter, WorkMode
from rfid.response import InventoryStatus

logger = getLogger()


class InventoryThread(QThread):
    result_tag_signal = Signal(type)
    result_finished_signal = Signal(bool)

    def __init__(self, reader: Reader) -> None:
        super().__init__()
        self.reader = reader
        self.__work_mode: WorkMode | None = None
        self.__answer_mode_inventory_parameter: AnswerModeInventoryParameter | None = None
        self.request_start = False
        self.request_stop = False

    @property
    def work_mode(self) -> None:
        raise ValueError("No getter for work mode")

    @work_mode.setter
    def work_mode(self, value: WorkMode) -> None:
        logger.info(f"InventoryThread() > work_mode() > value: {value}")
        self.__work_mode = value

    @property
    def answer_mode_inventory_parameter(self) -> None:
        raise ValueError("No getter for answer mode inventory parameters")

    @answer_mode_inventory_parameter.setter
    def answer_mode_inventory_parameter(self, value: AnswerModeInventoryParameter) -> None:
        logger.info(f"InventoryThread() > work_mode() > value: {value}")
        self.__answer_mode_inventory_parameter = value

    def run(self) -> None:
        while True:
            # Handle stop
            if self.request_stop and self.request_start:
                self.request_stop = False
                self.request_start = False
                self.reader.stop_inventory(work_mode=self.__work_mode)

            # Handle start
            if self.request_start:
                response = self.reader.start_inventory(work_mode=self.__work_mode,
                                                       answer_mode_inventory_parameter=
                                                       self.__answer_mode_inventory_parameter if
                                                       self.__work_mode == WorkMode.ANSWER_MODE else None)
                for res in response:
                    logger.info(f"InventoryThread() > run() > res: {res}")

                    # Handle stop - when inventory
                    if self.request_stop:
                        self.request_stop = False
                        self.reader.stop_inventory(work_mode=self.__work_mode)
                        break

                    if res is None:
                        continue

                    if res.status == InventoryStatus.SUCCESS and res.tag:
                        self.result_tag_signal.emit(res.tag)

                    if res.status == InventoryStatus.NO_COUNT_LABEL and self.__work_mode == WorkMode.ANSWER_MODE:
                        break

                self.request_start = False
                self.request_stop = False

            if self.request_stop and not self.request_start:
                self.request_stop = False

            self.result_finished_signal.emit(True)

            sleep(0.1)
