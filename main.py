import sys
import threading
from logging import getLogger

from PySide6.QtCore import Slot, QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QMessageBox
from dotenv import load_dotenv
from rfid.reader import Reader
from ui.connect_widget import ConnectWidget
from ui.main_widget import MainWidget
from ui.utils import pyinstaller_resource_path
from util_log import setup_logging
from ui.thread.inventory_thread import InventoryThread
from web import initialize_database, start_web_server


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
            logger.info(
                f"MainWidget() > Reader diinisialisasi dengan transport: {self.reader.transport}"
            )

    @Slot(Reader)
    def __receive_signal_reader_from_connect_widget(self, reader: Reader) -> None:
        logger.info(
            f"Main() > __receive_signal_reader_from_connect_widget() > reader.transport: {reader.transport}"
        )

        self.connect_widget.close()

        self.reader = reader
        self.main_widget = MainWidget(reader)
        self.connect_widget = None
        self.main_widget.show()

    def start(self) -> None:
        logger.info("Main() > start()")
        app = QApplication(sys.argv)

        # 1. Pre-requisite Warning
        msg = QMessageBox()
        msg.setWindowTitle("Pre-requisites / To-Do List")
        msg.setText("<b>Sebelum melanjutkan, pastikan Anda telah memenuhi persyaratan berikut:</b><br><br>"
                    "1. PC ini harus terhubung dengan database PostgreSQL 17. Unduh di: <a href='https://www.postgresql.org/download/'>Link PostgreSQL</a><br>"
                    "2. Matikan fitur 'Sleep Mode' pada pengaturan daya/power PC Anda.<br>"
                    "3. Pastikan PC Anda terhubung dengan Internet atau jaringan LAN yang benar.")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.exec()

        # 2. Initialize Database check
        db_success, db_msg = initialize_database()
        if not db_success:
            err_msg = QMessageBox()
            err_msg.setWindowTitle("Database Error")
            err_msg.setText(f"Gagal menghubungkan atau menginisialisasi database PostgreSQL.<br><br>Pesan Error: {db_msg}<br><br>Harap pastikan PostgreSQL menyala dan tersambung ke jaringan.")
            err_msg.setIcon(QMessageBox.Icon.Critical)
            err_msg.exec()
            sys.exit(1)

        # 3. Start Web Server in Thread
        threading.Thread(target=start_web_server, daemon=True).start()

        # 4. Open External Browser
        QDesktopServices.openUrl(QUrl("http://localhost:5000/"))

        self.connect_widget = ConnectWidget()
        self.connect_widget.reader_connected_signal.connect(
            self.__receive_signal_reader_from_connect_widget
        )
        self.connect_widget.show()

        # Inisialisasi Reader tanpa transport
        self.reader = Reader()    

        # Tampilkan MainWidget langsung
        # self.main_widget = MainWidget(self.reader)
        # self.main_widget.show()

        sys.exit(app.exec())


if __name__ == "__main__":
    load_dotenv(dotenv_path=pyinstaller_resource_path(".env.production"))
    setup_logging()
    Main().start()
