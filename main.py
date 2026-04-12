import sys
import os
import threading
from logging import getLogger

from PySide6.QtCore import Slot, QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QMessageBox
from dotenv import load_dotenv
from rfid.reader import Reader
from ui.connect_widget import ConnectWidget
from ui.multi_reader_main_widget import MultiReaderMainWidget

from ui.utils import pyinstaller_resource_path
from util_log import setup_logging
from ui.thread.inventory_thread import InventoryThread


logger = getLogger()


class Main:
    def __init__(self, reader: Reader | None = None) -> None:
        super().__init__()
        self.reader = reader

        if self.reader is None:
            logger.warning("MainWidget() > Reader tidak diinisialisasi")
        else:
            logger.info(
                f"MainWidget() > Reader diinisialisasi dengan transport: {self.reader.transport}"
            )

    @Slot(list)
    def __receive_signal_readers_from_connect_widget(self, readers: list[Reader]) -> None:
        logger.info(
            f"Main() > __receive_signal_readers_from_connect_widget() > connected readers: {len(readers)}"
        )

        self.connect_widget.close()

        self.readers = readers
        self.main_widget = MultiReaderMainWidget(readers)
        self.connect_widget = None
        self.main_widget.show()


    def start(self, app: QApplication) -> None:
        logger.info("Main() > start()")

        # Defer import web.py agar modul Flask siap setelah semua setup selesai
        from web import initialize_database, start_web_server

        # Initialize Database (SQLite — tidak perlu koneksi eksternal)
        db_success, db_msg = initialize_database()
        if not db_success:
            err_msg = QMessageBox()
            err_msg.setWindowTitle("Database Error")
            err_msg.setText(f"Gagal menginisialisasi database SQLite.<br><br>Pesan Error: {db_msg}")
            err_msg.setIcon(QMessageBox.Icon.Critical)
            err_msg.exec()
            sys.exit(1)

        # Start Web Server in Thread (DIMATIKAN SEKARANG - Murni Mode Gateway Online)
        # threading.Thread(target=start_web_server, daemon=True).start()

        # Open External Browser (DIMATIKAN - User diminta buka Web Dashboard online time.idlaps.com)
        # QDesktopServices.openUrl(QUrl("http://localhost:5000/"))

        # --- BYPASS CONNECT WIDGET START ---
        # self.connect_widget = ConnectWidget()
        # self.connect_widget.readers_connected_signal.connect(
        #     self.__receive_signal_readers_from_connect_widget
        # )
        # self.connect_widget.show()

        # Bypass langsung ke main widget dengan dummy reader
        self.connect_widget = None
        self.readers = [Reader()]
        self.main_widget = MultiReaderMainWidget(self.readers)
        self.main_widget.show()
        # --- BYPASS CONNECT WIDGET END ---

        # Inisialisasi Reader tanpa transport
        self.reader = Reader()

        sys.exit(app.exec())


def get_external_env_path():
    """Path ke .env.production di sebelah exe (atau direktori project saat dev)."""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, ".env.production")


if __name__ == "__main__":
    external_env = get_external_env_path()

    # Muat konfigurasi RFID (BAUD_RATE, IP_ADDRESS, TCP_PORT, APP_NAME, dll)
    # dari .env.production — masih diperlukan oleh connect_widget.py.
    # DATABASE_URI yang ada di dalamnya diabaikan karena web.py
    # sekarang menggunakan SQLite via get_db_path(), bukan env var.
    load_dotenv(dotenv_path=pyinstaller_resource_path(".env.production"), override=False)
    if os.path.exists(external_env):
        load_dotenv(dotenv_path=external_env, override=True)

    setup_logging()

    app = QApplication(sys.argv)

    # Pesan startup ringkas — tidak ada lagi prerequisite PostgreSQL
    msg = QMessageBox()
    msg.setWindowTitle("IDLAPS Checkpoint — Persiapan")
    msg.setText(
        "<b>Sebelum melanjutkan, pastikan:</b><br><br>"
        "1. Matikan fitur <b>Sleep Mode</b> pada pengaturan daya/power PC Anda.<br>"
        "2. Pastikan PC Anda terhubung dengan jaringan <b>LAN</b> yang benar.<br><br>"
    )
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setTextFormat(Qt.TextFormat.RichText)
    msg.exec()

    app_core = Main()
    app_core.start(app)


