from array import array
import glob
import sys
from enum import Enum
from logging import getLogger
from abc import ABC, abstractmethod
from dataclasses import dataclass
from sys import platform
from socket import socket, AF_INET, SOCK_STREAM
from typing import TypeVar
import serial
import usb
from usb.core import Device, Endpoint
from rfid.reader_settings import BaudRate
from rfid.utils import hex_readable

logger = getLogger()
T = TypeVar('T', bound='Parent')


class ConnectionType(Enum):
    SERIAL = 0
    USB = 1
    TCP_IP = 2

    def __str__(self) -> str:
        return ConnectionType.DISPLAY_STRINGS[self.value]

    @classmethod
    def from_str(cls, value: str) -> T:
        for connection_type in ConnectionType:
            if str(connection_type) == value:
                return connection_type


ConnectionType.DISPLAY_STRINGS = [
    "Serial",
    "USB",
    "TCP/IP"
]


class Transport(ABC):
    def __init__(self, connection_type: ConnectionType) -> None:
        self.connection_type = connection_type

    @abstractmethod
    def connect(self, **kwargs) -> None:
        raise NotImplementedError

    @abstractmethod
    def reconnect(self, **kwargs) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def read_bytes(self, **kwargs) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def write_bytes(self, buffer: bytes) -> None:
        raise NotImplementedError

    @abstractmethod
    def clear_buffer(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError


class TcpTransport(Transport):
    def __init__(self, ip_address: str, port: int, timeout: int = 6) -> None:
        super().__init__(ConnectionType.TCP_IP)
        self.ip_address: str = ip_address
        self.port: int = port
        self.timeout: int = timeout
        self.socket: socket | None = None

    def __str__(self) -> str:
        return f'TcpTransport(ip_address: {self.ip_address}, port: {self.port}, timeout: {self.timeout})'

    def connect(self) -> None:
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.settimeout(self.timeout)
        self.socket.connect((self.ip_address, self.port))

    def reconnect(self, ip_address: str | None = None, port: int | None = None,
                  timeout: int | None = None) -> None:
        self.socket.close()
        self.ip_address = ip_address if ip_address else self.ip_address
        self.timeout = timeout if timeout else self.timeout
        self.connect()

    def read_bytes(self, length: int) -> bytes:
        return self.socket.recv(length)

    def write_bytes(self, buffer: bytes) -> None:
        self.socket.sendall(buffer)

    def clear_buffer(self) -> None:
        # self.socket.recv(1024)
        pass

    def close(self) -> None:
        self.socket.close()


@dataclass
class DeviceAddress:
    bus: int
    address: int

    def __str__(self) -> str:
        return f"Bus: {self.bus}, Address: {self.address}"


class UsbTransport(Transport):
    @classmethod
    def scan(cls) -> list[DeviceAddress]:
        dev_list = []
        for dev in usb.core.find(idVendor=0x0483, idProduct=0x5750, find_all=True):
            dev_list.append(DeviceAddress(dev.bus, dev.address))
        return dev_list

    def __init__(self, device_address: DeviceAddress) -> None:
        super().__init__(ConnectionType.USB)
        self.device_address: DeviceAddress = device_address
        self.dev: Device | None = None
        self.ep_out: Endpoint | None = None
        self.ep_in: Endpoint | None = None
        self.max_packet_size: int | None = None
        self.endpoint_address: DeviceAddress | None = None
        self.connect()

    def __str__(self) -> str:
        return f'UsbTransport(device_address: {self.device_address}, ' \
               f'max_packet_size: {self.max_packet_size}, endpoint_address: {self.endpoint_address})'

    def connect(self):
        self.dev = usb.core.find(bus=self.device_address.bus, address=self.device_address.address)

        if platform == "linux" or platform == "linux2" or platform == "darwin":  # Linux or Mac OS
            if self.dev.is_kernel_driver_active(0):
                self.dev.detach_kernel_driver(0)
                self.dev.reset()

        self.dev.set_configuration()

        configuration = self.dev.get_active_configuration()
        interface = configuration[(0, 0)]

        self.ep_out: Endpoint = usb.util.find_descriptor(
            interface,
            custom_match=lambda e:
            usb.util.endpoint_direction(e.bEndpointAddress)
            == usb.util.ENDPOINT_OUT)
        assert self.ep_out

        self.ep_in: Endpoint = usb.util.find_descriptor(
            interface,
            custom_match=lambda e:
            usb.util.endpoint_direction(e.bEndpointAddress)
            == usb.util.ENDPOINT_IN)
        assert self.ep_in

        self.max_packet_size = self.ep_in.wMaxPacketSize
        self.endpoint_address = self.ep_in.bEndpointAddress

    def reconnect(self, device_address: DeviceAddress | None = None) -> None:
        self.close()

        # After close, USB change the address from 1 to 2, vice versa.
        # Then try to scan again
        if device_address is None:
            device_addresses = UsbTransport.scan()
            if len(device_addresses) > 0:
                device_address = device_addresses[0]

        self.device_address = device_address if device_address else self.device_address
        self.connect()

    def write_bytes(self, data: bytes) -> None:
        assert self.ep_out.write(data) == len(data)

    def read_bytes(self) -> bytes:
        data = self.ep_in.read(self.max_packet_size)
        if isinstance(data, array):  # array from USB
            data = data.tobytes()
        return data

    def clear_buffer(self) -> None:
        pass

    def close(self) -> None:
        usb.util.dispose_resources(self.dev)
        if platform == "linux" or platform == "linux2" or platform == "darwin":
            self.dev.attach_kernel_driver(0)


class SerialTransport(Transport):
    def __init__(self, serial_port: str, baud_rate: BaudRate, timeout: int = 0.5) -> None:
        super().__init__(ConnectionType.SERIAL)
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.serial = serial.Serial(self.serial_port, self.baud_rate.to_int,
                                    timeout=timeout, write_timeout=timeout * 2)

    def __str__(self) -> str:
        return f'SerialTransport(port: {self.serial_port}, baud_rate: {self.baud_rate})'

    @classmethod
    def scan(cls, timeout: int = 1) -> list[str]:
        result: list[str] = []
        if sys.platform.startswith("win"):  # Windows
            ports = ["COM%s" % (i + 1) for i in range(15)]
        elif sys.platform.startswith("linux") or sys.platform.startswith("cygwin"):  # Linux
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob("/dev/tty[A-Za-z]*")
        elif sys.platform.startswith("darwin"):  # Mac OS
            ports = glob.glob("/dev/tty.*")
        else:
            raise EnvironmentError("Unsupported platform")
        for port in ports:
            try:
                s = serial.Serial(port, timeout=timeout)
                s.close()
                result.append(port)
            except serial.SerialException as _:
                pass
        return result

    def connect(self, **kwargs):
        pass

    def reconnect(self, serial_port: str | None = None, baud_rate: BaudRate | None = None,
                  timeout: int | None = None) -> None:
        self.close()
        self.serial_port = serial_port if serial_port else self.serial.port
        self.baud_rate = baud_rate if baud_rate else BaudRate.from_int(self.serial.baudrate)
        self.timeout = timeout if timeout else self.serial.timeout
        self.serial = serial.Serial(self.serial_port, self.baud_rate.to_int,
                                    timeout=self.timeout, write_timeout=self.timeout * 2)

    def read_bytes(self, length: int) -> bytes:
        response = self.serial.read(length)
        print(f'>> RESPONSE TRANSPORT: {hex_readable(response)}')
        return response

    def write_bytes(self, buffer: bytes) -> None:
        print(f'<< REQUEST TRANSPORT : {hex_readable(buffer)}')
        self.serial.write(buffer)

    def clear_buffer(self) -> None:
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()

    def close(self) -> None:
        self.serial.close()
