from logging import getLogger

from PySide6.QtCore import QThread, Signal
from rfid.exception import ReaderException
from rfid.reader import Reader
from rfid.response import Status
from rfid.transport import Transport, SerialTransport, UsbTransport
from rfid.utils import get_all_networks
from util_log import log_traceback

logger = getLogger()


class RefreshSerialPortThread(QThread):
    ports_signal = Signal(list)

    def run(self) -> None:
        ports = SerialTransport.scan()
        logger.info(f"RefreshSerialPortThread() > run() > ports: {ports}")
        self.ports_signal.emit(ports)


class RefreshUsbDeviceAddressesThread(QThread):
    device_addresses_signal = Signal(list)

    def run(self) -> None:
        ports = UsbTransport.scan()
        logger.info(f"RefreshUsbDeviceAddressesThread() > run() > ports: {ports}")
        self.device_addresses_signal.emit(ports)


class ConnectThread(QThread):
    reader_connected_signal = Signal(type)

    def __init__(self, transport: Transport) -> None:
        super().__init__()
        self.transport = transport

    def run(self) -> None:
        reader = Reader(self.transport)
        try:
            self.transport.connect()
            response = reader.init()
            logger.info(f"ConnectThread() > run() > response: {response}")

            if response is None:
                self.reader_connected_signal.emit(ReaderException("Failed connect to reader."))
                reader.close()
                return

            if response.status == Status.SUCCESS:
                self.reader_connected_signal.emit(reader)
            else:
                self.reader_connected_signal.emit(ReaderException(response.status.name))
        except Exception as e:
            logger.info(f"ConnectThread() > run() > error when connect with: {self.transport}")

            # Get all IP Addresses
            networks: list[dict] = get_all_networks()
            for network in networks:
                logger.info(f"ConnectThread() > run() > Interface: {network['interface']} > "
                            f"IP Address: {network['address']} > Netmask: {network['netmask']}")

            log_traceback(logger, e)
            reader.close()
            self.reader_connected_signal.emit(e)

