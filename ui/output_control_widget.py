from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QPushButton, QVBoxLayout, QGroupBox, QLineEdit, QHBoxLayout, \
    QSpinBox, QCheckBox, QComboBox

from rfid.reader import Reader
from rfid.reader_settings import Relay, OutputControl
from rfid.response import Response, Status, ResponseOutputControl
from ui.thread.output_control_thread import SetManualRelayThread, SetAutoRelayThread, GetOutputControlThread
from ui.utils import show_message_box


class OutputControlWidget(QWidget):
    def __init__(self, reader: Reader) -> None:
        super().__init__()

        # GroupBox Output control
        output_control_group_box = QGroupBox("Output control")

        # Manual relay
        manual_relay_group_box = QGroupBox("Manual relay")

        manual_relay_label = QLabel("Relay")
        manual_relay_label.setFixedWidth(30)

        self.close_manual_relay_button = QPushButton("Close")
        self.close_manual_relay_button.setFixedWidth(100)
        self.close_manual_relay_button.setFixedHeight(30)
        self.close_manual_relay_button.clicked.connect(self.__set_close_manual_relay_clicked)
        self.open_manual_relay_button = QPushButton("Open")
        self.open_manual_relay_button.setFixedWidth(100)
        self.open_manual_relay_button.setFixedHeight(30)
        self.open_manual_relay_button.clicked.connect(self.__set_open_manual_relay_clicked)
        self.manual_time_relay_spin_box = QSpinBox()
        self.manual_time_relay_spin_box.setRange(0, 255)
        close_after_label = QLabel("for")
        manual_time_relay_unit_label = QLabel("second(s)")

        grid_manual_relay_layout = QGridLayout()
        grid_manual_relay_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        grid_manual_relay_layout.addWidget(self.open_manual_relay_button, 0, 0)
        grid_manual_relay_layout.addWidget(self.close_manual_relay_button, 0, 1)
        grid_manual_relay_layout.addWidget(close_after_label, 0, 2)
        grid_manual_relay_layout.addWidget(self.manual_time_relay_spin_box, 0, 3)
        grid_manual_relay_layout.addWidget(manual_time_relay_unit_label, 0, 4)
        manual_relay_group_box.setLayout(grid_manual_relay_layout)

        # Auto relay
        auto_relay_group_box = QGroupBox("Automatic relay")

        self.auto_relay_check_box = QCheckBox("Enabled")
        self.auto_time_relay_spin_box = QSpinBox()
        self.auto_time_relay_spin_box.setRange(0, 255)
        self.auto_time_relay_spin_box.setValue(1)
        self.read_auto_relay_button = QPushButton("Get")
        self.read_auto_relay_button.setFixedWidth(100)
        self.read_auto_relay_button.setFixedHeight(30)
        self.read_auto_relay_button.clicked.connect(self.__read_auto_relay_clicked)
        self.set_auto_relay_button = QPushButton("Set")
        self.set_auto_relay_button.setFixedWidth(100)
        self.set_auto_relay_button.setFixedHeight(30)
        self.set_auto_relay_button.clicked.connect(self.__set_auto_relay_clicked)
        h_button_auto_relay_layout = QHBoxLayout()
        h_button_auto_relay_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        h_button_auto_relay_layout.addWidget(self.read_auto_relay_button)
        h_button_auto_relay_layout.addWidget(self.set_auto_relay_button)

        h_set_auto_relay_layout = QHBoxLayout()
        h_set_auto_relay_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        h_set_auto_relay_layout.addWidget(self.auto_relay_check_box)
        h_set_auto_relay_layout.addWidget(QLabel("for "))
        h_set_auto_relay_layout.addWidget(self.auto_time_relay_spin_box)
        h_set_auto_relay_layout.addWidget(QLabel("second(s)"))

        v_auto_relay_layout = QVBoxLayout()
        v_auto_relay_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        v_auto_relay_layout.addLayout(h_button_auto_relay_layout)
        v_auto_relay_layout.addLayout(h_set_auto_relay_layout)

        auto_relay_group_box.setLayout(v_auto_relay_layout)

        h_relay_layout = QHBoxLayout()
        h_relay_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        h_relay_layout.addWidget(manual_relay_group_box, stretch=1)
        h_relay_layout.addWidget(auto_relay_group_box, stretch=1)

        output_control_group_box.setLayout(h_relay_layout)

        layout = QVBoxLayout()
        layout.addWidget(output_control_group_box)
        layout.setSpacing(0)
        layout.setContentsMargins(1, 1, 1, 1)
        self.setLayout(layout)

        self.reader: Reader | None = reader
        self.set_manual_relay_thread: SetManualRelayThread | None = None
        self.get_output_control_thread: GetOutputControlThread | None = None
        self.set_auto_relay_thread: SetAutoRelayThread | None = None

    def __set_disabled_manual_relay_button(self, value: bool) -> None:
        self.open_manual_relay_button.setDisabled(value)
        self.close_manual_relay_button.setDisabled(value)

    @property
    def output_control(self) -> OutputControl:
        return OutputControl(
            enable_relay=self.auto_relay_check_box.isChecked(),
            relay_valid_time=self.auto_time_relay_spin_box.value()
        )

    @output_control.setter
    def output_control(self, value: OutputControl) -> None:
        self.auto_relay_check_box.setChecked(value.enable_relay)
        self.auto_time_relay_spin_box.setValue(value.relay_valid_time)

    def __receive_signal_result_set_manual_relay(self, response: Response | Exception) -> None:
        self.__set_disabled_manual_relay_button(False)

        if isinstance(response, Response):
            if response.status == Status.SUCCESS:
                # show_message_box("Success", "Successful set manual relay.", success=True)
                return
            else:
                show_message_box("Failed", response.status.name, success=False)
        elif isinstance(response, Exception):
            message = str(response)
            if not message:
                message = "Something went wrong, can't set manual relay"
            show_message_box("Failed", message)
        else:
            show_message_box("Failed", "Can't set manual relay", success=False)

    def __receive_signal_result_get_output_control(self, response: ResponseOutputControl | Exception) -> None:
        if isinstance(response, ResponseOutputControl):
            if response.status == Status.SUCCESS:
                self.output_control = response.output_control
                return
            else:
                show_message_box("Failed", response.status.name, success=False)
        elif isinstance(response, Exception):
            message = str(response)
            if not message:
                message = "Something went wrong, can't set automatic relay"
            show_message_box("Failed", message)
        else:
            show_message_box("Failed", "Can't set automatic relay", success=False)

    def __receive_signal_result_set_auto_relay(self, response: Response | Exception) -> None:
        if isinstance(response, Response):
            if response.status == Status.SUCCESS:
                show_message_box("Success", "Successful set automatic relay.", success=True)
                return
            else:
                show_message_box("Failed", response.status.name, success=False)
        elif isinstance(response, Exception):
            message = str(response)
            if not message:
                message = "Something went wrong, can't set automatic relay"
            show_message_box("Failed", message)
        else:
            show_message_box("Failed", "Can't set automatic relay", success=False)

    def __set_open_manual_relay_clicked(self) -> None:
        self.__set_disabled_manual_relay_button(True)

        self.set_manual_relay_thread = SetManualRelayThread(self.reader)
        self.set_manual_relay_thread.release = True
        self.set_manual_relay_thread.valid_time = self.manual_time_relay_spin_box.value()
        self.set_manual_relay_thread.result_set_manual_relay_signal\
            .connect(self.__receive_signal_result_set_manual_relay)
        self.set_manual_relay_thread.start()

    def __set_close_manual_relay_clicked(self) -> None:
        self.__set_disabled_manual_relay_button(True)

        self.set_manual_relay_thread = SetManualRelayThread(self.reader)
        self.set_manual_relay_thread.release = False
        self.set_manual_relay_thread.valid_time = self.manual_time_relay_spin_box.value()
        self.set_manual_relay_thread.result_set_manual_relay_signal \
            .connect(self.__receive_signal_result_set_manual_relay)
        self.set_manual_relay_thread.start()

    def __read_auto_relay_clicked(self) -> None:
        self.get_output_control_thread = GetOutputControlThread(self.reader)
        self.get_output_control_thread.result_get_output_control_signal.\
            connect(self.__receive_signal_result_get_output_control)
        self.get_output_control_thread.start()

    def __set_auto_relay_clicked(self) -> None:
        self.set_auto_relay_thread = SetAutoRelayThread(self.reader)
        self.set_auto_relay_thread.output_control = self.output_control
        self.set_auto_relay_thread.result_set_auto_relay_signal.connect(self.__receive_signal_result_set_auto_relay)
        self.set_auto_relay_thread.start()


