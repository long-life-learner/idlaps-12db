from enum import Enum
from PySide6.QtCore import Signal
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QPushButton, QVBoxLayout, QGroupBox, \
    QLineEdit, QComboBox, QCheckBox, QSizePolicy

from rfid.reader import Reader
from rfid.reader_settings import LockMemoryBank, LockAction
from rfid.response import Status, ResponseLockMemory
from rfid.status import TagStatus
from ui.thread.read_write_thread import LockThread
from ui.utils import show_message_box, QHLine


class LockActionUi(Enum):
    UNLOCK = "Unlock"
    LOCK = "Lock"


class LockWidget(QWidget):
    is_lock_signal = Signal(bool)

    def __init__(self, reader: Reader) -> None:
        super().__init__()

        # GroupBox Lock
        lock_group_box = QGroupBox("Lock memory")
        lock_memory_bank_label = QLabel("Memory bank")
        lock_memory_bank_label.setMinimumWidth(60)
        lock_action_label = QLabel("Action")
        lock_action_label.setMinimumWidth(60)
        access_password_label = QLabel("Access password")
        access_password_label.setMinimumWidth(60)

        self.lock_memory_bank_combo_box = QComboBox()
        self.lock_memory_bank_combo_box.setMinimumWidth(100)
        self.lock_memory_bank_combo_box.addItems(str(lock_memory_bank) for lock_memory_bank in LockMemoryBank)
        self.lock_action_ui_combo_box = QComboBox()
        self.lock_action_ui_combo_box.setMinimumWidth(80)
        self.lock_action_ui_combo_box.addItems(lock_action_ui.value for lock_action_ui in LockActionUi)
        self.lock_action_ui_combo_box.currentTextChanged.connect(self.__on_changed_text_lock_action_ui)
        self.permanent_lock_check_box = QCheckBox("Permanent Unlock")
        self.permanent_lock_check_box.clicked.connect(self.__permanent_lock_check_box_clicked)
        self.access_password_line_edit = QLineEdit()
        self.access_password_line_edit.setMaxLength(8)
        self.access_password_line_edit.setText("00000000")
        self.access_password_line_edit.setValidator(QRegularExpressionValidator("^[0-9a-fA-F]{0,8}$"))
        self.access_password_line_edit.textEdited.connect(self.__access_password_line_edit_edited)
        self.access_password_line_edit.editingFinished.connect(self.__access_password_line_edit_finished)

        self.lock_button = QPushButton(str(LockAction.UNLOCK))
        self.lock_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.lock_button.clicked.connect(self.__lock_clicked)
        self.lock_button.setMinimumWidth(120)

        lock_grid_layout = QGridLayout()
        lock_grid_layout.addWidget(lock_memory_bank_label, 0, 0)
        lock_grid_layout.addWidget(self.lock_memory_bank_combo_box, 0, 1)
        lock_grid_layout.addWidget(access_password_label, 0, 2)
        lock_grid_layout.addWidget(self.access_password_line_edit, 0, 3)
        lock_grid_layout.addWidget(QHLine(), 1, 0, 1, 4)
        lock_grid_layout.addWidget(lock_action_label, 2, 0)
        lock_grid_layout.addWidget(self.lock_action_ui_combo_box, 2, 1)
        lock_grid_layout.addWidget(self.permanent_lock_check_box, 2, 2, 1, 2)
        lock_grid_layout.addWidget(self.lock_button, 0, 4, 3, 1)

        lock_group_box.setLayout(lock_grid_layout)

        layout = QVBoxLayout()
        layout.addWidget(lock_group_box)
        layout.setSpacing(0)
        layout.setContentsMargins(1, 1, 1, 1)
        self.setLayout(layout)

        self.reader = reader
        self.lock_thread: LockThread | None = None

    @property
    def is_locking(self) -> bool:
        if self.lock_button.text() == "Stop":
            return True
        return False

    @property
    def lock_memory_bank(self) -> LockMemoryBank:
        return LockMemoryBank.from_index(self.lock_memory_bank_combo_box.currentIndex())

    @property
    def lock_action_ui(self) -> LockActionUi:
        return LockActionUi(self.lock_action_ui_combo_box.currentText())

    @property
    def lock_action(self) -> LockAction:
        lock_action = None
        if self.lock_action_ui == LockActionUi.LOCK:
            if self.permanent_lock_check_box.isChecked():
                lock_action = LockAction.LOCK_PERMANENT
            else:
                lock_action = LockAction.LOCK
        elif self.lock_action_ui == LockActionUi.UNLOCK:
            if self.permanent_lock_check_box.isChecked():
                lock_action = LockAction.UNLOCK_PERMANENT
            else:
                lock_action = LockAction.UNLOCK
        return lock_action

    @property
    def access_password(self) -> bytes:
        return bytearray.fromhex(self.access_password_line_edit.text().replace(' ', ''))

    def __change_lock_text(self) -> None:
        lock_action_ui = LockActionUi(self.lock_action_ui_combo_box.currentText())
        if lock_action_ui == LockActionUi.LOCK:
            self.permanent_lock_check_box.setText("Permanent Lock")
            if self.permanent_lock_check_box.isChecked():
                self.lock_button.setText(str(LockAction.LOCK_PERMANENT))
            else:
                self.lock_button.setText(str(LockAction.LOCK))
        elif lock_action_ui == LockActionUi.UNLOCK:
            self.permanent_lock_check_box.setText("Permanent Unlock")
            if self.permanent_lock_check_box.isChecked():
                self.lock_button.setText(str(LockAction.UNLOCK_PERMANENT))
            else:
                self.lock_button.setText(str(LockAction.UNLOCK))

    def __on_changed_text_lock_action_ui(self, value: str) -> None:
        self.__change_lock_text()

    def __permanent_lock_check_box_clicked(self, value: bool) -> None:
        self.__change_lock_text()

    def __access_password_line_edit_edited(self, text: str) -> None:
        self.access_password_line_edit.setText(text.upper())

    def __access_password_line_edit_finished(self) -> None:
        if len(self.access_password_line_edit.text()) != 8:
            show_message_box("Failed", "Access password must set to 8 hex characters.", success=False)

    def __receive_signal_result_lock(self, response: ResponseLockMemory | Exception) -> None:
        if isinstance(response, ResponseLockMemory):
            pass
        elif isinstance(response, Exception):
            message = str(response)
            if not message:
                message = "Something went wrong, can't lock memory."
            show_message_box("Failed", message)
        else:
            show_message_box("Failed", "Can't lock memory.", success=False)

    def __receive_signal_result_lock_finished(self, responses: list[ResponseLockMemory]) -> None:
        self.__change_lock_text()
        self.is_lock_signal.emit(False)

        for response in responses:
            if response.status not in [Status.SUCCESS, Status.NO_COUNT_LABEL]:
                show_message_box("Failed", f"Can't lock, response status {response.status.name}.")
                return

            if response.lock_memory.tag_status != TagStatus.NO_ERROR:
                show_message_box("Failed", f"Can't lock, response tag status {response.lock_memory.tag_status.name}.")
                return

        tag_statuses = [response.lock_memory.tag_status for response in responses
                        if response.lock_memory is not None
                        and response.lock_memory.tag_status == TagStatus.NO_ERROR]
        if len(tag_statuses) > 0:
            show_message_box("Success", f"{self.lock_action_ui_combo_box.currentText()} memory successfully.",
                             success=True)

    def __lock_clicked(self) -> None:
        try:
            lock_memory_bank = self.lock_memory_bank
            lock_action = self.lock_action
            access_password = self.access_password
        except (AssertionError, ValueError) as e:
            show_message_box("Failed", str(e))
            return

        if not self.is_locking:
            self.lock_button.setText("Stop")
            self.is_lock_signal.emit(True)

            self.lock_thread = LockThread(self.reader)
            self.lock_thread.lock_memory_bank = lock_memory_bank
            self.lock_thread.lock_action = lock_action
            self.lock_thread.access_password = access_password
            self.lock_thread.result_lock_signal.connect(self.__receive_signal_result_lock)
            self.lock_thread.result_lock_finished_signal.connect(self.__receive_signal_result_lock_finished)
            self.lock_thread.start()
        else:
            self.lock_thread.request_stop = True
