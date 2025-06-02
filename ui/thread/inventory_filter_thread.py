from logging import getLogger

from PySide6.QtCore import QThread, Signal
from rfid.exception import ReaderException
from rfid.reader import Reader
from rfid.reader_settings import MaskInventoryPermission
from rfid.response import Status
from util_log import log_traceback


logger = getLogger()


class GetInventoryFilterThread(QThread):
    mask_inventory_permission_signal = Signal(type)

    def __init__(self, reader: Reader) -> None:
        super().__init__()
        self.reader = reader

    def run(self) -> None:
        try:
            response = self.reader.get_mask_inventory_permission()
            logger.info(f"GetInventoryFilterThread() > run() > response: {response}")
            self.mask_inventory_permission_signal.emit(response)
        except Exception as e:
            log_traceback(logger, e)
            self.mask_inventory_permission_signal.emit(e)


class SetInventoryFilterThread(QThread):
    result_set_mask_inventory_permission_signal = Signal(type)

    def __init__(self, reader: Reader) -> None:
        super().__init__()
        self.reader = reader
        self.__mask_inventory_permission: MaskInventoryPermission | None = None

    @property
    def mask_inventory_permission(self) -> None:
        raise ValueError("No getter for mask inventory permission")

    @mask_inventory_permission.setter
    def mask_inventory_permission(self, mask_inventory_permission: MaskInventoryPermission) -> None:
        self.__mask_inventory_permission = mask_inventory_permission

    def run(self) -> None:
        try:
            response = self.reader.set_mask_inventory_permission(self.__mask_inventory_permission)
            logger.info(f"SetInventoryFilterThread() > run() > response: {response}, "
                        f"mask_inventory_permission: {self.__mask_inventory_permission}")
            if response.status == Status.SUCCESS:
                self.result_set_mask_inventory_permission_signal.emit(self.__mask_inventory_permission)
            else:
                self.result_set_mask_inventory_permission_signal.emit(ReaderException(response.status.name))
        except Exception as e:
            log_traceback(logger, e)
            self.result_set_mask_inventory_permission_signal.emit(e)
