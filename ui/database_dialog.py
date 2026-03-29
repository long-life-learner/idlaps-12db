# [LEGACY - TIDAK DIPAKAI LAGI]
# File ini dulunya digunakan untuk konfigurasi koneksi PostgreSQL.
# Sejak migrasi ke SQLite, file ini tidak di-import oleh main.py.
# Dipertahankan sebagai referensi historis saja.
# ─────────────────────────────────────────────────────────────

import os
import psycopg2

from urllib.parse import urlparse, quote_plus, unquote_plus
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QFormLayout
)
from PySide6.QtCore import Qt

class DatabaseDialog(QDialog):
    def __init__(self, env_path: str):
        super().__init__()
        self.setWindowTitle("Konfigurasi Database IDLAPS")
        self.setFixedSize(400, 250)
        self.env_path = env_path

        self.db_host = QLineEdit()
        self.db_port = QLineEdit()
        self.db_user = QLineEdit()
        self.db_pass = QLineEdit()
        self.db_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.db_name = QLineEdit()

        self._load_current_env()

        form_layout = QFormLayout()
        form_layout.addRow("Host / IP Address:", self.db_host)
        form_layout.addRow("Port:", self.db_port)
        form_layout.addRow("Username:", self.db_user)
        form_layout.addRow("Password:", self.db_pass)
        form_layout.addRow("Database Name:", self.db_name)

        self.btn_connect = QPushButton("Test & Hubungkan")
        self.btn_connect.clicked.connect(self.test_and_save)

        self.btn_cancel = QPushButton("Keluar")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_connect)

        main_layout = QVBoxLayout()
        main_layout.addLayout(form_layout)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

    def _load_current_env(self):
        # Default fallback values
        self.db_host.setText("localhost")
        self.db_port.setText("5432")
        self.db_user.setText("postgres")
        self.db_name.setText("inventory")
        
        uri = os.environ.get("DATABASE_URI", "")
        if uri and uri.startswith("postgresql://"):
            try:
                parsed = urlparse(uri)
                if parsed.hostname: self.db_host.setText(parsed.hostname)
                if parsed.port: self.db_port.setText(str(parsed.port))
                if parsed.username: self.db_user.setText(unquote_plus(parsed.username))
                if parsed.password: self.db_pass.setText(unquote_plus(parsed.password))
                if parsed.path: self.db_name.setText(parsed.path.lstrip('/'))
            except Exception:
                pass

    def test_and_save(self):
        host = self.db_host.text().strip()
        port = self.db_port.text().strip()
        user = self.db_user.text().strip()
        pwd = self.db_pass.text()
        dbname = self.db_name.text().strip()

        # Build URI
        encoded_user = quote_plus(user)
        encoded_pwd = quote_plus(pwd)
        uri = f"postgresql://{encoded_user}:{encoded_pwd}@{host}:{port}/{dbname}"

        # Test connection
        try:
            conn = psycopg2.connect(uri)
            conn.close()
        except Exception as e:
            QMessageBox.critical(self, "Koneksi Gagal", f"Tidak dapat terhubung ke PostgreSQL:\n\n{str(e)}\n\nPastikan database berjalan dan parameter yang diisikan benar.")
            return

        # If success, update os.environ
        os.environ["DATABASE_URI"] = uri
        
        # Save to .env.production safely without deleting other keys
        try:
            from ui.utils import pyinstaller_resource_path
            
            # Jika file tidak ada di sebelah exe, kita harus salin master .env bawaan agar semua konfigurasi lain ikut tersimpan!
            if not os.path.exists(self.env_path):
                bundled_env = pyinstaller_resource_path(".env.production")
                if os.path.exists(bundled_env):
                    import shutil
                    shutil.copy(bundled_env, self.env_path)
                else: 
                    # Buat file kosong jika tidak ada master (sangat jarang jika pyinstaller benar)
                    open(self.env_path, 'a').close()
            
            from dotenv import set_key
            set_key(self.env_path, "DATABASE_URI", uri)
        except Exception as e:
            QMessageBox.warning(self, "Peringatan", f"Koneksi berhasil, tapi gagal menyimpan ke {self.env_path}:\n{e}")
            
        QMessageBox.information(self, "Sukses", "Koneksi Database berhasil dikonfigurasi!")
        self.accept()
