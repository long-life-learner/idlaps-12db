from rfid.reader import Reader
from rfid.response import Response, ResponseCurrentTemperature
from ui.thread.temperature_settings_thread import GetCurrentTemperatureThread, SetMaxTemperatureThread
from ui.utils import show_message_box
from PySide6.QtWidgets import QSpinBox, QPushButton
from PySide6.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QLabel, QGroupBox, QLineEdit


class TemperatureSettingsWidget(QWidget):
    def __init__(self, reader: Reader) -> None:
        super().__init__()

        # GroupBox - Temperature settings
        temperature_group_box = QGroupBox("Temperature settings")
        current_temperature_label = QLabel("Current")
        max_temperature_label = QLabel("Max")
        current_temperature_unit_label = QLabel("°C")
        current_temperature_unit_label.setFixedWidth(20)
        max_temperature_unit_label = QLabel("°C")
        max_temperature_unit_label.setFixedWidth(20)
        info_label = QLabel("<i>*When is inventorying, if <u>current > max</u>,<br/>"
                            "will automatically stop the process.</i>")

        self.current_temperature_line_edit = QLineEdit()
        self.current_temperature_line_edit.setReadOnly(True)
        self.current_temperature_line_edit.setFixedWidth(50)
        self.max_temperature_spin_box = QSpinBox()
        self.max_temperature_spin_box.setRange(50, 90)
        self.max_temperature_spin_box.setFixedWidth(50)

        self.get_button = QPushButton("Get")
        self.get_button.clicked.connect(self.__get_clicked)
        self.set_button = QPushButton("Set")
        self.set_button.clicked.connect(self.__set_clicked)

        temperature_grid_layout = QGridLayout()
        temperature_grid_layout.addWidget(current_temperature_label, 0, 0)
        temperature_grid_layout.addWidget(self.current_temperature_line_edit, 0, 1)
        temperature_grid_layout.addWidget(current_temperature_unit_label, 0, 2)
        temperature_grid_layout.addWidget(self.get_button, 0, 3)
        temperature_grid_layout.addWidget(max_temperature_label, 1, 0)
        temperature_grid_layout.addWidget(self.max_temperature_spin_box, 1, 1)
        temperature_grid_layout.addWidget(max_temperature_unit_label, 1, 2)
        temperature_grid_layout.addWidget(self.set_button, 1, 3)
        temperature_grid_layout.addWidget(info_label, 2, 0, 1, 4)

        temperature_group_box.setLayout(temperature_grid_layout)

        v_layout = QVBoxLayout()
        v_layout.addWidget(temperature_group_box)
        self.setLayout(v_layout)

        self.reader: Reader | None = reader
        self.get_current_temperature_thread: GetCurrentTemperatureThread | None = None
        self.set_max_temperature_thread: SetMaxTemperatureThread | None = None

    def __set_button_enabled(self, value: bool) -> None:
        self.set_button.setEnabled(value)
        self.get_button.setEnabled(value)

    def __get_clicked(self) -> None:
        self.__set_button_enabled(False)

        self.get_current_temperature_thread = GetCurrentTemperatureThread(self.reader)
        self.get_current_temperature_thread.temperature_signal.connect(self.__receive_signal_result_get_temperature)
        self.get_current_temperature_thread.start()

    def __set_clicked(self) -> None:
        self.__set_button_enabled(False)

        self.set_max_temperature_thread = SetMaxTemperatureThread(self.reader)
        self.set_max_temperature_thread.max_temperature = self.max_temperature_spin_box.value()
        self.set_max_temperature_thread.result_set_max_temperature_signal.connect(
            self.__receive_signal_result_set_max_temperature)
        self.set_max_temperature_thread.start()

    def __receive_signal_result_get_temperature(self, response: ResponseCurrentTemperature | Exception) -> None:
        self.__set_button_enabled(True)

        if isinstance(response, ResponseCurrentTemperature):
            self.current_temperature_line_edit.setText(str(response.current_temperature))
            self.max_temperature_spin_box.setValue(response.max_temperature)
        else:
            show_message_box("Failed", "Can't get current temperature.", success=False)

    def __receive_signal_result_set_max_temperature(self, response: Response | Exception) -> None:
        self.__set_button_enabled(True)

        if isinstance(response, Exception):
            message = str(response)
            if not message:
                message = "Something went wrong, can't set max temperature."
            show_message_box("Failed", message)
