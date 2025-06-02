import os
from enum import Enum
from logging import getLogger
from PySide6 import QtCore
from PySide6.QtCore import Signal, QSize
from PySide6.QtWidgets import QWidget, QTabWidget, \
    QLabel, QComboBox, QLineEdit, QGridLayout, QPushButton, QVBoxLayout, QProgressBar, QSpinBox
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
    search_ip_selected_signal = Signal(type)

    def __init__(self) -> None:
        super().__init__()

        self.serial_widget: ConnectSerialWidget = ConnectSerialWidget()
        self.usb_widget: ConnectUsbWidget = ConnectUsbWidget()
        self.usb_widget.device_addresses_signal.connect(self.__receive_signal_device_addresses)
        self.tcp_widget: ConnectTcpWidget = ConnectTcpWidget()
        self.tcp_widget.search_ip_selected_signal.connect(self.__receive_signal_search_ip_selected)

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

    def __receive_signal_search_ip_selected(self, network_settings: NetworkSettings) -> None:
        self.search_ip_selected_signal.emit(network_settings)


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
    search_ip_selected_signal = Signal(type)

    def __init__(self) -> None:
        super().__init__()

        layout = QGridLayout()
        ip_address_port_label = QLabel("IP Address")
        ip_address_port_label.setMaximumWidth(90)
        port_label = QLabel("Port")
        port_label.setMaximumWidth(70)
        or_label = QLabel("or")
        or_label.setMaximumWidth(50)

        self.ip_address_line_edit = QLineEdit(os.getenv('IP_ADDRESS'))
        self.ip_address_line_edit.setMaximumWidth(200)
        self.ip_address_line_edit.setValidator(IpAddressValidator())

        self.port_spin_box = QSpinBox()
        self.port_spin_box.setRange(0, 65535)
        self.port_spin_box.setValue(int(os.getenv('TCP_PORT')))
        self.port_spin_box.setMinimumWidth(70)
        self.port_spin_box.setMaximumWidth(70)

        self.search_ip_button: QPushButton = QPushButton("Search")
        self.search_ip_button.clicked.connect(self._show_search_ip_widget)

        layout.addWidget(ip_address_port_label, 0, 0)
        layout.addWidget(self.ip_address_line_edit, 0, 1)
        layout.addWidget(port_label, 0, 2)
        layout.addWidget(self.port_spin_box, 0, 3)
        layout.addWidget(or_label, 0, 4)
        layout.addWidget(self.search_ip_button, 0, 5)
        self.setLayout(layout)

        self.search_widget: SearchIpWidget = SearchIpWidget()
        self.search_widget.network_settings_signal.connect(self.search_ip_selected_signal.emit)

    @property
    def ip_address(self) -> str:
        value = self.ip_address_line_edit.text().strip()
        if not value:
            raise ValueError("IP address is empty")
        return value

    @property
    def port(self) -> int:
        value = self.port_spin_box.text().strip()

        if not value:
            raise ValueError("Port is empty")

        try:
            value = int(value)
        except ValueError:
            raise ValueError("Port must be a number")

        if not (0 < value <= 65_535):
            raise ValueError("Port must be start from 1 to 65.535")

        return value

    def _show_search_ip_widget(self) -> None:
        self.search_widget.show()


class ConnectWidget(QWidget):
    reader_connected_signal = Signal(Reader)
    search_ip_selected_signal = Signal(type)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(os.getenv('APP_NAME'))
        set_widget_style(self)

        self.tab = _ConnectTabWidget()
        self.tab.search_ip_selected_signal.connect(self.__receive_signal_search_ip_selected)

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

        self.connect_thread: ConnectThread | None = None

    def closeEvent(self, event):
        self.tab.close()
        if self.connect_thread:
            self.connect_thread.terminate()
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
        transport = None
        try:
            if self.connection_type == ConnectionType.SERIAL:
                transport = SerialTransport(self.serial_widget.port, self.serial_widget.baud_rate)
            elif self.connection_type == ConnectionType.USB:
                transport = UsbTransport(self.usb_widget.device_address)
            elif self.connection_type == ConnectionType.TCP_IP:
                transport = TcpTransport(self.tcp_widget.ip_address, self.tcp_widget.port)
        except Exception as e:
            show_message_box("Failed", f"Something went wrong, {e}.", success=False)
            return

        logger.info(f"ConnectWidget() > __connect_clicked() > self.connection_type: {self.connection_type}, "
                    f"transport: {transport}")

        assert transport is not None

        self.progress_bar.show()
        self.setEnabled(False)

        self.connect_thread = ConnectThread(transport)
        self.connect_thread.reader_connected_signal.connect(self.__receive_signal_reader_connected)
        self.connect_thread.start()

    def __receive_signal_reader_connected(self, response: Reader | Exception) -> None:
        self.progress_bar.hide()
        self.setEnabled(True)

        if isinstance(response, Reader):
            self.reader_connected_signal.emit(response)
        elif isinstance(response, ReaderException):
            show_message_box("Failed", response.message)
        elif isinstance(response, Exception):
            message = str(response)
            if isinstance(response, USBError) and 'timeout error' in str(response):
                message = "USB timeout, try again."
            if not message:
                message = "Something went wrong, can't connect to reader, maybe try another port/baud rate."
            show_message_box("Failed", message)

    def __receive_signal_search_ip_selected(self, network_settings: NetworkSettings) -> None:
        try:
            transport = TcpTransport(ip_string(network_settings.ip_address), network_settings.port)
        except Exception as e:
            show_message_box("Failed", f"Something went wrong, {e}.", success=False)
            return

        self.progress_bar.show()
        self.setEnabled(False)

        self.connect_thread = ConnectThread(transport)
        self.connect_thread.reader_connected_signal.connect(self.__receive_signal_reader_connected)
        self.connect_thread.start()

