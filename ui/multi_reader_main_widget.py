import os
import time
import requests
from logging import getLogger
from PySide6.QtWidgets import QWidget, QTabWidget, QVBoxLayout
from PySide6.QtCore import Signal
from rfid.reader import Reader
from ui.main_widget import MainWidget
from ui.utils import set_widget_style
from ui.thread.sync_thread import SyncThread

logger = getLogger()

class MultiReaderMainWidget(QWidget):
    def __init__(self, readers: list[Reader]) -> None:
        super().__init__()
        logger.info("MultiReaderMainWidget() > __init__()")

        # Fetch NTP Server Time Offset
        self.time_offset = 0.0
        try:
            res = requests.get("http://time.idlaps.com/api/time.php", timeout=3)
            if res.status_code == 200:
                server_time = res.json().get("server_time")
                if server_time:
                    self.time_offset = float(server_time) - time.time()
                    logger.info(f"NTP Sync Success: {self.time_offset:.3f}s offset")
        except Exception as e:
            logger.error(f"NTP Sync Failed: {e}")

        self.setWindowTitle(f"{os.getenv('APP_NAME')} - Connected: {len(readers)}")
        set_widget_style(self)
        self.setMinimumSize(800, 600)

        self.readers = readers
        self.main_widgets: list[MainWidget] = []
        self.sync_threads: list[SyncThread] = []
        
        layout = QVBoxLayout()
        self.tab_widget = QTabWidget()
        
        for idx, reader in enumerate(self.readers):
            try:
                # Coba ambil IP jika TCP, jika Serial/USB pakai nama transport
                reader_id = reader.transport.ip_address
            except AttributeError:
                reader_id = str(reader.transport)
                
            # Request Device SN for API Authentication
            device_sn = "UNKNOWN"
            try:
                dev_info = reader.get_device_info()
                device_sn = dev_info
                
                
                # if dev_info and hasattr(dev_info, 'serial_number'):
                #     device_sn = dev_info.serial_number.hex().upper()
            except Exception as e:
                logger.error(f"Gagal membaca Device SN: {e}")
                
            # Start Sync Worker
            sync_th = SyncThread(device_sn=device_sn, reader_ip=reader_id, parent=self)
            self.sync_threads.append(sync_th)
            sync_th.start()
                
            # Create main widget
            main_w = MainWidget(reader, reader_id=reader_id, time_offset=self.time_offset)
            self.main_widgets.append(main_w)
            
            # Hubungkan indikator jumlah "Data in Wait" SQLite agar update ke layar Desktop
            sync_th.unsynced_count_signal.connect(main_w.tab.inventory_widget.update_unsynced_count)
            
            tab_label = f"Reader {idx + 1} ({reader_id}) - {device_sn}"
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
