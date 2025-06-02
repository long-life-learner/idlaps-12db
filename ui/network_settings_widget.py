import os
from time import sleep

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QPushButton, QVBoxLayout, QGroupBox, QLineEdit, QHBoxLayout, \
    QSpinBox

from rfid.reader import Reader
from rfid.reader_settings import NetworkSettings
from rfid.response import Response, Status, ResponseNetworkSettings
from rfid.transport import TcpTransport
from rfid.utils import ip_bytes, hex_readable, ip_string
from ui.thread.network_settings_thread import GetNetworkSettingsThread, SetNetworkSettingsThread
from ui.utils import show_message_box, IpAddressValidator


class NetworkSettingsWidget(QWidget):
    on_reboot_signal = Signal(bool)

    def __init__(self, reader: Reader) -> None:
        super().__init__()

        # GroupBox Network settings
        network_settings_group_box = QGroupBox("Network settings")
        mac_address_label = QLabel("MAC address")
        mac_address_label.setMinimumWidth(60)
        ip_address_label = QLabel("IP address")
        ip_address_label.setMinimumWidth(60)
        netmask_label = QLabel("Netmask")
        netmask_label.setMinimumWidth(60)
        gateway_label = QLabel("Gateway")
        gateway_label.setMinimumWidth(60)

        self.mac_address_line_edit = QLineEdit("")
        self.mac_address_line_edit.setReadOnly(True)
        self.ip_address_line_edit = QLineEdit(os.getenv('IP_ADDRESS'))
        self.ip_address_line_edit.setValidator(IpAddressValidator())
        self.port_spin_box = QSpinBox()
        self.port_spin_box.setRange(0, 65535)
        self.port_spin_box.setValue(int(os.getenv('TCP_PORT')))
        self.port_spin_box.setMinimumWidth(70)
        self.netmask_line_edit = QLineEdit("255.255.255.0")
        self.netmask_line_edit.setValidator(IpAddressValidator())
        self.gateway_line_edit = QLineEdit("192.168.1.1")
        self.gateway_line_edit.setValidator(IpAddressValidator())

        h_ip_address_port_layout = QHBoxLayout()
        h_ip_address_port_layout.addWidget(self.ip_address_line_edit)
        h_ip_address_port_layout.addWidget(self.port_spin_box)

        network_settings_grid_layout = QGridLayout()
        network_settings_grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        network_settings_grid_layout.addWidget(mac_address_label, 0, 0)
        network_settings_grid_layout.addWidget(self.mac_address_line_edit, 0, 1)
        network_settings_grid_layout.addWidget(ip_address_label, 1, 0)
        network_settings_grid_layout.addLayout(h_ip_address_port_layout, 1, 1)
        network_settings_grid_layout.addWidget(netmask_label, 2, 0)
        network_settings_grid_layout.addWidget(self.netmask_line_edit, 2, 1)
        network_settings_grid_layout.addWidget(gateway_label, 3, 0)
        network_settings_grid_layout.addWidget(self.gateway_line_edit, 3, 1)
        network_settings_grid_layout.addWidget(QLabel("<i>*This feature only available "
                                                      "for reader has TCP/IP port.</i>"), 4, 0, 1, 2)

        h_network_settings_layout = QHBoxLayout()
        h_network_settings_layout.addLayout(network_settings_grid_layout, 1)
        h_network_settings_layout.addWidget(QLabel(""), 1)

        network_settings_group_box.setLayout(h_network_settings_layout)
        network_settings_layout = QVBoxLayout()
        network_settings_layout.addWidget(network_settings_group_box)

        # Button (read, set)
        self.read_button = QPushButton("Get")
        self.read_button.clicked.connect(self.__read_clicked)
        self.read_button.setMinimumHeight(32)
        self.set_button = QPushButton("Set")
        self.set_button.clicked.connect(self.__set_clicked)
        self.set_button.setMinimumHeight(32)

        button_grid_layout = QGridLayout()
        button_grid_layout.addWidget(self.read_button, 0, 0)
        button_grid_layout.addWidget(self.set_button, 0, 1)
        button_grid_layout.addWidget(QLabel(), 0, 2, 1, 2)
        button_grid_layout.addWidget(QLabel(""), 0, 5)

        # Combine Layout
        layout = QVBoxLayout()
        layout.addLayout(button_grid_layout)
        layout.addLayout(network_settings_layout)
        self.setLayout(layout)

        self.reader = reader
        self.get_network_settings_thread: GetNetworkSettingsThread | None = None
        self.set_network_settings_thread: SetNetworkSettingsThread | None = None
        self.__network_settings: NetworkSettings | None = None

    @property
    def mac_address(self) -> str:
        return self.mac_address_line_edit.text().strip()

    @property
    def ip_address(self) -> str:
        return self.ip_address_line_edit.text().strip()

    @property
    def port(self) -> int:
        return int(self.port_spin_box.text().strip())

    @property
    def netmask(self) -> str:
        return self.netmask_line_edit.text().strip()

    @property
    def gateway(self) -> str:
        return self.gateway_line_edit.text().strip()

    @property
    def network_settings(self) -> NetworkSettings | None:
        if not self.mac_address:
            raise ValueError("MAC address is not valid.")
        if not self.ip_address:
            raise ValueError("IP address is not valid.")
        if not self.port:
            raise ValueError("Port is not valid.")
        if not self.netmask:
            raise ValueError("Netmask is not valid.")
        if not self.gateway:
            raise ValueError("Gateway is not valid.")

        ip_address = ip_bytes(self.ip_address)
        netmask = ip_bytes(self.netmask)
        gateway = ip_bytes(self.gateway)

        return NetworkSettings(
            mac_address=self.__network_settings.mac_address,
            ip_address=ip_address,
            port=self.port,
            netmask=netmask,
            gateway=gateway,
        )

    @network_settings.setter
    def network_settings(self, value: NetworkSettings) -> None:
        self.__network_settings = value

        self.mac_address_line_edit.setText(hex_readable(value.mac_address))
        self.ip_address_line_edit.setText(ip_string(value.ip_address))
        self.port_spin_box.setValue(value.port)
        self.netmask_line_edit.setText(ip_string(value.netmask))
        self.gateway_line_edit.setText(ip_string(value.gateway))

    def __receive_signal_network_settings(self, response: ResponseNetworkSettings | Exception) -> None:
        self.read_button.setEnabled(True)

        if isinstance(response, ResponseNetworkSettings):
            if response.status == Status.SUCCESS:
                self.network_settings = response.network_settings
            else:
                show_message_box("Failed", response.status.name, success=False)
        elif isinstance(response, Exception):
            message = str(response)
            if not message:
                message = "Something went wrong, can't set network settings."
            show_message_box("Failed", message)
        else:
            show_message_box("Failed", "Can't set network settings.", success=False)

    def __check_is_ready(self) -> None:
        self.on_reboot_signal.emit(True)
        response = None
        for i in range(3):
            sleep(3)

            if isinstance(self.reader.transport, TcpTransport):
                self.reader.transport.reconnect(ip_address=self.ip_address, port=self.port)
            else:  # Serial, USB
                self.reader.transport.reconnect()

            response = self.reader.init()
            if isinstance(response, Response):
                break
        if response is None:
            show_message_box("Failed", "Failed reconnect to reader after reboot.")
            return
        if response:
            show_message_box("Successful", "Set network settings successfully, reader is ready to use.", success=True)
            self.on_reboot_signal.emit(False)

    def __receive_signal_result_set_network_settings(self, response: NetworkSettings | Exception) -> None:
        self.set_button.setEnabled(True)

        if isinstance(response, NetworkSettings):
            self.reader_settings = response

            show_message_box("Success", "Successful set network settings, "
                                        "please wait until reader is ready.", success=True)
            self.__check_is_ready()
        elif isinstance(response, Exception):
            message = str(response)
            if not message:
                message = "Something went wrong, can't set network settings."
            show_message_box("Failed", message)
        else:
            show_message_box("Failed", "Can't set network settings.", success=False)

    def __read_clicked(self) -> None:
        self.read_button.setEnabled(False)

        self.get_network_settings_thread = GetNetworkSettingsThread(self.reader)
        self.get_network_settings_thread.network_settings_signal.connect(self.__receive_signal_network_settings)
        self.get_network_settings_thread.start()

    def __set_clicked(self) -> None:
        self.set_network_settings_thread = SetNetworkSettingsThread(self.reader)

        try:
            self.set_network_settings_thread.network_settings = self.network_settings
        except (AssertionError, ValueError) as e:
            show_message_box("Failed", str(e))
            return

        self.set_button.setEnabled(False)

        self.set_network_settings_thread.result_set_network_settings_signal \
            .connect(self.__receive_signal_result_set_network_settings)
        self.set_network_settings_thread.start()
