import sys
from logging import getLogger

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QApplication
from dotenv import load_dotenv
from rfid.reader import Reader
from ui.connect_widget import ConnectWidget
from ui.main_widget import MainWidget
from ui.utils import pyinstaller_resource_path
from util_log import setup_logging
from ui.thread.inventory_thread import InventoryThread


logger = getLogger()


class Main:
    def __init__(self, reader: Reader | None = None) -> None:
        super().__init__()
        self.reader = reader
      
        if self.reader is None:
            # Lakukan sesuatu jika Reader tidak tersedia
            logger.warning("MainWidget() > Reader tidak diinisialisasi")
        else:
            # Lakukan inisialisasi yang bergantung pada Reader
            logger.info(f"MainWidget() > Reader diinisialisasi dengan transport: {self.reader.transport}")

    @Slot(Reader)
    def __receive_signal_reader_from_connect_widget(self, reader: Reader) -> None:
        logger.info(f"Main() > __receive_signal_reader_from_connect_widget() > reader.transport: {reader.transport}")

        self.connect_widget.close()

        self.reader = reader
        self.main_widget = MainWidget(reader)
        self.connect_widget = None
        self.main_widget.show()

    def start(self) -> None:
        logger.info("Main() > start()")
        app = QApplication(sys.argv)

        # self.connect_widget = ConnectWidget()
        # self.connect_widget.reader_connected_signal.connect(self.__receive_signal_reader_from_connect_widget)
        # self.connect_widget.show()

        # Inisialisasi Reader tanpa transport
        self.reader = Reader()

        # Tampilkan MainWidget langsung
        self.main_widget = MainWidget(self.reader)
        self.main_widget.show()

        sys.exit(app.exec())

if __name__ == "__main__":
    load_dotenv(dotenv_path=pyinstaller_resource_path('.env.production'))
    setup_logging()
    Main().start()
