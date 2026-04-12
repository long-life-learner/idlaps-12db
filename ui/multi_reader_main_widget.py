import os
import time
import requests
from logging import getLogger
from PySide6.QtWidgets import QWidget, QTabWidget, QVBoxLayout
from PySide6.QtCore import Signal
from rfid.reader import Reader
from ui.main_widget import MainWidget
from ui.utils import set_widget_style

logger = getLogger()

class MultiReaderMainWidget(QWidget):
    def __init__(self, readers: list[Reader]) -> None:
        super().__init__()
        logger.info("MultiReaderMainWidget() > __init__()")

        self.app_mode = os.getenv("APP_MODE", "online").lower()
        logger.info(f"MultiReaderMainWidget() > APP_MODE = {self.app_mode}")

        self.setWindowTitle(f"{os.getenv('APP_NAME')} - Connected: {len(readers)}")
        set_widget_style(self)
        self.setMinimumSize(1100, 700)

        self.readers = readers
        self.main_widgets: list[MainWidget] = []
        self.sync_threads = []

        # ── MODE ONLINE ONLY: Fetch NTP Server Time Offset ────────────────────
        self.time_offset = 0.0
        if self.app_mode == "online":
            try:
                res = requests.get("http://time.idlaps.com/api/time.php", timeout=3)
                if res.status_code == 200:
                    server_time = res.json().get("server_time")
                    if server_time:
                        self.time_offset = float(server_time) - time.time()
                        logger.info(f"NTP Sync Success: {self.time_offset:.3f}s offset")
            except Exception as e:
                logger.error(f"NTP Sync Failed (will use local time): {e}")

        layout = QVBoxLayout()
        self.tab_widget = QTabWidget()

        for idx, reader in enumerate(self.readers):
            try:
                reader_id = reader.transport.ip_address
            except AttributeError:
                reader_id = str(reader.transport)

            if self.app_mode == "online":
                # ── MODE ONLINE: Ambil Device SN & Start SyncThread ───────────
                from ui.thread.sync_thread import SyncThread
                device_sn = "UNKNOWN"
                try:
                    dev_info = reader.get_device_info()
                    if dev_info and hasattr(dev_info, 'serial_number'):
                        device_sn = dev_info.serial_number.hex().upper()
                except Exception as e:
                    logger.error(f"Gagal membaca Device SN: {e}")

                sync_th = SyncThread(device_sn=device_sn, reader_ip=reader_id, parent=self)
                self.sync_threads.append(sync_th)
                sync_th.start()

                tab_label = f"Reader {idx + 1} ({reader_id})"
            else:
                # ── MODE OFFLINE: Tidak ada SyncThread ───────────────────────
                tab_label = f"Reader {idx + 1} ({reader_id}) [Offline]"

            # Create main widget (time_offset hanya aktif di online mode)
            main_w = MainWidget(reader, reader_id=reader_id, time_offset=self.time_offset)
            self.main_widgets.append(main_w)

            if self.app_mode == "online" and self.sync_threads:
                # Hubungkan indikator "Data in Wait" hanya di mode online
                sync_th.unsynced_count_signal.connect(main_w.tab.inventory_widget.update_unsynced_count)

            self.tab_widget.addTab(main_w, tab_label)

        layout.addWidget(self.tab_widget)
        self.setLayout(layout)

    def closeEvent(self, event):
        logger.info("MultiReaderMainWidget() > closeEvent()")
        for mw in self.main_widgets:
            mw.close()
        for st in self.sync_threads:
            st.stop()
        event.accept()
