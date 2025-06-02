from PySide6 import QtGui
from PySide6.QtGui import QPainter, QBrush, QColor, QPalette, QPainterPath, QPen
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt, QRectF


_DIALOG_WIDTH = 300
_DIALOG_HEIGHT = 75


class MessageStack(QWidget):
    def __init__(self, parent: QWidget = None, message: str = None):
        QWidget.__init__(self, parent)
        self.message_label = QLabel(message if message is not None else "...Loading...")
        self.message_label.setParent(self)
        self.message_label.setFixedWidth(_DIALOG_WIDTH)
        self.message_label.setFixedHeight(_DIALOG_HEIGHT)
        self.message_label.setAlignment(Qt.AlignCenter)

    def paintEvent(self, event):
        message_painter = QPainter()
        message_painter.begin(self)
        message_painter.setRenderHint(QPainter.Antialiasing, True)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 4, 4)
        pen = QPen(Qt.white, 1)
        message_painter.setPen(pen)
        message_painter.fillPath(path, Qt.white)
        message_painter.drawPath(path)
        message_painter.end()


class MessageStackWidget(QWidget):
    def __init__(self, parent: QWidget, message: str):
        QWidget.__init__(self, parent)
        self.move(0, 0)
        palette = QPalette(self.palette())
        palette.setColor(self.backgroundRole(), Qt.GlobalColor.transparent)
        self.setPalette(palette)

        self.text = MessageStack(self, message)
        self.text.setParent(self)
        self.text.message_label.setText(message)

    def set_text(self, message):
        self.text.message_label.setText(message)

    def paintEvent(self, event):
        painter_bg = QPainter()
        painter_bg.begin(self)
        painter_bg.setRenderHint(QPainter.Antialiasing)
        painter_bg.fillRect(event.rect(), QBrush(QColor(0, 0, 0, 100)))
        painter_bg.end()

    def resizeEvent(self, event):
        position_x = ((self.frameGeometry().width() - self.text.frameGeometry().width()) / 2) - (_DIALOG_WIDTH / 3)
        position_y = ((self.frameGeometry().height() - self.text.frameGeometry().height()) / 2) - (_DIALOG_HEIGHT / 3)
        self.text.move(position_x, position_y)
        event.accept()

