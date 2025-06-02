from enum import Enum

from PySide6.QtWidgets import QWidget, QLabel, QComboBox, QGridLayout, QPushButton, QVBoxLayout, QGroupBox, \
    QSpinBox, QCheckBox, QHBoxLayout, QLineEdit
from PySide6.QtGui import QRegularExpressionValidator, Qt

from rfid.reader import Reader
from rfid.reader_settings import MaskInventoryPermission, MaskInventoryPermissionCondition
from ui.thread.inventory_filter_thread import SetInventoryFilterThread
from ui.utils import show_message_box


class InventoryFilterCondition(Enum):
    NO_FILTER = "-- No filter --"
    PASSWORD = "Password only"
    MASK = "Mask only"
    PASSWORD_OR_MASK = "Password OR Mask"
    PASSWORD_AND_MASK = "Password AND Mask"


class InventoryFilterWidget(QWidget):
    def __init__(self, reader: Reader):
        super().__init__()

        inventory_filter_group_box = QGroupBox("Inventory filter")
        access_password_label = QLabel("Access password")
        mask_data_label = QLabel("Mask data")
        mask_start_address_label = QLabel("Start address")
        condition_label = QLabel("Condition")
        condition_label.setMaximumWidth(80)

        mask_start_address_byte_label = QLabel("(in bytes)")
        mask_start_address_byte_label.setMinimumWidth(45)

        self.condition_combo_box = QComboBox()
        self.condition_combo_box.setMinimumWidth(250)
        self.condition_combo_box.setMaximumWidth(250)
        self.condition_combo_box.addItems([condition.value for condition in InventoryFilterCondition])
        self.condition_combo_box.currentTextChanged.connect(self.__on_changed_text_condition_combo_box)
        self.mask_start_address_spin_box = QSpinBox()
        self.mask_start_address_spin_box.setRange(0, 255)
        self.mask_start_address_spin_box.setMinimumWidth(60)
        self.access_password_line_edit = QLineEdit()
        self.access_password_line_edit.setMaxLength(8)
        self.access_password_line_edit.setText("00000000")
        self.access_password_line_edit.setValidator(QRegularExpressionValidator("^[0-9a-fA-F]{0,8}$"))
        self.access_password_line_edit.textEdited.connect(self.__access_password_line_edit_edited)
        self.access_password_line_edit.editingFinished.connect(self.__access_password_line_edit_finished)
        self.mask_data_line_edit = QLineEdit()
        self.mask_data_line_edit.setMinimumWidth(300)
        self.mask_data_line_edit.setValidator(QRegularExpressionValidator("^[0-9a-fA-F]+"))
        self.mask_data_line_edit.textEdited.connect(self.mask_data_line_edit_edited)
        self.mask_data_line_edit.setMaxLength(35)
        self.mask_data_line_edit.setText("00 00 00 00 00 00 00 00 00 00 00 00")

        access_password_v_layout = QGridLayout()
        access_password_v_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        access_password_v_layout.addWidget(access_password_label)
        access_password_v_layout.addWidget(self.access_password_line_edit)
        self.access_password_group_box = QGroupBox("Access password")
        self.access_password_group_box.setLayout(access_password_v_layout)
        self.access_password_group_box.setEnabled(False)

        mask_layout = QGridLayout()
        mask_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        mask_layout.addWidget(mask_start_address_label, 0, 0)
        mask_layout.addWidget(self.mask_start_address_spin_box, 0, 1)
        mask_layout.addWidget(mask_start_address_byte_label, 0, 2)
        mask_layout.addWidget(QLabel(), 0, 3)
        mask_layout.addWidget(mask_data_label, 1, 0)
        mask_layout.addWidget(self.mask_data_line_edit, 1, 1, 1, 6)
        self.mask_group_box = QGroupBox("Mask")
        self.mask_group_box.setLayout(mask_layout)
        self.mask_group_box.setEnabled(False)

        condition_h_layout = QHBoxLayout()
        condition_h_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        condition_h_layout.setContentsMargins(0, 10, 0, 0)
        condition_h_layout.addWidget(condition_label)
        condition_h_layout.addWidget(self.condition_combo_box)

        inventory_filter_h_layout = QHBoxLayout()
        inventory_filter_h_layout.addWidget(self.access_password_group_box, 1)
        inventory_filter_h_layout.addWidget(self.mask_group_box, 2)

        # Button (set)
        self.set_button = QPushButton("Set")
        self.set_button.clicked.connect(self.__set_clicked)
        self.set_button.setMinimumHeight(32)

        button_grid_layout = QGridLayout()
        button_grid_layout.addWidget(self.set_button, 0, 0)
        button_grid_layout.addWidget(QLabel(), 0, 1)
        button_grid_layout.addWidget(QLabel(), 0, 2, 1, 2)
        button_grid_layout.addWidget(QLabel(), 0, 5)

        inventory_filter_v_layout = QVBoxLayout()
        inventory_filter_v_layout.addLayout(button_grid_layout)
        inventory_filter_v_layout.addLayout(condition_h_layout)
        inventory_filter_v_layout.addLayout(inventory_filter_h_layout)

        inventory_filter_group_box.setLayout(inventory_filter_v_layout)

        layout = QVBoxLayout()
        layout.addWidget(inventory_filter_group_box)
        layout.setSpacing(0)
        layout.setContentsMargins(1, 1, 1, 1)
        self.setLayout(layout)

        self.reader = reader
        self.set_inventory_filter_thread: SetInventoryFilterThread | None = None
        self.__mask_inventory_permission: MaskInventoryPermission | None = None

    def __on_changed_text_condition_combo_box(self, value: str) -> None:
        self.access_password_group_box.setEnabled(self.enable_access_password)
        self.mask_group_box.setEnabled(self.enable_mask)

    @property
    def mask_inventory_permission(self) -> MaskInventoryPermission:
        return MaskInventoryPermission(
            enable_access_password=self.enable_access_password,
            enable_mask=self.enable_mask,
            mask_start_address=self.mask_start_address,
            mask=self.mask_data,
            condition=self.mask_inventory_permission_condition,
            access_password=self.access_password,
        )

    @property
    def enable_access_password(self) -> bool:
        if self.inventory_filter_condition in [InventoryFilterCondition.PASSWORD,
                                               InventoryFilterCondition.PASSWORD_OR_MASK,
                                               InventoryFilterCondition.PASSWORD_AND_MASK]:
            return True
        return False

    @property
    def enable_mask(self) -> bool:
        if self.inventory_filter_condition in [InventoryFilterCondition.MASK,
                                               InventoryFilterCondition.PASSWORD_OR_MASK,
                                               InventoryFilterCondition.PASSWORD_AND_MASK]:
            return True
        return False

    @property
    def inventory_filter_condition(self) -> InventoryFilterCondition:
        return InventoryFilterCondition(self.condition_combo_box.currentText())

    @property
    def mask_inventory_permission_condition(self) -> MaskInventoryPermissionCondition:
        if self.inventory_filter_condition == InventoryFilterCondition.PASSWORD_AND_MASK:
            return MaskInventoryPermissionCondition.PASSWORD_AND_MASK
        else:
            return MaskInventoryPermissionCondition.PASSWORD_OR_MASK

    @property
    def mask_start_address(self) -> int:
        return self.mask_start_address_spin_box.value()

    @property
    def access_password(self) -> bytes:
        access_password = bytearray.fromhex(self.access_password_line_edit.text().replace(' ', ''))
        if self.enable_access_password and access_password == bytes(4):
            raise ValueError("Failed, access password can't zero")
        return bytearray.fromhex(self.access_password_line_edit.text().replace(' ', ''))

    @property
    def mask_data(self) -> bytes:
        return bytearray.fromhex(self.mask_data_line_edit.text().replace(' ', ''))

    def __access_password_line_edit_edited(self, text: str) -> None:
        self.access_password_line_edit.setText(text.upper())

    def __access_password_line_edit_finished(self) -> None:
        if len(self.access_password_line_edit.text()) != 8:
            show_message_box("Failed", "Access password must set to 8 hex characters.", success=False)

    def mask_data_line_edit_edited(self, text: str) -> None:
        text = text.upper().replace(' ', '')
        self.mask_data_line_edit.setText(' '.join([text[i:i + 2] for i in range(0, len(text), 2)]).strip())

    def __set_clicked(self) -> None:
        self.set_inventory_filter_thread = SetInventoryFilterThread(self.reader)

        try:
            self.set_inventory_filter_thread.mask_inventory_permission = self.mask_inventory_permission
        except (AssertionError, ValueError) as e:
            show_message_box("Failed", str(e))
            return

        if self.inventory_filter_condition == InventoryFilterCondition.NO_FILTER:
            self.access_password_line_edit.setText("00000000")
            self.mask_start_address_spin_box.setValue(0)
            self.mask_data_line_edit.setText("00 00 00 00 00 00 00 00 00 00 00 00")

        self.set_button.setEnabled(False)

        self.set_inventory_filter_thread.result_set_mask_inventory_permission_signal \
            .connect(self.__receive_signal_result_set_mask_inventory_permission)
        self.set_inventory_filter_thread.start()

    def __receive_signal_result_set_mask_inventory_permission(self, response: MaskInventoryPermission | Exception) -> None:
        self.set_button.setEnabled(True)

        if isinstance(response, MaskInventoryPermission):
            show_message_box("Success", "Successful set inventory filter.", success=True)
        elif isinstance(response, Exception):
            message = str(response)
            if not message:
                message = "Something went wrong, can't set inventory filter."
            show_message_box("Failed", message)
        else:
            show_message_box("Failed", "Can't set inventory filter.", success=False)
