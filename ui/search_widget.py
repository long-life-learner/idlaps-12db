import os
from typing import Union, Any
from rfid.utils import ip_string

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt, QSize, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QWidget, QLineEdit, QTableView, QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QSpinBox, \
    QProgressBar

from rfid.reader_settings import NetworkSettings
from rfid.utils import netmask_to_cidr, ip_string, hex_readable
from ui.thread.search_ip_thread import SearchIpThread
from ui.utils import show_message_box, set_widget_style
from logging import getLogger

logger = getLogger()
class SearchIpWidget(QWidget):
    network_settings_list_signal = Signal(list)


    def __init__(self) -> None:
        super().__init__()



        self.setWindowTitle(os.getenv('APP_NAME'))
        set_widget_style(self)
        self.setMaximumWidth(600)
        self.setMinimumWidth(600)

        ip_network_label = QLabel("IP Range / CIDR")
        ip_network_label.setMaximumWidth(100)

        self.ip_network_line_edit = QLineEdit("192.168.1.3-255")
        self.ip_network_line_edit.setMaximumWidth(200)



        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.__search_clicked)
        
        self.select_button = QPushButton("Pilih")
        self.select_button.setDisabled(True)
        self.select_button.clicked.connect(self.__select_clicked)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setContentsMargins(1, 1, 1, 1)
        self.progress_bar.setMaximumSize(QSize(999999, 5))
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()

        self.search_ip_table_view = QTableView()
        self.search_ip_model = SearchIpModel(self)
        self.search_ip_table_view.setModel(self.search_ip_model)
        self.search_ip_table_view.setSelectionMode(QTableView.MultiSelection) # rikza
        self.search_ip_table_view.setSelectionBehavior(QTableView.SelectRows) # rikza 
        self.search_ip_table_view.setColumnWidth(0, 150)
        self.search_ip_table_view.setColumnWidth(1, 50)
        self.search_ip_table_view.setColumnWidth(2, 150)
        self.search_ip_table_view.setColumnWidth(3, 150)
        self.search_ip_table_view.horizontalHeader().setStretchLastSection(True)
        self.search_ip_table_view.verticalHeader().setDefaultSectionSize(10)
        self.search_ip_table_view.doubleClicked.connect(self.on_row_double_clicked)
        self.search_ip_table_view.selectionModel().selectionChanged.connect(self.__on_selection_changed)

        h_layout = QHBoxLayout()
        h_layout.addWidget(ip_network_label)
        h_layout.addWidget(self.ip_network_line_edit)

        h_layout.addWidget(self.search_button)
        h_layout.addWidget(self.select_button)

        v_layout = QVBoxLayout()
        v_layout.addLayout(h_layout)
        v_layout.addWidget(self.progress_bar)
        v_layout.addWidget(self.search_ip_table_view)
        self.setLayout(v_layout)

        self.is_searching: bool = False
        self.search_ip_thread: SearchIpThread | None = None

        

    def closeEvent(self, event):
        if self.is_searching:
            return
        event.accept()

    def __on_selection_changed(self):
        selected_rows = self.search_ip_table_view.selectionModel().selectedRows()
        self.select_button.setEnabled(bool(selected_rows))

    def __select_clicked(self):
        if self.is_searching:
            return

        selected_indexes = self.search_ip_table_view.selectionModel().selectedRows()
        selected_network_settings = [
            self.search_ip_model.list_network_settings[index.row()]
            for index in selected_indexes
        ]

        if not selected_network_settings:
            show_message_box("Peringatan", "Silakan pilih setidaknya satu perangkat.", success=False)
            return

        self.network_settings_list_signal.emit(selected_network_settings)
        self.close()


    @property
    def ip_network(self) -> str:
        value = self.ip_network_line_edit.text().strip()
        if not value:
            raise ValueError("IP network is empty")
        return value



    def on_row_double_clicked(self, index: QModelIndex) -> None:
        if self.is_searching:
            return
        network_settings: NetworkSettings = self.search_ip_model.list_network_settings[index.row()]
        self.network_settings_list_signal.emit([network_settings])
        self.close()


    def __search_clicked(self) -> None:
        self.is_searching = not self.is_searching

        if self.is_searching:
            self.search_button.setDisabled(True)
            self.search_button.setText("Searching...")
            self.search_ip_model.clear()
            # Kita kirimkan ip_network string (yg bs berupa CIDR atau range) langsung ke thread
            self.search_ip_thread = SearchIpThread(self.ip_network)

            self.search_ip_thread.progress_signal.connect(self.__receive_signal_progress)
            self.search_ip_thread.network_settings_signal.connect(self.__receive_signal_network_settings)
            self.search_ip_thread.finish_signal.connect(self.__receive_signal_finish)
            self.search_ip_thread.start()

    def __receive_signal_progress(self, value: int) -> None:
        self.progress_bar.show()
        self.progress_bar.setValue(value)

    def __receive_signal_network_settings(self, response: NetworkSettings | Exception) -> None:
        if isinstance(response, Exception):
            show_message_box("Failed", f"Something went wrong, {response}.", success=False)
            return
        if isinstance(response, NetworkSettings):
            self.search_ip_model.insert(response)

    def __receive_signal_finish(self) -> None:
        self.is_searching = False
        self.search_button.setDisabled(False)
        self.search_button.setText("Search")
        self.progress_bar.hide()


COLUMNS = ["IP Address", "Port", "IP Gateway", "MAC Address"]


class SearchIpModel(QAbstractTableModel):

    def __init__(self, parent: SearchIpWidget) -> None:
        super().__init__()
        self.parent = parent
        self.list_network_settings: list[NetworkSettings] = []

    def rowCount(self, parent: Union[QModelIndex, QPersistentModelIndex] = QModelIndex) -> int:
        return len(self.list_network_settings)

    def columnCount(self, parent: Union[QModelIndex, QPersistentModelIndex] = QModelIndex) -> int:
        return len(COLUMNS)

    def data(self, index: Union[QModelIndex, QPersistentModelIndex], role: int = Qt.DisplayRole) -> Any:
        if role == Qt.DisplayRole:
            network_settings = self.list_network_settings[index.row()]
            if index.column() == 0:  # IP Address
                return f"{ip_string(network_settings.ip_address)}/{netmask_to_cidr(ip_string(network_settings.netmask))}"
            if index.column() == 1:  # Port
                return network_settings.port
            elif index.column() == 2:  # IP Gateway
                return ip_string(network_settings.gateway)
            elif index.column() == 3:  # MAC Address
                return hex_readable(network_settings.mac_address, separator=":")
        if role == Qt.BackgroundRole:
            if index.row() % 2 == 0:
                bg_brush = QBrush()
                bg_brush.setColor(QColor.fromRgb(216, 216, 216))
                bg_brush.setStyle(Qt.SolidPattern)
                return bg_brush

    def insert(self, network_settings: NetworkSettings) -> None:
        find_network_settings = [n for n in self.list_network_settings if n.mac_address == network_settings.mac_address]
        if find_network_settings:
            return
        row_count = len(self.list_network_settings)
        self.beginInsertRows(QModelIndex(), row_count, row_count)
        self.list_network_settings.append(network_settings)
        row_count += 1
        self.endInsertRows()

    def remove(self, index: int) -> None:
        row_count = self.rowCount()
        row_count -= 1
        self.beginRemoveRows(QModelIndex(), row_count, row_count)
        self.list_network_settings.pop(index)
        self.endRemoveRows()

    def clear(self) -> None:
        self.list_network_settings.clear()
        self.layoutChanged.emit()

    def update(self, network_settings: NetworkSettings) -> None:
        find_network_settings = [n for n in self.list_network_settings if n.mac_address == network_settings.mac_address]
        find_network_settings = find_network_settings[0]
        find_network_settings.ip_address = network_settings.ip_address
        find_network_settings.port = network_settings.port
        find_network_settings.netmask = network_settings.netmask
        find_network_settings.gateway = network_settings.gateway
        index = self.list_network_settings.index(find_network_settings)
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
