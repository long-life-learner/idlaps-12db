import os
from enum import Enum
from logging import getLogger
from PySide6 import QtCore
from PySide6.QtCore import Signal, QSize
from PySide6.QtWidgets import QWidget, QTabWidget, \
    QLabel, QComboBox, QLineEdit, QGridLayout, QPushButton, QVBoxLayout, QProgressBar, QSpinBox, QListWidget, QListWidgetItem, QHBoxLayout

from usb import USBError
from rfid.exception import ReaderException
from rfid.reader import Reader
from rfid.reader_settings import BaudRate, NetworkSettings
from rfid.transport import UsbTransport, SerialTransport, DeviceAddress, TcpTransport, ConnectionType
from rfid.utils import ip_string
from ui.search_widget import SearchIpWidget
from ui.thread.connect_thread import RefreshUsbDeviceAddressesThread, ConnectThread, RefreshSerialPortThread
from ui.utils import IpAddressValidator, set_widget_style, show_message_box


logger = getLogger()


class _ConnectTabWidget(QTabWidget):
    def __init__(self) -> None:
        super().__init__()

        self.serial_widget: ConnectSerialWidget = ConnectSerialWidget()
        self.usb_widget: ConnectUsbWidget = ConnectUsbWidget()
        self.usb_widget.device_addresses_signal.connect(self.__receive_signal_device_addresses)
        self.tcp_widget: ConnectTcpWidget = ConnectTcpWidget()

        self.addTab(self.serial_widget, str(ConnectionType.SERIAL))
        self.addTab(self.usb_widget, str(ConnectionType.USB))
        self.addTab(self.tcp_widget, str(ConnectionType.TCP_IP))

    def close(self) -> bool:
        self.serial_widget.close()
        self.usb_widget.close()
        return True

    def __receive_signal_device_addresses(self, device_addresses: list[DeviceAddress]) -> None:
        if len(device_addresses) > 0:
            self.setCurrentIndex(1)


class ConnectSerialWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()

        port_label = QLabel("Port")
        port_label.setMaximumWidth(30)
        baud_rate_label = QLabel("Baud Rate")
        baud_rate_label.setMaximumWidth(60)

        self.port_combo_box = QComboBox()
        self.baud_rate_combo_box = QComboBox()
        self.baud_rate_combo_box.addItems([str(baud_rate) for baud_rate in BaudRate])
        selected_baud_rate = BaudRate.from_int(int(os.getenv('BAUD_RATE')))
        selected_baud_rate_index = self.baud_rate_combo_box.findText(str(selected_baud_rate),
                                                                     QtCore.Qt.MatchFlag.MatchFixedString)
        self.baud_rate_combo_box.setCurrentIndex(selected_baud_rate_index)
        self.refresh_button = QPushButton("↻")
        self.refresh_button.clicked.connect(self.refresh_serial_ports)
        self.refresh_button.setToolTip("Refresh")
        self.refresh_button.setMaximumWidth(30)

        layout = QGridLayout()
        layout.addWidget(port_label, 0, 0)
        layout.addWidget(self.port_combo_box, 0, 1)
        layout.addWidget(baud_rate_label, 0, 2)
        layout.addWidget(self.baud_rate_combo_box, 0, 3)
        layout.addWidget(self.refresh_button, 0, 4)
        self.setLayout(layout)

        # Logic
        self.refresh_serial_port_thread = RefreshSerialPortThread()
        self.refresh_serial_port_thread.ports_signal.connect(self.__receive_signal_refresh_serial_ports)
        self.refresh_serial_port_thread.start()

    def close(self) -> None:
        self.refresh_serial_port_thread.terminate()

    @property
    def port(self) -> str:
        if not self.port_combo_box.currentText():
            raise ValueError("Port is empty")
        return self.port_combo_box.currentText().strip()

    @property
    def baud_rate(self) -> BaudRate:
        if self.baud_rate_combo_box.currentIndex() == -1:
            raise ValueError("Baud rate is empty")
        return BaudRate(self.baud_rate_combo_box.currentIndex())

    def refresh_serial_ports(self) -> None:
        self.refresh_button.setEnabled(False)

        self.refresh_serial_port_thread = RefreshSerialPortThread()
        self.refresh_serial_port_thread.ports_signal.connect(self.__receive_signal_refresh_serial_ports)
        self.refresh_serial_port_thread.start()

    def __receive_signal_refresh_serial_ports(self, ports: list[str]) -> None:
        self.refresh_button.setEnabled(True)

        self.port_combo_box.clear()
        self.port_combo_box.addItems(ports)


class ConnectUsbWidget(QWidget):
    device_addresses_signal = Signal(list)

    def __init__(self) -> None:
        super().__init__()

        layout = QGridLayout()
        port_label = QLabel("Port")
        port_label.setMaximumWidth(30)

        self.device_addresses_combo_box = QComboBox()
        self.refresh_button = QPushButton("↻")
        self.refresh_button.clicked.connect(self.refresh_usb_ports)
        self.refresh_button.setToolTip("Refresh")
        self.refresh_button.setMaximumWidth(30)

        layout.addWidget(port_label, 0, 0)
        layout.addWidget(self.device_addresses_combo_box, 0, 1)
        layout.addWidget(self.refresh_button, 0, 2)
        self.setLayout(layout)

        # Logic
        self.device_addresses = []
        self.refresh_usb_device_address_thread = RefreshUsbDeviceAddressesThread()
        self.refresh_usb_device_address_thread.\
            device_addresses_signal.connect(self.__receive_signal_refresh_usb_device_addresses)
        self.refresh_usb_device_address_thread.start()

    def close(self) -> None:
        self.refresh_usb_device_address_thread.terminate()

    @property
    def device_address(self) -> DeviceAddress:
        if self.device_addresses_combo_box.currentIndex() < 0:
            raise ValueError("Port is empty")
        return self.device_addresses[self.device_addresses_combo_box.currentIndex()]

    def refresh_usb_ports(self) -> None:
        self.refresh_button.setEnabled(False)

        self.refresh_usb_device_address_thread = RefreshUsbDeviceAddressesThread()
        self.refresh_usb_device_address_thread.\
            device_addresses_signal.connect(self.__receive_signal_refresh_usb_device_addresses)
        self.refresh_usb_device_address_thread.start()

    def __receive_signal_refresh_usb_device_addresses(self, device_addresses: list[DeviceAddress]) -> None:
        self.refresh_button.setEnabled(True)

        self.device_addresses = device_addresses
        self.device_addresses_combo_box.clear()
        self.device_addresses_combo_box.addItems([str(device_address) for device_address in self.device_addresses])
        self.device_addresses_signal.emit(device_addresses)


class ConnectTcpWidget(QWidget):
    search_ip_list_selected_signal = Signal(list)

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout()
        
        # Input Header
        input_layout = QHBoxLayout()
        ip_address_port_label = QLabel("IP Address")
        ip_address_port_label.setMaximumWidth(60)
        port_label = QLabel("Port")
        port_label.setMaximumWidth(30)

        self.ip_address_line_edit = QLineEdit(os.getenv('IP_ADDRESS', '192.168.1.200'))
        self.ip_address_line_edit.setMaximumWidth(120)
        self.ip_address_line_edit.setValidator(IpAddressValidator())

        self.port_spin_box = QSpinBox()
        self.port_spin_box.setRange(0, 65535)
        self.port_spin_box.setValue(int(os.getenv('TCP_PORT', '2022')))
        self.port_spin_box.setMaximumWidth(60)

        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self._add_manual_ip)
        self.add_button.setMaximumWidth(50)

        self.search_ip_button = QPushButton("Search")
        self.search_ip_button.clicked.connect(self._show_search_ip_widget)

        input_layout.addWidget(ip_address_port_label)
        input_layout.addWidget(self.ip_address_line_edit)
        input_layout.addWidget(port_label)
        input_layout.addWidget(self.port_spin_box)
        input_layout.addWidget(self.add_button)
        input_layout.addWidget(self.search_ip_button)
        
        # List of IPs
        self.ip_list_widget = QListWidget()
        
        layout.addLayout(input_layout)
        layout.addWidget(self.ip_list_widget)
        self.setLayout(layout)

        self.search_widget: SearchIpWidget = SearchIpWidget()
        self.search_widget.network_settings_list_signal.connect(self._on_search_ip_selected)

    def _add_manual_ip(self):
        ip_address = self.ip_address_line_edit.text().strip()
        port = self.port_spin_box.value()
        if not ip_address:
            return
        self._add_to_list(ip_address, port)

    def _on_search_ip_selected(self, network_settings_list: list[NetworkSettings]):
        for ns in network_settings_list:
            ip_str = ip_string(ns.ip_address)
            self._add_to_list(ip_str, ns.port)

    def _add_to_list(self, ip_address: str, port: int):
        display_text = f"{ip_address}:{port}"
        # Cek apakah sudah ada (mencegah duplikat)
        for i in range(self.ip_list_widget.count()):
            item = self.ip_list_widget.item(i)
            # Karena custom widget, kita cek user data
            if item.data(QtCore.Qt.UserRole) == display_text:
                return

        # Buat Custom Item dengan Tombol Hapus
        item = QListWidgetItem(self.ip_list_widget)
        item.setData(QtCore.Qt.UserRole, display_text)
        
        widget = QWidget()
        widget_layout = QHBoxLayout()
        widget_layout.setContentsMargins(5, 2, 5, 2)
        
        lbl = QLabel(display_text)
        del_btn = QPushButton("×")
        del_btn.setFixedSize(20, 20)
        del_btn.setStyleSheet("color: #f38ba8; font-weight: bold; border: none; background: transparent;")
        del_btn.clicked.connect(lambda: self.ip_list_widget.takeItem(self.ip_list_widget.row(item)))
        
        widget_layout.addWidget(lbl)
        widget_layout.addStretch()
        widget_layout.addWidget(del_btn)
        widget.setLayout(widget_layout)
        
        item.setSizeHint(widget.sizeHint())
        self.ip_list_widget.setItemWidget(item, widget)

    def get_all_tcp_transports(self) -> list[TcpTransport]:
        transports = []
        for i in range(self.ip_list_widget.count()):
            item = self.ip_list_widget.item(i)
            text = item.data(QtCore.Qt.UserRole)
            ip_addr, port_str = text.split(":")
            transports.append(TcpTransport(ip_addr, int(port_str)))
        return transports

    def _show_search_ip_widget(self) -> None:
        self.search_widget.show()



class ConnectWidget(QWidget):
    readers_connected_signal = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(os.getenv('APP_NAME'))
        set_widget_style(self)

        self.tab = _ConnectTabWidget()


        self.progress_bar = QProgressBar(self)
        self.progress_bar.setContentsMargins(1, 1, 1, 1)
        self.progress_bar.setMaximumSize(QSize(999999, 5))
        self.progress_bar.setMaximum(0)
        self.progress_bar.setValue(-1)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.__connect_clicked)
        self.connect_button.setMinimumHeight(32)

        layout = QVBoxLayout()
        layout.addWidget(self.tab)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.connect_button)

        self.setLayout(layout)

        self.connect_threads: list[ConnectThread] = []
        self.connected_readers: list[Reader] = []
        self.failed_ports: list[str] = []
        self.active_threads_count = 0

    def closeEvent(self, event):
        self.tab.close()
        for thread in self.connect_threads:
            thread.terminate()
        event.accept()

    @property
    def connection_type(self) -> ConnectionType:
        return ConnectionType(self.tab.currentIndex())

    @property
    def serial_widget(self) -> ConnectSerialWidget:
        return self.tab.serial_widget

    @property
    def usb_widget(self) -> ConnectUsbWidget:
        return self.tab.usb_widget

    @property
    def tcp_widget(self) -> ConnectTcpWidget:
        return self.tab.tcp_widget

    def __connect_clicked(self) -> None:
        transports = []
        try:
            if self.connection_type == ConnectionType.SERIAL:
                transports.append(SerialTransport(self.serial_widget.port, self.serial_widget.baud_rate))
            elif self.connection_type == ConnectionType.USB:
                transports.append(UsbTransport(self.usb_widget.device_address))
            elif self.connection_type == ConnectionType.TCP_IP:
                transports = self.tcp_widget.get_all_tcp_transports()
                if not transports:
                    show_message_box("Warning", "IP list is empty. Please add or search IPs first.", success=False)
                    return
        except Exception as e:
            show_message_box("Failed", f"Something went wrong, {e}.", success=False)
            return

        self.progress_bar.show()
        self.setEnabled(False)
        
        self.connect_threads.clear()
        self.connected_readers.clear()
        self.failed_ports.clear()
        self.active_threads_count = len(transports)

        for transport in transports:
            logger.info(f"ConnectWidget() > __connect_clicked() > transport: {transport}")
            thread = ConnectThread(transport)
            thread.reader_connected_signal.connect(self.__receive_signal_reader_connected)
            thread.finished_signal.connect(lambda t: self.__on_thread_finished())
            thread.start()
            self.connect_threads.append(thread)

    def __receive_signal_reader_connected(self, response: Reader | Exception) -> None:
        if isinstance(response, Reader):
            self.connected_readers.append(response)
        elif isinstance(response, Exception):
            # Coba ambil info transport jika ada, atau buat dummy message
            msg = str(response)
            if isinstance(response, USBError) and 'timeout error' in str(response):
                msg = "USB timeout"
            if not msg:
                msg = "Connection failed"
            self.failed_ports.append(msg)

    def __on_thread_finished(self):
        self.active_threads_count -= 1
        if self.active_threads_count == 0:
            self.progress_bar.hide()
            self.setEnabled(True)

            if self.failed_ports:
                msg = "Gagal terkoneksi ke beberapa perangkat:\n" + "\n".join(self.failed_ports)
                show_message_box("Sebagian Koneksi Gagal", msg, success=False)

            if self.connected_readers:
                self.readers_connected_signal.emit(self.connected_readers)
            else:
                show_message_box("Failed", "Semua koneksi gagal. Silahkan coba lagi.", success=False)


