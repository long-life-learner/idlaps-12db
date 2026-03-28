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
from ui.main_widget import MainWidget
from ui.utils import pyinstaller_resource_path
from util_log import setup_logging
from ui.thread.inventory_thread import InventoryThread
# web.py di-import nanti secara *deferred* setelah DatabaseDialog berteguh.


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

    def start(self, app: QApplication) -> None:
        logger.info("Main() > start()")
        
        # Defer import web.py agar membaca os.environ yang baru di-inject dari DatabaseDialog
        from web import initialize_database, start_web_server        
        

        # 2. Initialize Database check
        db_success, db_msg = initialize_database()
        if not db_success:
            err_msg = QMessageBox()
            err_msg.setWindowTitle("Database Error")
            err_msg.setText(f"Gagal menghubungkan atau menginisialisasi tabel database PostgreSQL.<br><br>Pesan Error: {db_msg}")
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


def get_external_env_path():
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(application_path, ".env.production")

if __name__ == "__main__":
    external_env = get_external_env_path()
    
    # 1. Selalu muat cadangan bawaan (bundled) terlebih dahulu agar variabel vital tidak None
    load_dotenv(dotenv_path=pyinstaller_resource_path(".env.production"), override=False)

    # 2. Jika ada opsi eksternal (.env.production di sebelah exe), itu akan menimpa (override) bawaan
    if os.path.exists(external_env):
        load_dotenv(dotenv_path=external_env, override=True)

    setup_logging()
    
    app = QApplication(sys.argv)
    from ui.database_dialog import DatabaseDialog
    
    # 1. Munculkan Form Konfigurasi Database terlebih dahulu!# 1. Pre-requisite Warning
    msg = QMessageBox()
    msg.setWindowTitle("Pre-requisites / To-Do List")
    msg.setText("<b>Sebelum melanjutkan, pastikan Anda telah memenuhi persyaratan berikut:</b><br><br>"
                "1. PC ini harus terhubung dengan database PostgreSQL 17. Unduh di: <a href='https://www.postgresql.org/download/'>Link PostgreSQL</a><br>"
                "2. Matikan fitur 'Sleep Mode' pada pengaturan daya/power PC Anda.<br>"
                "3. Pastikan PC Anda terhubung dengan Internet atau jaringan LAN yang benar.")
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setTextFormat(Qt.TextFormat.RichText)
    msg.exec()
    dialog = DatabaseDialog(env_path=external_env)
    
    if dialog.exec() == DatabaseDialog.DialogCode.Accepted:
        # 2. Lanjut masuk ke aplikasi
        app_core = Main()
        app_core.start(app)
    else:
        # Jika batal / close
        sys.exit(0)
