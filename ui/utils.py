import os
import sys

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QRegularExpressionValidator, QPixmap, QIcon, QFont
from PySide6.QtWidgets import QSpinBox, QAbstractSpinBox, QWidget, QFrame, QMessageBox, QGraphicsOpacityEffect


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


def set_widget_style(widget: QWidget) -> None:
    # Icon
    widget.setWindowIcon(bytes_to_icon(os.getenv('APP_ICON_BASE64').encode()))

    # Fix window size
    widget.setWindowFlag(Qt.MSWindowsFixedSizeDialogHint)
    # widget.setContentsMargins(1, 1, 1, 1)

    # Background color
    p = widget.palette()
    p.setColor(widget.backgroundRole(), Qt.white)
    widget.setPalette(p)


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
