from typing import Any, Union
from PySide6.QtCore import Qt, QModelIndex, QPersistentModelIndex, QAbstractTableModel, Signal
from PySide6.QtGui import QColor, QBrush, QRegularExpressionValidator
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QGridLayout, QComboBox, QSpinBox, QLineEdit, QVBoxLayout, \
    QSizePolicy, QHBoxLayout, QGroupBox

from rfid.read_write import ReadMemory
from rfid.reader import Reader
from rfid.reader_settings import MemoryBank
from rfid.response import Status, ResponseReadMemory, ResponseWriteMemory
from rfid.status import TagStatus
from rfid.utils import hex_readable
from ui.thread.read_write_thread import ReadThread, WriteThread
from ui.utils import show_message_box


COLUMNS = ["PC", "CRC", "EPC", "Data length", "Data", "Antenna", "Count"]


class ReadMemoryItemModel(QAbstractTableModel):
    def __init__(self) -> None:
        super().__init__()
        self.read_memories: list[ReadMemory] = []

    def rowCount(self, parent: Union[QModelIndex, QPersistentModelIndex] = QModelIndex) -> int:
        return len(self.read_memories)

    def columnCount(self, parent: Union[QModelIndex, QPersistentModelIndex] = QModelIndex) -> int:
        return len(COLUMNS)

    def data(self, index: Union[QModelIndex, QPersistentModelIndex], role: int = Qt.DisplayRole) -> Any:
        if role == Qt.DisplayRole:
            read_memory = self.read_memories[index.row()]
            if index.column() == 0:  # PC
                return hex_readable(read_memory.pc)
            elif index.column() == 1:  # CRC
                return hex_readable(read_memory.crc)
            elif index.column() == 2:  # EPC
                return hex_readable(read_memory.epc)
            elif index.column() == 3:  # Data length
                return read_memory.data_word_length
            elif index.column() == 4:  # Data
                return hex_readable(read_memory.data)
            elif index.column() == 5:  # Antenna
                return read_memory.antenna
            elif index.column() == 6:  # Count
                return read_memory.count

        if role == Qt.BackgroundRole:
            if index.row() % 2 == 0:
                bg_brush = QBrush()
                bg_brush.setColor(QColor.fromRgb(216, 216, 216))
                bg_brush.setStyle(Qt.SolidPattern)
                return bg_brush

    def insert(self, read_memory: ReadMemory) -> None:
        row_count = len(self.read_memories)
        self.beginInsertRows(QModelIndex(), row_count, row_count)
        self.read_memories.append(read_memory)
        row_count += 1
        self.endInsertRows()

    def remove(self, index: int) -> None:
        row_count = self.rowCount()
        row_count -= 1
        self.beginRemoveRows(QModelIndex(), row_count, row_count)
        self.read_memories.pop(index)
        self.endRemoveRows()

    def clear(self) -> None:
        self.read_memories.clear()
        self.layoutChanged.emit()

    def update(self, read_memory: ReadMemory) -> None:
        find_read_memory = [t for t in self.read_memories if t.epc == read_memory.epc]
        find_read_memory = find_read_memory[0]
        find_read_memory.count = read_memory.count
        find_read_memory.pc = read_memory.pc
        find_read_memory.crc = read_memory.crc
        find_read_memory.antenna = read_memory.antenna
        find_read_memory.epc_length = read_memory.epc_length
        find_read_memory.data_word_length = read_memory.data_word_length
        find_read_memory.data = read_memory.data
        index = self.read_memories.index(find_read_memory)
        for i, column in enumerate(COLUMNS):
            create_index = self.createIndex(index, i)
            self.dataChanged.emit(create_index, create_index, Qt.DisplayRole)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return COLUMNS[section]
            elif orientation == Qt.Vertical:
                return section + 1
        return None


class ReadWriteWidget(QWidget):
    is_read_write_signal = Signal(bool)

    def __init__(self, reader: Reader, read_memory_item_model: ReadMemoryItemModel) -> None:
        super().__init__()

        self.reader = reader
        self.read_memory_item_model = read_memory_item_model
        self.read_thread: ReadThread | None = None
        self.write_thread: WriteThread | None = None

        # GroupBox Lock
        read_write_group_box = QGroupBox("Read/write memory")
        memory_bank_label = QLabel("Memory bank")
        memory_bank_label.setMinimumWidth(60)
        access_password_label = QLabel("Access password")
        access_password_label.setMinimumWidth(60)
        start_address_label = QLabel("Start address")
        start_address_label.setMinimumWidth(60)
        length_label = QLabel("Length")
        length_label.setMinimumWidth(60)
        data_label = QLabel("Data to write")
        data_label.setMinimumWidth(60)

        word_start_address_label = QLabel("word")
        word_start_address_label.setMinimumWidth(40)
        word_length_label = QLabel("word")
        word_length_label.setMinimumWidth(40)

        self.memory_bank_combo_box = QComboBox()
        self.memory_bank_combo_box.addItems([str(memory_bank) for memory_bank in MemoryBank])
        self.memory_bank_combo_box.setCurrentIndex(MemoryBank.EPC.value)
        self.memory_bank_combo_box.setMinimumWidth(100)
        self.access_password_line_edit = QLineEdit()
        self.access_password_line_edit.setMaxLength(8)
        self.access_password_line_edit.setText("00000000")
        self.access_password_line_edit.setValidator(QRegularExpressionValidator("^[0-9a-fA-F]{0,8}$"))
        self.access_password_line_edit.textEdited.connect(self.__access_password_line_edit_edited)
        self.access_password_line_edit.editingFinished.connect(self.__access_password_line_edit_finished)
        self.data_line_edit = QLineEdit()
        self.data_line_edit.setValidator(QRegularExpressionValidator("^[0-9a-fA-F]+"))
        self.data_line_edit.textEdited.connect(self.data_line_edit_edited)

        self.start_address_spin_box = QSpinBox()
        self.start_address_spin_box.setValue(2)
        self.start_address_spin_box.setMinimumWidth(100)
        self.start_address_spin_box.setRange(0, 65535)
        self.length_spin_box = QSpinBox()
        self.length_spin_box.setRange(1, 255)
        self.length_spin_box.setMinimumWidth(100)

        self.read_button = QPushButton("Read")
        self.read_button.clicked.connect(self.__read_clicked)
        self.read_button.setMinimumWidth(120)
        self.read_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.write_button = QPushButton("Write")
        self.write_button.clicked.connect(self.__write_clicked)
        self.write_button.setMinimumWidth(120)
        self.write_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        h_start_address_layout = QHBoxLayout()
        h_start_address_layout.addWidget(self.start_address_spin_box)
        h_start_address_layout.addWidget(word_start_address_label)
        h_length_layout = QHBoxLayout()
        h_length_layout.addWidget(self.length_spin_box)
        h_length_layout.addWidget(word_length_label)

        read_write_grid_layout = QGridLayout()

        read_write_grid_layout.addWidget(memory_bank_label, 0, 0)
        read_write_grid_layout.addWidget(self.memory_bank_combo_box, 0, 1)
        read_write_grid_layout.addWidget(access_password_label, 0, 2)
        read_write_grid_layout.addWidget(self.access_password_line_edit, 0, 3)
        read_write_grid_layout.addWidget(start_address_label, 1, 0)
        read_write_grid_layout.addLayout(h_start_address_layout, 1, 1)
        read_write_grid_layout.addWidget(length_label, 1, 2)
        read_write_grid_layout.addLayout(h_length_layout, 1, 3)
        read_write_grid_layout.addWidget(self.read_button, 1, 4, 2, 1)
        read_write_grid_layout.addWidget(self.write_button, 1, 5, 2, 1)
        read_write_grid_layout.addWidget(data_label, 2, 0)
        read_write_grid_layout.addWidget(self.data_line_edit, 2, 1, 1, 3)

        read_write_group_box.setLayout(read_write_grid_layout)

        layout = QVBoxLayout()
        layout.addWidget(read_write_group_box)
        layout.setSpacing(0)
        layout.setContentsMargins(1, 1, 1, 1)
        self.setLayout(layout)

    def close(self) -> None:
        if self.read_thread:
            self.read_thread.terminate()
        if self.write_thread:
            self.write_thread.terminate()

    @property
    def is_reading(self) -> bool:
        if self.read_button.text() == "Read":
            return False
        return True

    @property
    def is_writing(self) -> bool:
        if self.write_button.text() == "Write":
            return False
        return True

    @property
    def memory_bank(self) -> MemoryBank:
        return MemoryBank(self.memory_bank_combo_box.currentIndex())

    @property
    def start_address(self) -> bytes:
        return self.start_address_spin_box.value()

    @property
    def length(self) -> int:
        return self.length_spin_box.value()

    @property
    def access_password(self) -> bytes:
        return bytearray.fromhex(self.access_password_line_edit.text().replace(' ', ''))

    @property
    def data(self) -> bytes:
        return bytearray.fromhex(self.data_line_edit.text().replace(' ', ''))

    def __access_password_line_edit_edited(self, text: str) -> None:
        self.access_password_line_edit.setText(text.upper())

    def __access_password_line_edit_finished(self) -> None:
        if len(self.access_password_line_edit.text()) != 8:
            show_message_box("Failed", "Access password must set to 8 hex characters.", success=False)

    def data_line_edit_edited(self, text: str) -> None:
        text = text.upper().replace(' ', '')
        self.data_line_edit.setText(' '.join([text[i:i + 2] for i in range(0, len(text), 2)]).strip())

    def __read_clicked(self) -> None:
        if not self.is_reading:
            self.read_button.setText("Stop")
            self.is_read_write_signal.emit(True)
            self.write_button.setDisabled(True)

            self.read_memory_item_model.clear()

            self.read_thread = ReadThread(self.reader)
            self.read_thread.result_read_signal.connect(self.__receive_signal_result_read)
            self.read_thread.result_read_finished_signal.connect(self.__receive_signal_result_read_finished)
            self.read_thread.request_stop = False
            self.read_thread.memory_bank = self.memory_bank
            self.read_thread.start_address = self.start_address
            self.read_thread.length = self.length
            self.read_thread.access_password = self.access_password
            self.read_thread.start()
        else:
            self.read_thread.request_stop = True

    def __receive_signal_result_read(self, response_read_memory: ResponseReadMemory | Exception) -> None:
        def find_read_memory_index(t) -> int:
            find_tag = [ta for ta in self.read_memory_item_model.read_memories if ta.epc == t.epc]
            if len(find_tag) > 0:
                return self.read_memory_item_model.read_memories.index(find_tag[0])
            return -1

        if isinstance(response_read_memory, Exception):
            message = str(response_read_memory)
            if not message:
                message = "Something went wrong, can't read."
            show_message_box("Failed", message)
            return

        if response_read_memory.status != Status.SUCCESS:
            return

        # If success, update table
        read_memory = response_read_memory.read_memory

        index_read_memory = find_read_memory_index(read_memory)
        if index_read_memory < 0:  # Insert read_memory
            self.read_memory_item_model.insert(read_memory)
        else:  # Update read_memory
            read_memory.count = self.read_memory_item_model.read_memories[index_read_memory].count + 1
            self.read_memory_item_model.update(read_memory)

    def __receive_signal_result_read_finished(self, responses: list[ResponseReadMemory]) -> None:
        self.read_button.setText("Read")
        self.is_read_write_signal.emit(False)
        self.write_button.setDisabled(False)

        for response in responses:
            if response.status not in [Status.SUCCESS, Status.NO_COUNT_LABEL]:
                show_message_box("Failed", f"Can't read, response status {response.status.name}")
                return

            if response.read_memory.tag_status != TagStatus.NO_ERROR:
                show_message_box("Failed", f"Can't read, response tag status {response.read_memory.tag_status.name}")
                return

    def __write_clicked(self) -> None:
        if len(self.data_line_edit.text().replace(' ', '').strip()) <= 0:
            show_message_box("Failed", "There is no data to write.", success=False)
            return

        if len(self.data_line_edit.text().replace(' ', '').strip()) % 2 != 0:
            show_message_box("Failed", "Data length must be even number.", success=False)
            return

        if not self.is_writing:
            self.write_button.setText("Stop")
            self.is_read_write_signal.emit(True)
            self.read_button.setDisabled(True)

            self.write_thread = WriteThread(self.reader)
            self.write_thread.result_write_signal.connect(self.__receive_signal_result_write)
            self.write_thread.result_write_finished_signal.connect(self.__receive_signal_result_write_finished)
            self.write_thread.request_stop = False
            self.write_thread.memory_bank = self.memory_bank
            self.write_thread.start_address = self.start_address
            self.write_thread.length = self.length
            self.write_thread.access_password = self.access_password
            self.write_thread.data = self.data
            self.write_thread.start()
        else:
            self.write_thread.request_stop = True

    def __receive_signal_result_write(self, response_write_memory: ResponseWriteMemory | Exception) -> None:
        if isinstance(response_write_memory, Exception):
            message = str(response_write_memory)
            if not message:
                message = "Something went wrong, can't write."
            show_message_box("Failed", message)
            return

        if response_write_memory.status != Status.SUCCESS:
            return

    def __receive_signal_result_write_finished(self, responses: list[ResponseWriteMemory]) -> None:
        self.write_button.setText("Write")
        self.is_read_write_signal.emit(False)
        self.read_button.setDisabled(False)

        for response in responses:
            if response.status not in [Status.SUCCESS, Status.NO_COUNT_LABEL]:
                show_message_box("Failed", f"Can't write, response status {response.status.name}.")
                return

            if response.write_memory.tag_status != TagStatus.NO_ERROR:
                show_message_box("Failed", f"Can't write, response tag status {response.write_memory.tag_status.name}.")
                return

        tag_statuses = [response.write_memory.tag_status for response in responses
                        if response.write_memory is not None
                        and response.write_memory.tag_status == TagStatus.NO_ERROR]
        if len(tag_statuses) > 0:
            show_message_box("Success", "Write successfully.", success=True)
