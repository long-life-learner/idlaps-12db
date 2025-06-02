import os
from logging import getLogger
from enum import Enum
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QTabWidget, QMenuBar, QMenu, QVBoxLayout

from rfid.exception import ReaderException
from rfid.reader import Reader
from rfid.reader_settings import DeviceInfo, WorkMode
from rfid.response import ResponseReaderSettings, Status, ResponseDeviceInfo, ResponseNetworkSettings
from rfid.utils import hex_readable
from ui.advance_settings_widget import AdvanceSettingsWidget
from ui.network_settings_widget import NetworkSettingsWidget
from ui.read_write_lock_kill_widget import ReadWriteLockKillWidget
from ui.reader_settings_widget import ReaderSettingsWidget
from ui.inventory_widget import InventoryWidget
from ui.log_widget import LogWidget
from ui.thread.device_info_thread import GetDeviceInfoThread
from ui.thread.network_settings_thread import GetNetworkSettingsThread
from ui.thread.reader_settings_thread import GetReaderSettingsThread
from ui.utils import show_message_box, set_widget_style

logger = getLogger()


class MainTab(Enum):
    READER_SETTINGS = "Reader settings"
    INVENTORY = "Inventory"
    READ_WRITE = "Read/write"
    NETWORK_SETTINGS = "Network settings"
    ADVANCE_SETTINGS = "Advance settings"
    EXPORT = "Export"


class _MainTabWidget(QTabWidget):
    device_info_signal = Signal(type)

    def __init__(self, reader: Reader) -> None:
        super().__init__()

        logger.info(f"_MainTabWidget() > __init__()")

        #RIKZA
        self.reader_settings_widget = ReaderSettingsWidget(reader)
        self.reader_settings_widget.on_reboot_signal.connect(self.__receive_signal_on_reboot)
        self.inventory_widget = InventoryWidget(reader)
        self.read_write_lock_kill_widget = ReadWriteLockKillWidget(reader)
        self.read_write_lock_kill_widget.is_read_write_lock_kill_signal.connect(
            self.__receive_signal_is_read_write_lock_kill)
        self.reader_settings_widget.work_mode_signal.connect(self.__receive_signal_work_mode)
        self.inventory_widget.is_inventory_signal.connect(self.__receive_signal_is_inventory)
        self.inventory_widget.tags_signal.connect(self.read_write_lock_kill_widget.receive_signal_tags)
        self.network_settings_widget = NetworkSettingsWidget(reader)
        self.network_settings_widget.on_reboot_signal.connect(self.__receive_signal_on_reboot)
        self.advance_settings_widget = AdvanceSettingsWidget(reader)

        self.device_info_signal.connect(self.__receive_signal_device_info)

        self.addTab(self.reader_settings_widget, MainTab.READER_SETTINGS.value)
        self.addTab(self.inventory_widget, MainTab.INVENTORY.value)
        self.addTab(self.read_write_lock_kill_widget, MainTab.READ_WRITE.value)
        self.addTab(self.network_settings_widget, MainTab.NETWORK_SETTINGS.value)
        self.addTab(self.advance_settings_widget, MainTab.ADVANCE_SETTINGS.value)
        # self.addTab(self.advance_settings_widget, MainTab.EXPORT.value)

    def close(self) -> None:
        logger.info(f"_MainTabWidget() > close()")
        self.reader_settings_widget.close()
        self.inventory_widget.close()
        self.read_write_lock_kill_widget.close()
        self.network_settings_widget.close()
        self.advance_settings_widget.close()

    def __receive_signal_device_info(self, value: DeviceInfo) -> None:
        self.inventory_widget.receive_device_info_signal(value)
        self.reader_settings_widget.receive_device_info_signal(value)
        self.advance_settings_widget.receive_device_info_signal(value)

        # Remove read/write tab
        if not value.series.enabled_read_write:
            for i in range(self.count()):
                if not isinstance(self.widget(i), ReadWriteLockKillWidget):
                    continue
                self.removeTab(i)

        # Remove network settings tab
        if not value.series.enabled_network_settings:
            for i in range(self.count()):
                if not isinstance(self.widget(i), NetworkSettingsWidget):
                    continue
                self.removeTab(i)

    def __receive_signal_is_inventory(self, value: bool) -> None:
        for i in range(self.count()):
            if not isinstance(self.widget(i), InventoryWidget):
                self.setTabEnabled(i, not value)

    def __receive_signal_is_read_write_lock_kill(self, value: bool) -> None:
        for i in range(self.count()):
            if not isinstance(self.widget(i), ReadWriteLockKillWidget):
                self.setTabEnabled(i, not value)

    def __receive_signal_work_mode(self, work_mode: WorkMode) -> None:
        self.inventory_widget.receive_work_mode_signal(work_mode)
        self.read_write_lock_kill_widget.receive_work_mode_signal(work_mode)

    def __receive_signal_on_reboot(self, value: bool) -> None:
        for i in reversed(range(self.count())):
            self.setTabEnabled(i, not value)


class MainWidget(QWidget):
    def __init__(self, reader: Reader) -> None:
    # def __init__(self, reader: None) -> None:
        super().__init__()
        logger.info(f"MainWidget() > __init__()")

        self.setWindowTitle(os.getenv('APP_NAME'))
        set_widget_style(self)

        # Menu bar
        self.menu_bar = QMenuBar()
        self.help_menu = QMenu("Help")
        self.help_menu.addAction("About", lambda: show_message_box("About",
                                                                   "This is a demo application for <br>Electron "
                                                                   "<u>EL-UHF-RC Series</u> UHF RFID Reader:"
                                                                   "<br><br>"
                                                                   "- <a href='https://www.electron.id/produk/el-uhf-rc4-2/'>EL-UHF-RC4-2 Std</a><br>"
                                                                   "- <a href='https://www.electron.id/produk/el-uhf-rc4-2/'>EL-UHF-RC4-2 TCP/IP</a><br>"
                                                                   "- <a href='https://www.electron.id/produk/el-uhf-rc4-62/'>EL-UHF-RC4-62-T</a><br>"
                                                                   "- <a href='https://www.electron.id/produk/el-uhf-rc4-91/'>EL-UHF-RC4-91-T</a><br>"
                                                                   "- <a href='https://www.electron.id/produk/el-uhf-rc4-c1/'>EL-UHF-RC4-C1-T</a><br>"
                                                                   "<br>"
                                                                   "Please contact <a "
                                                                   "href='mailto:sales@electron.id'>sales@electron.id"
                                                                   "</a> for more information."
                                                                   "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
                                                                   "<br><br>"
                                                                   f"Software version {os.getenv('VERSION')}",
                                                                   success=True, with_icon=True))
        self.menu_bar.addMenu(self.help_menu)

        # RIKZA
        self.tab = _MainTabWidget(reader)
        self.log_widget = LogWidget(reader)

        log_layout = QVBoxLayout()
        log_layout.addWidget(self.log_widget)

        # Combine Layout
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.tab)
        self.layout.addLayout(log_layout)
        self.layout.setMenuBar(self.menu_bar)
        self.setLayout(self.layout)

        self.setEnabled(True)

        self.reader = reader
        self.get_device_info_thread = GetDeviceInfoThread(self.reader)
        self.get_device_info_thread.device_info_signal.connect(self.__receive_signal_device_info)

        # After this widget (MainWidget) shown, try to get Device Info
        logger.info("MainWidget() > __init__() > Try to get Device Info using GetDeviceInfoThread")
        self.get_device_info_thread.start()

        self.get_reader_settings_thread = GetReaderSettingsThread(self.reader)
        self.get_reader_settings_thread.reader_settings_signal.connect(self.__receive_signal_reader_settings)

        self.get_network_settings_thread = GetNetworkSettingsThread(self.reader)
        self.get_network_settings_thread.network_settings_signal.connect(self.__receive_signal_network_settings)

        self.device_info: DeviceInfo | None = None

    def closeEvent(self, event):
        self.tab.close()
        self.get_device_info_thread.terminate()
        self.get_reader_settings_thread.terminate()
        self.reader.close()
        event.accept()
    
    def __receive_signal_device_info(self, response: ResponseDeviceInfo | Exception) -> None:
        if response is None:
            logger.warning("MainWidget() > Device info retrieval failed.")
            # Tampilkan dialog peringatan atau berikan respons default
            return

        logger.info(f"MainWidget() > __receive_signal_device_info() > response: {response}")

        if isinstance(response, ResponseDeviceInfo):
            if response.status == Status.SUCCESS:
                self.tab.device_info_signal.emit(response.device_info)
                self.get_reader_settings_thread.start()

                self.device_info = response.device_info
                # self.setWindowTitle(f"{self.device_info.series.name}  "
                #                     f"|  SN: {hex_readable(self.device_info.serial_number)}  "
                #                     f"|  {str(self.reader.transport.connection_type)}")
                self.setWindowTitle("IDLAPS CHECKPOINT")
                logger.info(f"MainWidget() > __receive_signal_device_info() "
                            f"> SN: {hex_readable(self.device_info.serial_number)}")
        elif isinstance(response, ReaderException):
            show_message_box("Failed", response.message)
        elif isinstance(response, Exception):
            message = str(response)
            if not message:
                message = "Something went wrong, can't get device info."
            show_message_box("Failed", message)

    def __receive_signal_reader_settings(self, response: ResponseReaderSettings | Exception) -> None:
        logger.info(f"MainWidget() > __receive_signal_reader_settings() > response: {response}")
        if isinstance(response, ResponseReaderSettings):
            if response.status == Status.SUCCESS:
                self.tab.reader_settings_widget.reader_settings = response.reader_settings

                if self.device_info.series.enabled_network_settings:
                    self.get_network_settings_thread.start()

                self.setEnabled(True)
            else:
                show_message_box("Failed", response.status.name)

        elif isinstance(response, ReaderException):
            show_message_box("Failed", response.message)
        elif isinstance(response, Exception):
            message = str(response)
            if not message:
                message = "Something went wrong, can't get reader settings."
            show_message_box("Failed", message)

    def __receive_signal_network_settings(self, response: ResponseNetworkSettings | Exception) -> None:
        logger.info(f"MainWidget() > __receive_signal_network_settings() > response: {response}")

        if isinstance(response, ResponseNetworkSettings):
            self.tab.network_settings_widget.network_settings = response.network_settings

        else:
            message = str(response)
            if not message:
                message = "Something went wrong, can't get network settings."
            show_message_box("Failed", message)
