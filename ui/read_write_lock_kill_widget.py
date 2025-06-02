from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableView, QHBoxLayout, QComboBox, QPushButton, QLabel

from rfid.reader import Reader
from rfid.reader_settings import WorkMode
from rfid.response import Response
from rfid.status import Status
from rfid.tag import Tag
from rfid.utils import hex_readable
from ui.kill_widget import KillWidget
from ui.lock_widget import LockWidget
from ui.message_stack_widget import MessageStackWidget
from ui.thread.read_write_thread import SetFilterThread
from ui.read_write_widget import ReadWriteWidget, ReadMemoryItemModel
from ui.utils import show_message_box


NO_FILTER_ITEM = "-- No filter --"


class ReadWriteLockKillWidget(QWidget):
    is_read_write_lock_kill_signal = Signal(bool)

    def __init__(self, reader: Reader) -> None:
        super().__init__()

        self.reader = reader
        self.__selected_filter_text = NO_FILTER_ITEM
        self.set_filter_thread: SetFilterThread | None = None

        filter_label = QLabel("Filter")
        filter_label.setMaximumWidth(50)

        self.filter_combo_box = QComboBox()
        self.filter_combo_box.addItem(NO_FILTER_ITEM)
        self.set_filter_button = QPushButton("Set filter")
        self.set_filter_button.setMaximumWidth(100)
        self.set_filter_button.clicked.connect(self.__set_filter_clicked)

        self.read_write_table_view = QTableView()
        self.read_memory_item_model = ReadMemoryItemModel()
        self.read_write_table_view.setModel(self.read_memory_item_model)
        self.read_write_table_view.setMaximumHeight(120)
        # PC, CRC, EPC, Data length, Data, Antenna, Count
        self.read_write_table_view.setColumnWidth(0, 60)
        self.read_write_table_view.setColumnWidth(1, 60)
        self.read_write_table_view.setColumnWidth(2, 240)
        self.read_write_table_view.setColumnWidth(3, 80)
        self.read_write_table_view.setColumnWidth(4, 240)
        self.read_write_table_view.setColumnWidth(5, 60)
        self.read_write_table_view.setColumnWidth(6, 30)
        self.read_write_table_view.horizontalHeader().setStretchLastSection(True)
        self.read_write_table_view.verticalHeader().setDefaultSectionSize(10)

        filter_h_layout = QHBoxLayout()
        filter_h_layout.addWidget(filter_label, 1)
        filter_h_layout.addWidget(self.filter_combo_box, 2)
        filter_h_layout.addWidget(self.set_filter_button, 1)
        filter_h_layout.addWidget(QLabel(), 2)

        self.read_write_widget = ReadWriteWidget(reader, self.read_memory_item_model)
        self.read_write_widget.is_read_write_signal.connect(self.__receive_signal_is_read_write)
        self.lock_widget = LockWidget(reader)
        self.lock_widget.is_lock_signal.connect(self.__receive_signal_is_lock)
        self.kill_widget = KillWidget(reader)
        self.kill_widget.is_kill_signal.connect(self.__receive_signal_is_kill)

        h_layout = QHBoxLayout()
        h_layout.addWidget(self.lock_widget)
        h_layout.addWidget(self.kill_widget)

        v_layout = QVBoxLayout()
        v_layout.addLayout(filter_h_layout)
        v_layout.addWidget(self.read_write_widget)
        v_layout.addLayout(h_layout)
        v_layout.addWidget(self.read_write_table_view)
        self.setLayout(v_layout)

        # Message disabled when on active mode
        self.message_stack_active_mode = MessageStackWidget(self, "When reader on Active Mode/Trigger Mode,\n"
                                                                  "you can't read/write to specific memory.\n"
                                                                  "Try change to Answer Mode.")

    def resizeEvent(self, event):
        self.message_stack_active_mode.resize(event.size())
        event.accept()

    def close(self) -> None:
        if self.set_filter_thread:
            self.set_filter_thread.terminate()
        self.read_write_widget.close()
        self.lock_widget.close()
        self.kill_widget.close()

    def receive_signal_tags(self, tags: list[Tag]) -> None:
        current_tag_combo_box = self.filter_combo_box.currentText()
        tags_str: list[str] = []
        tags_str.extend([hex_readable(tag.data) for tag in tags])

        self.filter_combo_box.clear()
        self.filter_combo_box.addItem(NO_FILTER_ITEM)
        self.filter_combo_box.addItems(tags_str)

        if current_tag_combo_box != NO_FILTER_ITEM and current_tag_combo_box in tags_str:
            self.filter_combo_box.setCurrentText(current_tag_combo_box)

    def receive_work_mode_signal(self, work_mode: WorkMode) -> None:
        if work_mode in [WorkMode.ACTIVE_MODE, WorkMode.TRIGGER_MODE]:
            self.message_stack_active_mode.show()
        else:
            self.message_stack_active_mode.hide()

    def __set_filter_clicked(self) -> None:
        self.set_filter_button.setEnabled(False)
        self.set_filter_thread = SetFilterThread(self.reader)
        self.set_filter_thread.result_set_signal.connect(self.__receive_signal_set_filter)

        mask: bytes = bytes()
        if self.filter_combo_box.currentText() != NO_FILTER_ITEM:
            epc_str = self.filter_combo_box.currentText().replace(' ', '')
            mask = bytearray.fromhex(epc_str)
        self.set_filter_thread.mask = mask
        self.set_filter_thread.start()

    def __receive_signal_set_filter(self, response: Response | Exception) -> None:
        self.set_filter_button.setEnabled(True)
        if isinstance(response, Response):
            if response.status == Status.SUCCESS:
                show_message_box("Success", "Successful set filter.", success=True)
            else:
                show_message_box("Failed", "Failed set filter.", success=False)
        elif isinstance(response, Exception):
            message = str(response)
            if not message:
                message = "Something went wrong, can't set filter."
            show_message_box("Failed", message)
        else:
            show_message_box("Failed", "Can't set filter.", success=False)

    def __receive_signal_is_read_write(self, value: bool) -> None:
        self.is_read_write_lock_kill_signal.emit(value)

        # Disabled Lock & Kill button
        self.lock_widget.lock_button.setDisabled(value)
        self.kill_widget.kill_button.setDisabled(value)

    def __receive_signal_is_lock(self, value: bool) -> None:
        self.is_read_write_lock_kill_signal.emit(value)

        # Disabled Read/Write & Kill button
        self.read_write_widget.read_button.setDisabled(value)
        self.read_write_widget.write_button.setDisabled(value)
        self.kill_widget.kill_button.setDisabled(value)

    def __receive_signal_is_kill(self, value: bool) -> None:
        self.is_read_write_lock_kill_signal.emit(value)

        # Disabled Read/Write & Lock button
        self.read_write_widget.read_button.setDisabled(value)
        self.read_write_widget.write_button.setDisabled(value)
        self.lock_widget.lock_button.setDisabled(value)
