import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from logging import getLogger
from socket import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_BROADCAST, SOCK_STREAM, IPPROTO_UDP

from PySide6.QtCore import QThread, Signal

from rfid.command import Command, CommandRequest, CommandOption
from rfid.response import ResponseNetworkSettings
from rfid.utils import hex_readable, generate_ip_range
from util_log import log_traceback

logger = getLogger()


class SearchIpThread(QThread):
    progress_signal = Signal(int)
    network_settings_signal = Signal(type)
    finish_signal = Signal()

    def __init__(self, ip_network: str, cidr: int) -> None:
        super().__init__()
        self.ip_network: str = ip_network
        self.cidr: int = cidr
        self.ip_ranges: list[str] = generate_ip_range(f"{self.ip_network}/{self.cidr}")

        self.send_count: int = 0
        self._lock = threading.Lock()

        self.command: Command = Command(CommandRequest.SET_GET_NETWORK, data=bytearray([CommandOption.GET.value]))
        self.tcp_port: int = int(os.getenv('TCP_PORT'))

    def _send_broadcast(self) -> None:
        broadcast_socket: socket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
        broadcast_socket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        broadcast_socket.bind(('0.0.0.0', 5000))
        broadcast_socket.settimeout(1.5)

        broadcast_socket.sendto(self.command.serialize(), ("255.255.255.255", 5000))

        try:
            while True:
                data, addr = broadcast_socket.recvfrom(29)
                try:
                    response: ResponseNetworkSettings = ResponseNetworkSettings(data)
                    self.network_settings_signal.emit(response.network_settings)
                except AssertionError as _:
                    logger.error(f"SearchIpThread() >> _send_broadcast >> "
                                 f"Parse error from: {addr[0]}, data: {hex_readable(data)}")
                except (socket.timeout, TimeoutError):
                    logger.error("SearchIpThread() >> _send_broadcast >> No response received within the timeout period.")
                    break
        except Exception as e:
            pass
        finally:
            broadcast_socket.close()

    def _send_manual(self) -> None:
        def send_request(ip_address: str, port: int) -> None:
            request_socket: socket = socket(AF_INET, SOCK_STREAM)
            request_socket.settimeout(1.5)
            try:
                request_socket.connect((ip_address, port))

                request_socket.sendall(self.command.serialize())

                data: bytes = request_socket.recv(29)
                try:
                    response: ResponseNetworkSettings = ResponseNetworkSettings(data)
                    self.network_settings_signal.emit(response.network_settings)
                except AssertionError as _:
                    logger.error(f"SearchIpThread() >> _send_manual() >> Parse error from: {ip_address}:{port}, "
                                 f"data: {hex_readable(data)}")
            except Exception as e:
                pass
            finally:
                request_socket.close()

            with self._lock:
                self.send_count += 1
                self.progress_signal.emit(self.progress_in_percent)

        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(send_request, ip_add, self.tcp_port) for ip_add in self.ip_ranges]
            for future in as_completed(futures):
                result = future.result()
                if result is None:
                    continue

    @property
    def progress_in_percent(self):
        return int(100 * self.send_count / len(self.ip_ranges))

    def run(self) -> None:
        try:
            self._send_broadcast()
            self._send_manual()
            self.finish_signal.emit()
        except Exception as e:
            log_traceback(logger, e)
            self.network_settings_signal.emit(e)
            self.finish_signal.emit()
