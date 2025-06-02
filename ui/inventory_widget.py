from typing import Any, Union
from PySide6.QtCore import Qt, QModelIndex, QPersistentModelIndex, QAbstractTableModel, Signal
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import QWidget, QLabel, QComboBox, QSpinBox, QPushButton, QTableView, QHeaderView, \
    QHBoxLayout, QVBoxLayout
from rfid.reader import Reader
from rfid.reader_settings import StopAfter, WorkMode, AnswerModeInventoryParameter, DeviceInfo
from rfid.tag import Tag
from rfid.utils import hex_readable, calculate_rssi
from ui.thread.inventory_thread import InventoryThread
from datetime import datetime  # Tambahkan ini di bagian import
import sqlite3
from threading import Timer

COLUMNS = ["Data", "Count", "RSSI", "Channel", "Timestamp"]

class InventoryWidget(QWidget):
    is_inventory_signal = Signal(bool)
    tags_signal = Signal(list)

    def __init__(self, reader: Reader) -> None:
        super().__init__()

        self.reader: Reader = reader
        self.__work_mode: WorkMode = WorkMode.ANSWER_MODE
        self.__device_info: DeviceInfo | None = None
        self.inventory_thread: InventoryThread = InventoryThread(self.reader)
        self.inventory_thread.result_tag_signal.connect(self.__receive_signal_result_tag)
        self.inventory_thread.result_finished_signal.connect(self.__receive_signal_result_finished)
        self.inventory_thread.start()

        self.stop_after_label = QLabel("Stop after")
        self.stop_after_label.setFixedWidth(60)

        self.stop_after_combo_box = QComboBox()
        self.stop_after_combo_box.setMaximumWidth(100)
        self.stop_after_combo_box.addItems([str(stop_after) for stop_after in StopAfter])
        self.stop_after_combo_box.currentIndexChanged.connect(self.__on_changed_index_stop_after)
        self.param_spin_box = QSpinBox()
        self.param_spin_box.setRange(0x00, 0xFFFF)  # 0 - 65.535
        self.param_spin_box.setMaximumWidth(60)
        self.param_spin_box.setValue(0)
        self.param_unit_label = QLabel(StopAfter.TIME.unit)
        self.param_unit_label.setMaximumWidth(60)

        self.start_stop_button = QPushButton("Start")
        self.start_stop_button.clicked.connect(self.__start_stop_clicked)
        self.start_stop_button.setMaximumWidth(200)
        self.start_stop_button.setMinimumHeight(32)

        self.inventory_table_view = QTableView()
        self.tag_item_model = InventoryTagItemModel(self)
        self.inventory_table_view.setModel(self.tag_item_model)
        self.inventory_table_view.setColumnWidth(0, 420)
        self.inventory_table_view.setColumnWidth(1, 100)
        self.inventory_table_view.setColumnWidth(2, 100)
        self.inventory_table_view.setColumnWidth(3, 100)
        self.inventory_table_view.horizontalHeader().setStretchLastSection(True)
        self.inventory_table_view.verticalHeader().setDefaultSectionSize(10)

        h_layout = QHBoxLayout()
        h_layout.addWidget(self.start_stop_button)
        h_layout.addWidget(self.stop_after_label)
        h_layout.addWidget(self.stop_after_combo_box)
        h_layout.addWidget(self.param_spin_box)
        h_layout.addWidget(self.param_unit_label)
        h_layout.addWidget(QLabel())

        v_layout = QVBoxLayout()
        v_layout.addLayout(h_layout)
        v_layout.addWidget(self.inventory_table_view)
        self.setLayout(v_layout)

        self.stop_after_combo_box.setCurrentIndex(StopAfter.TIME.value)
        self.database_pooler = DatabasePooler(self.tag_item_model)
        self.database_pooler.start()

    def close(self) -> None:
        self.database_pooler.stop()  # Hentikan pooler
        self.inventory_thread.terminate()

    def __on_changed_index_stop_after(self, index: int) -> None:
        stop_after = StopAfter(index)
        self.param_unit_label.setText(stop_after.unit)

    def receive_device_info_signal(self, device_info: DeviceInfo) -> None:
        self.device_info = device_info

    @property
    def device_info(self) -> DeviceInfo | None:
        return self.__device_info

    @device_info.setter
    def device_info(self, value: DeviceInfo) -> None:
        self.__device_info = value

    def receive_work_mode_signal(self, work_mode: WorkMode) -> None:
        self.work_mode = work_mode

    @property
    def work_mode(self) -> WorkMode:
        return self.__work_mode

    @work_mode.setter
    def work_mode(self, value: WorkMode) -> None:
        self.__work_mode = value

        visible_answer_mode_parameters = self.__work_mode == WorkMode.ANSWER_MODE

        self.stop_after_label.setVisible(visible_answer_mode_parameters)
        self.stop_after_combo_box.setVisible(visible_answer_mode_parameters)
        self.param_spin_box.setVisible(visible_answer_mode_parameters)
        self.param_unit_label.setVisible(visible_answer_mode_parameters)

        if visible_answer_mode_parameters and not self.__device_info.series.enabled_stop_after_by_cycles:
            self.stop_after_combo_box.setVisible(False)
            self.stop_after_combo_box.setCurrentIndex(StopAfter.TIME.value)

    @property
    def stop_after(self) -> StopAfter:
        return StopAfter(self.stop_after_combo_box.currentIndex())

    @property
    def is_inventory(self) -> bool:
        if self.start_stop_button.text() == "Start":
            return False
        return True

    def stop_inventory(self) -> None:
        self.inventory_thread.request_stop = True

    def start_inventory(self) -> None:
        self.is_inventory_signal.emit(True)
        self.start_stop_button.setText("Stop")

        self.tag_item_model.clear()

        if self.work_mode == WorkMode.ANSWER_MODE:
            answer_mode_inventory_parameter = AnswerModeInventoryParameter(
                stop_after=self.stop_after, value=self.param_spin_box.value())
            self.inventory_thread.answer_mode_inventory_parameter = answer_mode_inventory_parameter
        else:
            self.inventory_thread.answer_mode_inventory_parameter = None
        self.inventory_thread.work_mode = self.work_mode
        self.inventory_thread.request_start = True

    def __start_stop_clicked(self) -> None:
        if self.is_inventory:
            self.stop_inventory()
        else:
            self.start_inventory()

    def __receive_signal_result_tag(self, tag: Tag) -> None:
        def find_tag_index(t) -> int:
            find_tag = [ta for ta in self.tag_item_model.tags if ta.data == t.data]
            if len(find_tag) > 0:
                return self.tag_item_model.tags.index(find_tag[0])
            return -1

        index_tag = find_tag_index(tag)
        if index_tag < 0:  # Insert tag
            self.tag_item_model.insert(tag)
        else:  # Update tag
            tag.count = self.tag_item_model.tags[index_tag].count + 1
            self.tag_item_model.update(tag)

    def __receive_signal_result_finished(self, value: bool) -> None:
        if not self.is_inventory:
            return
        self.tags_signal.emit(self.tag_item_model.tags)
        self.start_stop_button.setText("Start")

        self.is_inventory_signal.emit(False)


class InventoryTagItemModel(QAbstractTableModel):

    def __init__(self, parent: InventoryWidget) -> None:
        super().__init__()
        self.parent = parent
        self.tags: list[Tag] = []

    def rowCount(self, parent: Union[QModelIndex, QPersistentModelIndex] = QModelIndex) -> int:
        return len(self.tags)

    def columnCount(self, parent: Union[QModelIndex, QPersistentModelIndex] = QModelIndex) -> int:
        return len(COLUMNS)

    def data(self, index: Union[QModelIndex, QPersistentModelIndex], role: int = Qt.DisplayRole) -> Any:
        if role == Qt.DisplayRole:
            tag = self.tags[index.row()]
            if index.column() == 0:  # EPC
                return hex_readable(tag.data)
            elif index.column() == 1:  # Count
                return tag.count
            elif index.column() == 2:  # RSSI
                return str(calculate_rssi(tag.rssi))[0:3]
            elif index.column() == 3:  # Channel
                return tag.channel
            elif index.column() == 4:  # Timestamp
                return tag.timestamp  # Ambil timestamp

        if role == Qt.BackgroundRole:
            if index.row() % 2 == 0:
                bg_brush = QBrush()
                bg_brush.setColor(QColor.fromRgb(216, 216, 216))
                bg_brush.setStyle(Qt.SolidPattern)
                return bg_brush

    def insert(self, tag: Tag) -> None:
        tag.timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]  # Tambahkan timestamp
        row_count = len(self.tags)
        self.beginInsertRows(QModelIndex(), row_count, row_count)
        self.tags.append(tag)
        row_count += 1
        self.endInsertRows()

    def remove(self, index: int) -> None:
        row_count = self.rowCount()
        row_count -= 1
        self.beginRemoveRows(QModelIndex(), row_count, row_count)
        self.tags.pop(index)
        self.endRemoveRows()

    def clear(self) -> None:
        self.tags.clear()
        self.layoutChanged.emit()

    def update(self, tag: Tag) -> None:
        find_tag = [t for t in self.tags if t.data == tag.data]
        find_tag = find_tag[0]
        find_tag.count = tag.count
        find_tag.rssi = tag.rssi
        find_tag.channel = tag.channel
        find_tag.antenna = tag.antenna
        index = self.tags.index(find_tag)
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


class DatabasePooler:
    def __init__(self, model: InventoryTagItemModel, interval: int = 3):
        self.model = model
        self.interval = interval
        self.timer = None

    def create_table(self):
        connection = sqlite3.connect("inventory.db", check_same_thread=False, timeout=10)
        cursor = connection.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            epc TEXT PRIMARY KEY,
            timestamp TEXT
        )
        """)
        # NEW
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_epc ON inventory (epc);
        """)
        connection.commit()
        connection.close()

    def start(self):
        self.timer = Timer(self.interval, self.send_data)
        self.timer.start()

    def stop(self):
        if self.timer:
            self.timer.cancel()

    def send_data(self):
        tags_to_send = self.model.tags.copy()  # Salin data dari model

        # NEW
        # try:
        #     connection = sqlite3.connect("inventory.db", check_same_thread=False, timeout=10)
        #     cursor = connection.cursor()

        #     # Batch insert
        #     cursor.executemany("""
        #     INSERT INTO inventory (epc, timestamp)
        #     VALUES (?, ?)
        #     """, [(str(hex_readable(tag.data)).replace(" ", ""), tag.timestamp) for tag in tags_to_send])
        #     connection.commit()
        #     connection.close()

        #     # Hapus semua dari model jika berhasil
        #     self.model.tags.clear()
        # except sqlite3.OperationalError as e:
        #     print(f"Error saving tags to database: {e}")

        for tag in tags_to_send:
            try:
                connection = sqlite3.connect("inventory.db", check_same_thread=False, timeout=10)
                cursor = connection.cursor()
                cursor.execute("""
                INSERT INTO inventory (epc, timestamp)
                VALUES (?, ?)
                """, (str(hex_readable(tag.data)).replace(" ", ""), tag.timestamp))
                connection.commit()
                connection.close()  

                # Hapus dari model jika berhasil
                index = self.model.tags.index(tag)
                self.model.remove(index)
            except Exception as e:
                print(f"Error saving tag {tag.data} to database: {e}")

        # Jalankan ulang pengiriman
        self.start()