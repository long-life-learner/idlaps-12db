from PySide6.QtGui import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QSizePolicy

from rfid.reader import Reader
from rfid.reader_settings import DeviceInfo
from ui.inventory_filter_widget import InventoryFilterWidget
from ui.output_control_widget import OutputControlWidget
from ui.temperature_settings_widget import TemperatureSettingsWidget


class AdvanceSettingsWidget(QWidget):
    def __init__(self, reader: Reader):
        super().__init__()

        self.reader = reader
        self.__device_info: DeviceInfo | None = None
        self.inventory_filter_widget = InventoryFilterWidget(reader)
        self.output_control_widget = OutputControlWidget(reader)
        self.temperature_settings_widget = TemperatureSettingsWidget(reader)
        self.temperature_settings_widget.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.v_layout = QVBoxLayout()

        self.setLayout(self.v_layout)

    def receive_device_info_signal(self, device_info: DeviceInfo) -> None:
        self.device_info = device_info

    @property
    def device_info(self) -> DeviceInfo | None:
        return self.__device_info

    @device_info.setter
    def device_info(self, value: DeviceInfo) -> None:
        self.__device_info = value

        if self.__device_info.series.enabled_inventory_filter:
            self.v_layout.addWidget(self.inventory_filter_widget)

        if self.__device_info.series.enabled_output_control:
            self.v_layout.addWidget(self.output_control_widget)

        if self.__device_info.series.enabled_set_temperature:
            layout = QHBoxLayout()
            layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            layout.addWidget(self.temperature_settings_widget, stretch=1)
            layout.addWidget(QLabel(), stretch=2)
            self.v_layout.addLayout(layout)

        self.v_layout.addWidget(QLabel(), stretch=2)

        self.setLayout(self.v_layout)


