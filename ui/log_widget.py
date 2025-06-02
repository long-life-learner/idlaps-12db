from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QTextEdit, QVBoxLayout, QGroupBox
from rfid.reader import Reader
from rfid.response import Response
from rfid.utils import hex_readable


class LogWidget(QWidget):
    def __init__(self, reader: Reader) -> None:
        super().__init__()

        self.reader = reader
        self.reader.send_request_bytes_signal.connect(self.__receive_signal_send_request_bytes)
        self.reader.receive_response_bytes_signal.connect(self.__receive_signal_receive_response_bytes)

        self.log_tex_edit = QTextEdit()
        self.log_tex_edit.setReadOnly(True)
        self.log_tex_edit.setMinimumHeight(200)
        self.log_tex_edit.setFont(QFont('Cascadia Code'))

        layout = QVBoxLayout()
        layout.addWidget(self.log_tex_edit)

        log_group_box = QGroupBox("Log")
        log_group_box.setLayout(layout)

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.addWidget(log_group_box)

        self.setLayout(layout)

    def __receive_signal_send_request_bytes(self, data: bytes) -> None:
        self.log_tex_edit.append(f'>> REQUEST\t: {hex_readable(data)}')

    def __receive_signal_receive_response_bytes(self, data: bytes) -> None:
        self.log_tex_edit.append(f'<< RESPONSE\t: {hex_readable(Response(data).serialize())}')

