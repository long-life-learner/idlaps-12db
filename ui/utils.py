import os
import sys

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QRegularExpressionValidator, QPixmap, QIcon, QFont, QPalette, QColor
from PySide6.QtWidgets import QSpinBox, QAbstractSpinBox, QWidget, QFrame, QMessageBox, QGraphicsOpacityEffect, QApplication


class QHLine(QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.Shape.HLine)
        opacity_effect = QGraphicsOpacityEffect(self)
        opacity_effect.setOpacity(0.25)
        self.setGraphicsEffect(opacity_effect)
        self.setAutoFillBackground(True)


class QVLine(QFrame):
    def __init__(self):
        super(QVLine, self).__init__()
        self.setFrameShape(QFrame.Shape.VLine)


class QHexSpinBox(QSpinBox):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMaximum(255)
        self.setDisplayIntegerBase(16)
        self.setPrefix("0x")
        font = self.font()
        font.setCapitalization(QFont.Capitalization.AllUppercase)
        self.setFont(font)

    def textFromValue(self, val:int) -> str:
        return "{:02X}".format(val)


class QFrequencySpinBox(QSpinBox, QAbstractSpinBox):
    def __init__(self) -> None:
        super().__init__()


class IpAddressValidator(QRegularExpressionValidator):
    def __init__(self) -> None:
        octet= "([0-1]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])"
        ip_regex = f"^{octet}\\.{octet}\\.{octet}\\.{octet}$"
        super().__init__(ip_regex)


def bytes_to_icon(value: bytes) -> QIcon:
    temp = QPixmap()
    temp.loadFromData(QByteArray.fromBase64(value))
    return QIcon(temp)


def setup_input_widget(widget, min_width: int = 110, height: int = 30) -> None:
    """Set consistent size on input widgets (QComboBox, QSpinBox, QLineEdit).

    On macOS, QSS min-height only affects visual rendering — NOT the sizeHint
    reported to the layout engine. This causes QGridLayout to allocate
    insufficient row height, making rows overlap. setFixedHeight() here forces
    the layout engine to reserve the correct height on all platforms.
    """
    widget.setMinimumWidth(min_width)
    widget.setFixedHeight(height)


APP_STYLESHEET = """
    /* ── Global ── */
    QWidget {
        background-color: #1e1e2e;
        color: #cdd6f4;
        font-family: "SF Pro Text", "Helvetica Neue", "Segoe UI", Arial, sans-serif;
        font-size: 13px;
    }

    /* ── Window / Dialog ── */
    QMainWindow, QDialog {
        background-color: #1e1e2e;
    }

    /* ── GroupBox ── */
    QGroupBox {
        background-color: #313244;
        border: 1px solid #45475a;
        border-radius: 6px;
        margin-top: 10px;
        padding: 8px 6px 6px 6px;
        font-weight: 600;
        color: #cdd6f4;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 10px;
        padding: 0 4px;
        color: #89b4fa;
    }

    /* ── Labels ── */
    QLabel {
        background-color: transparent;
        color: #cdd6f4;
    }

    /* ── Buttons ── */
    QPushButton {
        background-color: #89b4fa;
        color: #1e1e2e;
        border: none;
        border-radius: 5px;
        padding: 5px 14px;
        font-weight: 600;
        min-height: 28px;
    }
    QPushButton:hover {
        background-color: #b4befe;
    }
    QPushButton:pressed {
        background-color: #74c7ec;
    }
    QPushButton:disabled {
        background-color: #45475a;
        color: #585b70;
    }

    /* ── ComboBox ── */
    QComboBox {
        background-color: #313244;
        color: #cdd6f4;
        border: 1px solid #585b70;
        border-radius: 4px;
        padding: 3px 8px;
        selection-background-color: #89b4fa;
        selection-color: #1e1e2e;
    }
    QComboBox:hover {
        border-color: #89b4fa;
    }
    QComboBox:focus {
        border-color: #89b4fa;
    }
    QComboBox::drop-down {
        border: none;
        width: 20px;
    }
    QComboBox::down-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid #cdd6f4;
        width: 0;
        height: 0;
        margin-right: 6px;
    }
    QComboBox QAbstractItemView {
        background-color: #313244;
        color: #cdd6f4;
        border: 1px solid #585b70;
        selection-background-color: #89b4fa;
        selection-color: #1e1e2e;
        outline: none;
    }

    /* ── SpinBox / DoubleSpinBox ── */
    QSpinBox, QDoubleSpinBox {
        background-color: #313244;
        color: #cdd6f4;
        border: 1px solid #585b70;
        border-radius: 4px;
        padding: 3px 6px;
        selection-background-color: #89b4fa;
        selection-color: #1e1e2e;
    }
    QSpinBox:hover, QDoubleSpinBox:hover {
        border-color: #89b4fa;
    }
    QSpinBox:focus, QDoubleSpinBox:focus {
        border-color: #89b4fa;
    }
    QSpinBox::up-button, QDoubleSpinBox::up-button {
        background-color: #45475a;
        border: none;
        border-radius: 2px;
        width: 14px;
        subcontrol-origin: border;
        subcontrol-position: top right;
        margin: 1px 1px 0px 0px;
    }
    QSpinBox::down-button, QDoubleSpinBox::down-button {
        background-color: #45475a;
        border: none;
        border-radius: 2px;
        width: 14px;
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        margin: 0px 1px 1px 0px;
    }
    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
        background-color: #585b70;
    }
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
        border-left: 3px solid transparent;
        border-right: 3px solid transparent;
        border-bottom: 4px solid #cdd6f4;
        width: 0; height: 0;
    }
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
        border-left: 3px solid transparent;
        border-right: 3px solid transparent;
        border-top: 4px solid #cdd6f4;
        width: 0; height: 0;
    }

    /* ── LineEdit ── */
    QLineEdit {
        background-color: #313244;
        color: #cdd6f4;
        border: 1px solid #585b70;
        border-radius: 4px;
        padding: 3px 8px;
        selection-background-color: #89b4fa;
        selection-color: #1e1e2e;
    }
    QLineEdit:hover {
        border-color: #89b4fa;
    }
    QLineEdit:focus {
        border-color: #89b4fa;
    }

    /* ── TabWidget ── */
    QTabWidget::pane {
        background-color: #181825;
        border: 1px solid #45475a;
        border-radius: 6px;
        margin-top: -1px;
    }
    QTabBar::tab {
        background-color: #313244;
        color: #a6adc8;
        border: 1px solid #45475a;
        border-bottom: none;
        border-radius: 4px 4px 0 0;
        padding: 5px 14px;
        margin-right: 2px;
        font-weight: 500;
    }
    QTabBar::tab:selected {
        background-color: #89b4fa;
        color: #1e1e2e;
        font-weight: 700;
        border-color: #89b4fa;
    }
    QTabBar::tab:hover:!selected {
        background-color: #45475a;
        color: #cdd6f4;
    }

    /* ── TableView ── */
    QTableView {
        background-color: #181825;
        color: #cdd6f4;
        gridline-color: #313244;
        border: 1px solid #45475a;
        border-radius: 4px;
        selection-background-color: #89b4fa;
        selection-color: #1e1e2e;
        alternate-background-color: #1e1e2e;
    }
    QHeaderView::section {
        background-color: #313244;
        color: #89b4fa;
        border: none;
        border-right: 1px solid #45475a;
        border-bottom: 1px solid #45475a;
        padding: 4px 8px;
        font-weight: 600;
    }
    QHeaderView::section:first {
        border-left: none;
    }
    QTableView::item:selected {
        background-color: #89b4fa;
        color: #1e1e2e;
    }
    QTableView::item:alternate {
        background-color: #1e1e2e;
    }
    QTableCornerButton::section {
        background-color: #313244;
        border: none;
        border-right: 1px solid #45475a;
        border-bottom: 1px solid #45475a;
    }

    /* ── ScrollBar ── */
    QScrollBar:vertical {
        background-color: #181825;
        width: 10px;
        margin: 0;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical {
        background-color: #45475a;
        border-radius: 5px;
        min-height: 20px;
    }
    QScrollBar::handle:vertical:hover {
        background-color: #585b70;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    QScrollBar:horizontal {
        background-color: #181825;
        height: 10px;
        border-radius: 5px;
    }
    QScrollBar::handle:horizontal {
        background-color: #45475a;
        border-radius: 5px;
        min-width: 20px;
    }
    QScrollBar::handle:horizontal:hover {
        background-color: #585b70;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

    /* ── CheckBox ── */
    QCheckBox {
        background-color: transparent;
        color: #cdd6f4;
        spacing: 6px;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 2px solid #585b70;
        border-radius: 3px;
        background-color: #313244;
    }
    QCheckBox::indicator:checked {
        background-color: #89b4fa;
        border-color: #89b4fa;
    }
    QCheckBox::indicator:hover {
        border-color: #89b4fa;
    }

    /* ── ProgressBar ── */
    QProgressBar {
        background-color: #313244;
        border: none;
        border-radius: 3px;
        text-align: center;
        color: transparent;
    }
    QProgressBar::chunk {
        background-color: #89b4fa;
        border-radius: 3px;
    }

    /* ── MenuBar ── */
    QMenuBar {
        background-color: #181825;
        color: #cdd6f4;
    }
    QMenuBar::item:selected {
        background-color: #313244;
    }
    QMenu {
        background-color: #313244;
        color: #cdd6f4;
        border: 1px solid #45475a;
    }
    QMenu::item:selected {
        background-color: #89b4fa;
        color: #1e1e2e;
    }

    /* ── ListWidget ── */
    QListWidget {
        background-color: #181825;
        color: #cdd6f4;
        border: 1px solid #45475a;
        border-radius: 4px;
    }
    QListWidget::item:selected {
        background-color: #89b4fa;
        color: #1e1e2e;
    }
    QListWidget::item:hover {
        background-color: #313244;
    }

    /* ── MessageBox ── */
    QMessageBox {
        background-color: #1e1e2e;
    }
    QMessageBox QLabel {
        color: #cdd6f4;
    }
"""


def apply_app_style(app: QApplication) -> None:
    """Apply global stylesheet to the entire application. Call once at startup."""
    app.setStyleSheet(APP_STYLESHEET)


def set_widget_style(widget: QWidget) -> None:
    # Icon (Safe Fallback)
    try:
        icon_b64 = os.getenv('APP_ICON_BASE64')
        if icon_b64:
            widget.setWindowIcon(bytes_to_icon(icon_b64.encode()))
    except Exception:
        pass
    # NOTE: Tidak menggunakan setPalette() karena di macOS menyebabkan palette
    # di-inherit ke child widgets (ComboBox, SpinBox, LineEdit), sehingga teks
    # dan border menjadi tidak visible (putih di atas putih).
    # Styling sepenuhnya ditangani oleh APP_STYLESHEET via apply_app_style().


def show_message_box(title: str, message: str, success: bool = False, with_icon: bool = True) -> None:
    message_box = QMessageBox()
    message_box.setWindowTitle(title)
    message_box.setText(message)
    message_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    message_box.setContentsMargins(1, 1, 1, 1)

    set_widget_style(message_box)

    if with_icon:
        if success:
            message_box.setIcon(QMessageBox.Icon.Information)
        else:
            message_box.setIcon(QMessageBox.Icon.Critical)

    message_box.exec_()


def pyinstaller_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception as _:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def get_db_path() -> str:
    """
    Mengembalikan path absolut ke file inventory.db.
    - Mode exe (PyInstaller): di samping file .exe
    - Mode dev (script):      di direktori root proyek
    Kedua komponen (web.py dan inventory_widget.py) harus menggunakan
    fungsi ini agar keduanya menulis ke file yang SAMA.
    """
    if getattr(sys, 'frozen', False):
        # Berjalan sebagai hasil PyInstaller → pakai folder di sebelah .exe
        base = os.path.dirname(sys.executable)
    else:
        # Berjalan sebagai script Python biasa
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "inventory.db")
