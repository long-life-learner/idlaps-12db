import os
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

        self.setWindowTitle(f"{os.getenv('APP_NAME')} - Connected: {len(readers)}")
        set_widget_style(self)
        self.setMinimumSize(800, 600)

        self.readers = readers
        self.main_widgets: list[MainWidget] = []
        
        layout = QVBoxLayout()
        self.tab_widget = QTabWidget()
        
        for idx, reader in enumerate(self.readers):
            try:
                # Coba ambil IP jika TCP, jika Serial/USB pakai nama transport
                reader_id = reader.transport.ip_address
            except AttributeError:
                reader_id = str(reader.transport)
                
            # Create main widget
            # Note: We modified InventoryWidget to take reader_id, 
            # we need to pass reader_id down to MainWidget
            main_w = MainWidget(reader, reader_id=reader_id)
            self.main_widgets.append(main_w)
            
            tab_label = f"Reader {idx + 1} ({reader_id})"
            self.tab_widget.addTab(main_w, tab_label)
            
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)

    def closeEvent(self, event):
        logger.info("MultiReaderMainWidget() > closeEvent()")
        for mw in self.main_widgets:
            mw.close()
        event.accept()
