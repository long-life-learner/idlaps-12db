from typing import Any, Union
from unittest import result
from PySide6.QtCore import (
    Qt,
    QModelIndex,
    QPersistentModelIndex,
    QAbstractTableModel,
    Signal,
)
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QComboBox,
    QSpinBox,
    QPushButton,
    QTableView,
    QHeaderView,
    QHBoxLayout,
    QVBoxLayout,
)
from rfid.reader import Reader
from rfid.reader_settings import (
    StopAfter,
    WorkMode,
    AnswerModeInventoryParameter,
    DeviceInfo,
)
from rfid.tag import Tag
from rfid.utils import hex_readable, calculate_rssi
from ui.thread.inventory_thread import InventoryThread
from ui.utils import get_db_path
import sqlite3
from threading import Timer
import threading
import os
from datetime import datetime, timedelta


COLUMNS = ["Data", "Count", "RSSI", "Channel", "Timestamp"]


class InventoryWidget(QWidget):
    is_inventory_signal = Signal(bool)
    tags_signal = Signal(list)

    def __init__(self, reader: Reader, reader_id: str = None, time_offset: float = 0.0) -> None:
        super().__init__()
        
        self.reader: Reader = reader
        self.time_offset = time_offset
        self.__work_mode: WorkMode = WorkMode.ANSWER_MODE
        self.__device_info: DeviceInfo | None = None
        self.inventory_thread: InventoryThread = InventoryThread(self.reader)
        self.inventory_thread.result_tag_signal.connect(
            self.__receive_signal_result_tag
        )
        self.inventory_thread.result_finished_signal.connect(
            self.__receive_signal_result_finished
        )
        self.inventory_thread.start()

        self.stop_after_label = QLabel("Stop after")
        self.stop_after_label.setFixedWidth(60)

        self.stop_after_combo_box = QComboBox()
        self.stop_after_combo_box.setMaximumWidth(100)
        self.stop_after_combo_box.addItems(
            [str(stop_after) for stop_after in StopAfter]
        )
        self.stop_after_combo_box.currentIndexChanged.connect(
            self.__on_changed_index_stop_after
        )
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

        # Widget allowed_minutes telah dihapus sesuai instruksi

        # Indikator Unsynced Data In Wait
        self.unsynced_label = QLabel("🟢 Data in Wait: 0")
        self.unsynced_label.setStyleSheet("font-weight: bold; color: #a6e3a1; padding-left: 15px;")

        h_layout = QHBoxLayout()
        h_layout.addWidget(self.start_stop_button)
        h_layout.addWidget(self.stop_after_label)
        h_layout.addWidget(self.stop_after_combo_box)
        h_layout.addWidget(self.param_spin_box)
        h_layout.addWidget(self.param_unit_label)
        h_layout.addWidget(self.unsynced_label)
        h_layout.addWidget(QLabel())

        v_layout = QVBoxLayout()
        v_layout.addLayout(h_layout)
        v_layout.addWidget(self.inventory_table_view)
        self.setLayout(v_layout)

        self.stop_after_combo_box.setCurrentIndex(StopAfter.TIME.value)
        self.reader_id = reader_id
        self.database_pooler = create_database_pooler(self.tag_item_model, reader_id=self.reader_id)
        self.database_pooler.start()



    def update_unsynced_count(self, count: int) -> None:
        if count > 0:
            self.unsynced_label.setText(f"🟡 Data in Wait: {count}")
            self.unsynced_label.setStyleSheet("font-weight: bold; color: #fab387; padding-left: 15px;")
        else:
            self.unsynced_label.setText("🟢 Data in Wait: 0")
            self.unsynced_label.setStyleSheet("font-weight: bold; color: #a6e3a1; padding-left: 15px;")

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

        if (
            visible_answer_mode_parameters
            and not self.__device_info.series.enabled_stop_after_by_cycles
        ):
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
        self.database_pooler.stop()  # Hentikan pooler

    def start_inventory(self) -> None:
        self.is_inventory_signal.emit(True)
        self.start_stop_button.setText("Stop")

        self.tag_item_model.clear()

        if self.work_mode == WorkMode.ANSWER_MODE:
            answer_mode_inventory_parameter = AnswerModeInventoryParameter(
                stop_after=self.stop_after, value=self.param_spin_box.value()
            )
            self.inventory_thread.answer_mode_inventory_parameter = (
                answer_mode_inventory_parameter
            )
        else:
            self.inventory_thread.answer_mode_inventory_parameter = None
        self.inventory_thread.work_mode = self.work_mode
        
        self.database_pooler.start()  # Mulai sinkronisasi DB lagi
        self.inventory_thread.request_start = True

    def start_inventory_all_readers(self):
        self.tag_item_model.clear()  # Bersihkan data lama
        self.inventory_threads = []

        for reader in self.readers:
            inventory_thread = InventoryThread(reader)

            if self.work_mode == WorkMode.ANSWER_MODE:
                answer_mode_inventory_parameter = AnswerModeInventoryParameter(
                    stop_after=self.stop_after, value=self.param_spin_box.value()
                )
                inventory_thread.answer_mode_inventory_parameter = (
                    answer_mode_inventory_parameter
                )
            else:
                inventory_thread.answer_mode_inventory_parameter = None

            inventory_thread.work_mode = self.work_mode
            inventory_thread.request_start = True

            # Koneksikan sinyal untuk menangani hasil tag yang ditemukan
            inventory_thread.result_tag_signal.connect(
                self.on_tag_found
            )  # Buat/ubah fungsi ini
            inventory_thread.result_finished_signal.connect(self.on_inventory_finished)

            inventory_thread.start()
            self.inventory_threads.append(inventory_thread)

        self.is_inventory_signal.emit(True)
        self.start_stop_button.setText("Stop")

    def stop_inventory_all_readers(self):
        for thread in self.inventory_threads:
            thread.request_stop = True

        self.is_inventory_signal.emit(False)
        self.start_stop_button.setText("Start")

    def __start_stop_clicked(self) -> None:
        if self.is_inventory:
            self.stop_inventory()
        else:
            self.start_inventory()
        # if self.is_inventory:
        #     self.stop_inventory_all_readers()
        # else:
        #     self.start_inventory_all_readers()

    def __receive_signal_result_tag(self, tag: Tag) -> None:
        def find_tag_index(t) -> int:
            find_tag = [ta for ta in self.tag_item_model.tags if ta.data == t.data]
            if len(find_tag) > 0:
                return self.tag_item_model.tags.index(find_tag[0])
            return -1

        # 1. Berikan timestamp yang disinkronkan dengan NTP Offset Server IDLAPS
        server_datetime = datetime.now() + timedelta(seconds=self.time_offset)
        tag.timestamp = server_datetime.strftime("%H:%M:%S.%f")[:-3]
        
        # 2. Simpan raw read ke buffer memory SQLite (Untuk SyncWorker)
        self.tag_item_model.pending_sqlite.append(tag)

        # 3. Update tampilan layar UI (Log Histori GUI)
        index_tag = find_tag_index(tag)
        if index_tag < 0:  # Insert tag baru ke layar
            self.tag_item_model.insert(tag)
        else:  # Update tag count saja, UI array tidak membongsor
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
        self.pending_sqlite: list[Tag] = []  # Buffer khusus untuk dikirim ke SQLite

    def rowCount(
        self, parent: Union[QModelIndex, QPersistentModelIndex] = QModelIndex
    ) -> int:
        return len(self.tags)

    def columnCount(
        self, parent: Union[QModelIndex, QPersistentModelIndex] = QModelIndex
    ) -> int:
        return len(COLUMNS)

    def data(
        self,
        index: Union[QModelIndex, QPersistentModelIndex],
        role: int = Qt.DisplayRole,
    ) -> Any:
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        # cegah IndexError
        if row < 0 or row >= len(self.tags):
            return None

        tag = self.tags[row]

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
                bg_brush.setColor(QColor.fromRgb(49, 50, 68))  # #313244 dark theme alternate
                bg_brush.setStyle(Qt.SolidPattern)
                return bg_brush

    def insert(self, tag: Tag) -> None:
        if not hasattr(tag, 'timestamp') or not tag.timestamp:
            tag.timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
        row_count = len(self.tags)
        
        # FIFO Cap: Maksimal 2000 baris agar UI tetap smooth dan RAM enteng
        if row_count >= 2000:
            self.beginRemoveRows(QModelIndex(), 0, 0)
            self.tags.pop(0)
            self.endRemoveRows()
            row_count -= 1
            
        self.beginInsertRows(QModelIndex(), row_count, row_count)
        self.tags.append(tag)
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

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole
    ) -> Any:
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return COLUMNS[section]
            elif orientation == Qt.Vertical:
                return section + 1
        return None

class DatabasePooler:
    """Base class: koneksi SQLite, create table, timer loop."""

    def __init__(self, model: InventoryTagItemModel, interval: int = 3, reader_id: str = None):
        self.model = model
        self.interval = interval
        self.reader_id = reader_id
        self.timer = None
        self.db_path = get_db_path()
        self.create_table()

    def connect(self) -> sqlite3.Connection:
        """Buka koneksi SQLite dengan WAL mode aktif."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def create_table(self):
        """Skema terpadu: selalu ada kolom synced (dipakai Online, diabaikan Offline)."""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    epc       TEXT,
                    timestamp TEXT,
                    reader_id TEXT,
                    synced    INTEGER NOT NULL DEFAULT 0
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_epc ON inventory (epc)")
            # Migrasi: tambah kolom synced jika belum ada (DB lama)
            try:
                cursor.execute("ALTER TABLE inventory ADD COLUMN synced INTEGER NOT NULL DEFAULT 0")
            except Exception:
                pass  # Kolom sudah ada — abaikan
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"[ERROR] Failed to create table: {e}")

    def start(self):
        self.timer = Timer(self.interval, self.send_data)
        self.timer.start()

    def stop(self):
        if self.timer:
            self.timer.cancel()

    def send_data(self):
        raise NotImplementedError("Subclass harus mengimplementasikan send_data()")


class DatabasePoolerOnline(DatabasePooler):
    """
    Mode Online (Gateway): bulk insert mentah dari pending_sqlite buffer.
    Tidak ada filter lap/menit — server yang handle duplikat.
    GUI (self.tags) TIDAK dihapus agar panitia tetap melihat log.
    """

    def send_data(self):
        # Ambil dari buffer terpisah, bukan self.model.tags
        tags_to_send = self.model.pending_sqlite.copy()
        self.model.pending_sqlite.clear()

        if not tags_to_send:
            self.start()
            return

        try:
            conn = self.connect()
            cursor = conn.cursor()

            valid_inserts = [
                (str(hex_readable(tag.data)).replace(" ", ""), str(tag.timestamp), self.reader_id, 0)
                for tag in tags_to_send
            ]

            if valid_inserts:
                cursor.executemany(
                    "INSERT INTO inventory (epc, timestamp, reader_id, synced) VALUES (?, ?, ?, ?)",
                    valid_inserts
                )
            conn.commit()
            cursor.close()
            conn.close()

        except Exception as e:
            print(f"[ERROR][Online] Database operation failed: {e}")
            # Kembalikan ke buffer agar dicoba lagi
            self.model.pending_sqlite = tags_to_send + self.model.pending_sqlite

        self.start()


class DatabasePoolerOffline(DatabasePooler):
    """
    Mode Offline (Flask Local): insert dengan filter EPC/lap/menit.
    Hapus tag dari GUI setelah berhasil tersimpan ke SQLite.
    """

    def send_data(self):
        tags_to_send = self.model.tags.copy()

        if not tags_to_send:
            self.start()
            return

        allowed_minutes = getattr(self.model, "allowed_minutes", 5)

        epc_list = list({str(hex_readable(tag.data)).replace(" ", "") for tag in tags_to_send})

        try:
            conn = self.connect()
            cursor = conn.cursor()

            # 1. Pemetaan EPC → BIB
            placeholders_epc = ",".join(["?"] * len(epc_list))
            cursor.execute(
                f"SELECT epc, bib_number FROM epc WHERE epc IN ({placeholders_epc})",
                epc_list
            )
            epc_to_bib = {}
            bib_list = []
            for row in cursor.fetchall():
                epc_to_bib[row[0]] = row[1]
                if row[1] not in bib_list:
                    bib_list.append(row[1])

            # 2. Ambil history waktu terakhir per BIB
            db_state = {}
            if bib_list:
                placeholders_bib = ",".join(["?"] * len(bib_list))
                cursor.execute(f"""
                    SELECT e.bib_number, MAX(i.timestamp), COUNT(i.id), cat.lap
                    FROM inventory i
                    JOIN epc e        ON i.epc = e.epc
                    JOIN category cat ON e.category_id = cat.id
                    WHERE e.bib_number IN ({placeholders_bib})
                    GROUP BY e.bib_number, cat.lap
                """, bib_list)
                for row in cursor.fetchall():
                    db_state[row[0]] = {
                        "last_timestamp": row[1],
                        "existing_lap":   int(row[2]),
                        "allowed_laps":   int(row[3]),
                    }

            # 3. Validasi & kumpulkan insert
            valid_inserts  = []
            tags_to_remove = []

            for tag in tags_to_send:
                epc_str      = str(hex_readable(tag.data)).replace(" ", "")
                current_time = tag.timestamp
                should_insert = True
                bib_num = epc_to_bib.get(epc_str)

                if bib_num and bib_num in db_state:
                    state        = db_state[bib_num]
                    last_ts      = state["last_timestamp"]
                    existing_lap = state["existing_lap"]
                    allowed_laps = state["allowed_laps"]

                    last_dt    = datetime.strptime(last_ts, "%H:%M:%S.%f")
                    current_dt = datetime.strptime(current_time, "%H:%M:%S.%f")
                    diff_min   = abs((current_dt - last_dt).total_seconds()) / 60

                    if diff_min < allowed_minutes or existing_lap >= allowed_laps:
                        should_insert = False

                if should_insert:
                    valid_inserts.append((epc_str, str(current_time), self.reader_id))
                    if bib_num:
                        if bib_num in db_state:
                            db_state[bib_num]["last_timestamp"] = current_time
                            db_state[bib_num]["existing_lap"] += 1
                        else:
                            db_state[bib_num] = {"last_timestamp": current_time, "existing_lap": 1, "allowed_laps": 100}

                tags_to_remove.append(tag)

            if valid_inserts:
                cursor.executemany(
                    "INSERT INTO inventory (epc, timestamp, reader_id) VALUES (?, ?, ?)",
                    valid_inserts
                )

            conn.commit()

            # Hapus dari GUI setelah commit berhasil
            for tag in reversed(tags_to_remove):
                try:
                    index = self.model.tags.index(tag)
                    self.model.remove(index)
                except ValueError:
                    pass

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"[ERROR][Offline] Database operation failed: {e}")
            # Tag TIDAK dihapus dari GUI → dicoba ulang di siklus berikutnya

        self.start()


def create_database_pooler(
    model: InventoryTagItemModel,
    interval: int = 3,
    reader_id: str = None
) -> DatabasePooler:
    """Factory: pilih subclass DatabasePooler berdasarkan APP_MODE di environment."""
    import os
    app_mode = os.getenv("APP_MODE", "online").lower()
    if app_mode == "offline":
        return DatabasePoolerOffline(model, interval=interval, reader_id=reader_id)
    return DatabasePoolerOnline(model, interval=interval, reader_id=reader_id)
