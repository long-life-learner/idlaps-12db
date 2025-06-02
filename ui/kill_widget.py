from PySide6.QtCore import Signal
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QGroupBox, QLineEdit, QHBoxLayout

from rfid.reader import Reader
from rfid.response import ResponseKillTag
from rfid.status import Status, TagStatus
from ui.thread.read_write_thread import KillThread
from ui.utils import show_message_box


class KillWidget(QWidget):
    is_kill_signal = Signal(bool)

    def __init__(self, reader: Reader) -> None:
        super().__init__()

        # GroupBox Kill
        kill_group_box = QGroupBox("Kill tag")
        kill_password_label = QLabel("Kill password")
        kill_password_label.setMinimumWidth(60)

        self.kill_password_line_edit = QLineEdit()
        self.kill_password_line_edit.setMaxLength(8)
        self.kill_password_line_edit.setText("00000000")
        self.kill_password_line_edit.setValidator(QRegularExpressionValidator("^[0-9a-fA-F]{0,8}$"))
        self.kill_password_line_edit.textEdited.connect(self.__kill_password_line_edit_edited)
        self.kill_password_line_edit.editingFinished.connect(self.__kill_password_line_edit_finished)

        self.kill_button = QPushButton("Kill")
        self.kill_button.setMinimumHeight(32)
        self.kill_button.clicked.connect(self.__kill_clicked)

        kill_h_layout = QHBoxLayout()
        kill_h_layout.addWidget(kill_password_label)
        kill_h_layout.addWidget(self.kill_password_line_edit)

        kill_v_layout = QVBoxLayout()
        kill_v_layout.addLayout(kill_h_layout)
        kill_v_layout.addWidget(self.kill_button)

        kill_group_box.setLayout(kill_v_layout)

        layout = QVBoxLayout()
        layout.addWidget(kill_group_box)
        layout.setSpacing(0)
        layout.setContentsMargins(1, 1, 1, 1)
        self.setLayout(layout)

        self.reader = reader
        self.kill_thread: KillThread | None = None

    @property
    def is_killing(self) -> bool:
        if self.kill_button.text() == "Stop":
            return True
        return False

    @property
    def kill_password(self) -> bytes:
        return bytearray.fromhex(self.kill_password_line_edit.text().replace(' ', ''))

    def __kill_password_line_edit_edited(self, text: str) -> None:
        self.kill_password_line_edit.setText(text.upper())

    def __kill_password_line_edit_finished(self) -> None:
        if len(self.kill_password_line_edit.text()) != 8:
            show_message_box("Failed", "Kill password must set to 8 hex characters.", success=False)

    def __receive_signal_result_kill(self, response: ResponseKillTag | Exception) -> None:
        self.kill_button.setEnabled(True)

        if isinstance(response, ResponseKillTag):
            pass
        elif isinstance(response, Exception):
            message = str(response)
            if not message:
                message = "Something went wrong, can't kill tag."
            show_message_box("Failed", message)
        else:
            show_message_box("Failed", "Can't kill tag.", success=False)

    def __receive_signal_result_kill_finished(self, responses: list[ResponseKillTag]) -> None:
        self.kill_button.setText("Kill")
        self.is_kill_signal.emit(False)

        for response in responses:
            if response.status not in [Status.SUCCESS, Status.NO_COUNT_LABEL]:
                show_message_box("Failed", f"Can't kill, response status {response.status.name}.")
                return

            if response.kill_tag.tag_status != TagStatus.NO_ERROR:
                show_message_box("Failed", f"Can't kill, response tag status {response.kill_tag.tag_status.name}.")
                return

        tag_statuses = [response.kill_tag.tag_status for response in responses
                        if response.kill_tag is not None
                        and response.kill_tag.tag_status == TagStatus.NO_ERROR]
        if len(tag_statuses) > 0:
            show_message_box("Success", "Kill tag successfully.", success=True)

    def __kill_clicked(self) -> None:
        try:
            kill_password = self.kill_password
        except (AssertionError, ValueError) as e:
            show_message_box("Failed", str(e))
            return

        if not self.is_killing:
            self.kill_button.setText("Stop")
            self.is_kill_signal.emit(True)

            self.kill_thread = KillThread(self.reader)
            self.kill_thread.kill_password = kill_password
            self.kill_thread.result_kill_signal.connect(self.__receive_signal_result_kill)
            self.kill_thread.result_kill_finished_signal.connect(self.__receive_signal_result_kill_finished)
            self.kill_thread.start()
        else:
            self.kill_thread.request_stop = True
