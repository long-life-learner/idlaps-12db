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


logger = getLogger()


class Main:
    def __init__(self) -> None:
        self.connect_widget = None
        self.reader: Reader | None = None

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

         # Inisialisasi langsung Reader (pastikan class Reader sudah siap)

        # Tampilkan MainWidget langsung
        # self.main_widget = MainWidget(None)
        # self.main_widget.show()
        

        self.connect_widget = ConnectWidget()
        self.connect_widget.reader_connected_signal.connect(self.__receive_signal_reader_from_connect_widget)
        self.connect_widget.show()

        sys.exit(app.exec())


if __name__ == "__main__":
    load_dotenv(dotenv_path=pyinstaller_resource_path('.env.production'))
    setup_logging()
    Main().start()
