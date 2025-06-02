from time import sleep

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QLabel, QComboBox, QGridLayout, QPushButton, QVBoxLayout, QGroupBox, \
    QSpinBox, QDoubleSpinBox, QCheckBox

from rfid.reader import Reader
from rfid.reader_settings import BaudRate, WorkMode, OutputInterface, MemoryBank, WiegandProtocol, \
    WiegandByteFirstType, REGIONS, Region, ReaderSettings, Frequency, DeviceInfo
from rfid.response import Response, Status, ResponseReaderSettings
from ui.thread.reader_settings_thread import GetReaderSettingsThread, SetReaderSettingsThread, \
    ResetSettingsAndRebootThread
from ui.utils import QHLine, QHexSpinBox, show_message_box


class ReaderSettingsWidget(QWidget):
    work_mode_signal = Signal(type)
    on_reboot_signal = Signal(bool)

    def __init__(self, reader: Reader) -> None:
        super().__init__()

        # GroupBox Reader settings
        reader_settings_group_box = QGroupBox("Reader settings")
        reader_address_label = QLabel("Address")
        reader_address_label.setMinimumWidth(60)
        power_label = QLabel("Power")
        power_label.setMinimumWidth(60)
        baud_rate_label = QLabel("Baud rate")
        baud_rate_label.setMinimumWidth(60)
        frequency_label = QLabel("Region")
        frequency_label.setMinimumWidth(60)
        min_frequency_label = QLabel("Min. frequency")
        min_frequency_label.setMinimumWidth(60)
        max_frequency_label = QLabel("Max. frequency")
        max_frequency_label.setMinimumWidth(60)

        dbm_label = QLabel("dBm")
        dbm_label.setMinimumWidth(45)
        min_mhz_label = QLabel("MHz")
        min_mhz_label.setMinimumWidth(45)
        max_mhz_label = QLabel("MHz")
        max_mhz_label.setMinimumWidth(45)
        reader_address_empty_label = QLabel("")
        reader_address_empty_label.setMinimumWidth(45)
        baud_rate_empty_label = QLabel("")
        baud_rate_empty_label.setMinimumWidth(45)
        frequency_empty_label = QLabel("")
        frequency_empty_label.setMinimumWidth(45)

        self.reader_address_spin_box = QHexSpinBox()
        self.reader_address_spin_box.setMinimumWidth(100)
        self.power_spin_box = QSpinBox()
        self.power_spin_box.setMinimumWidth(100)
        self.baud_rate_combo_box = QComboBox()
        self.baud_rate_combo_box.addItems([str(baud_rate) for baud_rate in BaudRate])
        self.baud_rate_combo_box.setMinimumWidth(100)
        self.frequency_combo_box = QComboBox()
        self.frequency_combo_box.addItems([str(region) for region in REGIONS])
        self.frequency_combo_box.currentTextChanged.connect(self.__on_changed_text_frequency)
        self.frequency_combo_box.setMinimumWidth(100)
        self.min_frequency_spin_box = QDoubleSpinBox()
        self.min_frequency_spin_box.valueChanged.connect(self.__on_changed_value_min_frequency)
        self.min_frequency_spin_box.setDecimals(3)
        self.min_frequency_spin_box.setMinimumWidth(100)
        self.max_frequency_spin_box = QDoubleSpinBox()
        self.max_frequency_spin_box.valueChanged.connect(self.__on_changed_value_max_frequency)
        self.max_frequency_spin_box.setDecimals(3)
        self.max_frequency_spin_box.setMinimumWidth(100)

        self.reader_address_spin_box.setMinimum(0x00)
        self.reader_address_spin_box.setMaximum(0xFE)
        self.power_spin_box.setMinimum(0)
        self.power_spin_box.setMaximum(30)

        reader_settings_grid_layout = QGridLayout()
        # Reader settings - Row 0
        reader_settings_grid_layout.addWidget(reader_address_label, 0, 0)
        reader_settings_grid_layout.addWidget(self.reader_address_spin_box, 0, 1)
        reader_settings_grid_layout.addWidget(reader_address_empty_label, 0, 2)
        reader_settings_grid_layout.addWidget(baud_rate_label, 0, 3)
        reader_settings_grid_layout.addWidget(self.baud_rate_combo_box, 0, 4)
        reader_settings_grid_layout.addWidget(baud_rate_empty_label, 0, 5)
        reader_settings_grid_layout.addWidget(power_label, 0, 6)
        reader_settings_grid_layout.addWidget(self.power_spin_box, 0, 7)
        reader_settings_grid_layout.addWidget(dbm_label, 0, 8)
        # Reader settings - Row 1 (Line)
        reader_settings_grid_layout.addWidget(QHLine(), 1, 0, 1, 9)
        # Reader settings - Row 2
        reader_settings_grid_layout.addWidget(frequency_label, 2, 0)
        reader_settings_grid_layout.addWidget(self.frequency_combo_box, 2, 1)
        reader_settings_grid_layout.addWidget(frequency_empty_label, 2, 2)
        reader_settings_grid_layout.addWidget(min_frequency_label, 2, 3)
        reader_settings_grid_layout.addWidget(self.min_frequency_spin_box, 2, 4)
        reader_settings_grid_layout.addWidget(min_mhz_label, 2, 5)
        reader_settings_grid_layout.addWidget(max_frequency_label, 2, 6)
        reader_settings_grid_layout.addWidget(self.max_frequency_spin_box, 2, 7)
        reader_settings_grid_layout.addWidget(max_mhz_label, 2, 8)

        reader_settings_group_box.setLayout(reader_settings_grid_layout)
        reader_settings_layout = QVBoxLayout()
        reader_settings_layout.addWidget(reader_settings_group_box)

        # GroupBox Output settings
        output_settings_group_box = QGroupBox("Output settings")
        work_mode_label = QLabel("Work mode")
        work_mode_label.setMinimumWidth(60)
        interface_label = QLabel("Interface")
        interface_label.setMinimumWidth(60)
        memory_bank_label = QLabel("Memory bank")
        memory_bank_label.setMinimumWidth(60)
        start_address_label = QLabel("Start address")
        start_address_label.setMinimumWidth(60)
        length_label = QLabel("Length")
        length_label.setMinimumWidth(60)
        buzzer_label = QLabel("Buzzer")
        buzzer_label.setMinimumWidth(60)
        filter_time_label = QLabel("Filter time")
        filter_time_label.setMinimumWidth(60)
        trigger_time_label = QLabel("Trigger time")
        trigger_time_label.setMinimumWidth(60)
        inventory_interval_label = QLabel("Inventory interval")
        inventory_interval_label.setMinimumWidth(60)
        wiegand_label = QLabel("Wiegand")
        wiegand_label.setMinimumWidth(60)

        work_mode_empty_label = QLabel("")
        work_mode_empty_label.setMinimumWidth(45)
        interface_empty_label = QLabel("")
        interface_empty_label.setMinimumWidth(45)
        memory_bank_empty_label = QLabel("")
        memory_bank_empty_label.setMinimumWidth(45)
        start_address_byte_label = QLabel("(in bytes)")
        start_address_byte_label.setMinimumWidth(45)
        length_byte_label = QLabel("(in bytes)")
        length_byte_label.setMinimumWidth(45)
        buzzer_empty_label = QLabel("")
        buzzer_empty_label.setMinimumWidth(45)
        filter_time_sec_label = QLabel("s")
        filter_time_sec_label.setMinimumWidth(45)
        trigger_time_sec_label = QLabel("s")
        trigger_time_sec_label.setMinimumWidth(45)
        inventory_interval_sec_label = QLabel("x 10ms")
        inventory_interval_sec_label.setMinimumWidth(45)

        self.work_mode_combo_box = QComboBox()
        self.work_mode_combo_box.addItems([str(work_mode) for work_mode in WorkMode])
        self.work_mode_combo_box.currentIndexChanged.connect(self.__on_changed_index_work_mode)
        self.work_mode_combo_box.setMinimumWidth(100)
        self.interface_combo_box = QComboBox()
        self.interface_combo_box.addItems([str(interface) for interface in OutputInterface])
        self.interface_combo_box.currentIndexChanged.connect(self.__on_changed_index_interface)
        self.interface_combo_box.setMinimumWidth(100)
        self.memory_bank_combo_box = QComboBox()
        self.memory_bank_combo_box.addItems([str(memory_bank) for memory_bank in MemoryBank])
        self.memory_bank_combo_box.setMinimumWidth(100)
        self.start_address_spin_box = QSpinBox()
        self.start_address_spin_box.setMinimumWidth(100)
        self.length_spin_box = QSpinBox()
        self.length_spin_box.setMinimumWidth(100)
        self.buzzer_check_box = QCheckBox()
        self.buzzer_check_box.setMinimumWidth(100)
        self.filter_time_spin_box = QSpinBox()
        self.filter_time_spin_box.setMinimumWidth(100)
        self.trigger_time_spin_box = QSpinBox()
        self.trigger_time_spin_box.setMinimumWidth(100)
        self.inventory_interval_spin_box = QSpinBox()
        self.inventory_interval_spin_box.setMinimumWidth(100)
        self.wiegand_combo_box = QComboBox()
        self.wiegand_combo_box.addItems([str(wiegand) for wiegand in WiegandProtocol])
        self.wiegand_combo_box.setMinimumWidth(100)
        self.wiegand_byte_first_type_combo_vox = QComboBox()
        self.wiegand_byte_first_type_combo_vox.addItems([str(wiegand_byte_first)
                                                         for wiegand_byte_first in WiegandByteFirstType])
        self.wiegand_byte_first_type_combo_vox.setMinimumWidth(100)

        self.start_address_spin_box.setMinimum(0x00)
        self.start_address_spin_box.setMaximum(0xFF)
        self.length_spin_box.setMinimum(0x00)
        self.length_spin_box.setMaximum(0xFF)
        self.filter_time_spin_box.setMinimum(0x00)
        self.filter_time_spin_box.setMaximum(0xFF)
        self.trigger_time_spin_box.setMinimum(0x00)
        self.trigger_time_spin_box.setMaximum(0xFF)
        self.inventory_interval_spin_box.setMinimum(0x00)
        self.inventory_interval_spin_box.setMaximum(0xFF)

        output_settings_grid_layout = QGridLayout()
        # Output settings - Row 0
        output_settings_grid_layout.addWidget(work_mode_label, 0, 0)
        output_settings_grid_layout.addWidget(self.work_mode_combo_box, 0, 1)
        output_settings_grid_layout.addWidget(work_mode_empty_label, 0, 2)
        output_settings_grid_layout.addWidget(interface_label, 0, 3)
        output_settings_grid_layout.addWidget(self.interface_combo_box, 0, 4)
        output_settings_grid_layout.addWidget(interface_empty_label, 0, 5)
        output_settings_grid_layout.addWidget(memory_bank_label, 0, 6)
        output_settings_grid_layout.addWidget(self.memory_bank_combo_box, 0, 7)
        output_settings_grid_layout.addWidget(memory_bank_empty_label, 0, 8)
        # Output settings - Row 1
        output_settings_grid_layout.addWidget(start_address_label, 1, 0)
        output_settings_grid_layout.addWidget(self.start_address_spin_box, 1, 1)
        output_settings_grid_layout.addWidget(start_address_byte_label, 1, 2)
        output_settings_grid_layout.addWidget(length_label, 1, 3)
        output_settings_grid_layout.addWidget(self.length_spin_box, 1, 4)
        output_settings_grid_layout.addWidget(length_byte_label, 1, 5)
        output_settings_grid_layout.addWidget(buzzer_label, 1, 6)
        output_settings_grid_layout.addWidget(self.buzzer_check_box, 1, 7)
        output_settings_grid_layout.addWidget(buzzer_empty_label, 1, 8)
        # Output settings - Row 2
        output_settings_grid_layout.addWidget(filter_time_label, 2, 0)
        output_settings_grid_layout.addWidget(self.filter_time_spin_box, 2, 1)
        output_settings_grid_layout.addWidget(filter_time_sec_label, 2, 2)
        output_settings_grid_layout.addWidget(trigger_time_label, 2, 3)
        output_settings_grid_layout.addWidget(self.trigger_time_spin_box, 2, 4)
        output_settings_grid_layout.addWidget(trigger_time_sec_label, 2, 5)
        output_settings_grid_layout.addWidget(inventory_interval_label, 2, 6)
        output_settings_grid_layout.addWidget(self.inventory_interval_spin_box, 2, 7)
        output_settings_grid_layout.addWidget(inventory_interval_sec_label, 2, 8)
        # Output settings - Row 3
        output_settings_grid_layout.addWidget(wiegand_label, 3, 0)
        output_settings_grid_layout.addWidget(self.wiegand_combo_box, 3, 1)
        output_settings_grid_layout.addWidget(self.wiegand_byte_first_type_combo_vox, 3, 2)

        output_settings_group_box.setLayout(output_settings_grid_layout)
        output_settings_layout = QVBoxLayout()
        output_settings_layout.addWidget(output_settings_group_box)

        # Button (reset, read, set)
        self.read_button = QPushButton("Get")
        self.read_button.clicked.connect(self.__read_clicked)
        self.read_button.setMinimumHeight(32)
        self.set_button = QPushButton("Set")
        self.set_button.clicked.connect(self.__set_clicked)
        self.set_button.setMinimumHeight(32)
        self.reset_button = QPushButton("Reset settings && reboot")
        self.reset_button.setMinimumHeight(32)
        self.reset_button.clicked.connect(self.__reset_settings_and_reboot_clicked)

        button_grid_layout = QGridLayout()
        button_grid_layout.addWidget(self.read_button, 0, 0)
        button_grid_layout.addWidget(self.set_button, 0, 1)
        button_grid_layout.addWidget(QLabel(), 0, 2, 1, 2)
        button_grid_layout.addWidget(self.reset_button, 0, 5)

        # Combine Layout
        layout = QVBoxLayout()
        layout.addLayout(button_grid_layout)
        layout.addLayout(reader_settings_layout)
        layout.addLayout(output_settings_layout)
        layout.addWidget(QLabel())
        self.setLayout(layout)

        self.reader = reader
        self.get_reader_settings_thread: GetReaderSettingsThread | None = None
        self.set_reader_settings_thread: SetReaderSettingsThread | None = None
        self.reset_settings_and_reboot_thread: ResetSettingsAndRebootThread | None = None
        self.__reader_settings: ReaderSettings | None = None
        self.__device_info: DeviceInfo | None = None

    def close(self) -> None:
        if self.get_reader_settings_thread:
            self.get_reader_settings_thread.terminate()
        if self.set_reader_settings_thread:
            self.set_reader_settings_thread.terminate()
        if self.reset_settings_and_reboot_thread:
            self.reset_settings_and_reboot_thread.terminate()

    def receive_device_info_signal(self, device_info: DeviceInfo) -> None:
        self.device_info = device_info

    @property
    def device_info(self) -> DeviceInfo | None:
        return self.__device_info

    @device_info.setter
    def device_info(self, value: DeviceInfo) -> None:
        self.__device_info = value
        self.power_spin_box.setMaximum(self.__device_info.series.max_power)

    def __baud_rate_changed(self, baud_rate: BaudRate) -> None:
        self.reader.transport.reconnect(baud_rate=baud_rate)

    def __check_is_ready(self) -> None:
        self.on_reboot_signal.emit(True)
        response = None
        for i in range(3):
            sleep(2)
            self.reader.transport.reconnect()
            response = self.reader.init()
            if isinstance(response, Response):
                break
        if response is None:
            show_message_box("Failed", "Failed reconnect to reader after reboot.")
            return
        if response:
            show_message_box("Success", "Reset successfully, reader is ready to use.", success=True)
            self.on_reboot_signal.emit(False)

    def __on_changed_text_frequency(self, text: str) -> None:
        region = Region.from_name(text)

        self.min_frequency_spin_box.setRange(region.start_frequency, region.end_frequency)
        self.min_frequency_spin_box.setSingleStep(region.step)
        self.max_frequency_spin_box.setRange(region.start_frequency, region.end_frequency)
        self.max_frequency_spin_box.setSingleStep(region.step)
        self.min_frequency_spin_box.setValue(region.start_frequency)
        self.max_frequency_spin_box.setValue(region.end_frequency)

    def __on_changed_value_min_frequency(self, value: float) -> None:
        value = round(value, 3)
        region = Region.from_name(self.frequency_combo_box.currentText())
        if value not in region.values:
            show_message_box("Failed", f"{value} not in range.", success=False)
            self.min_frequency_spin_box.setValue(region.start_frequency)

    def __on_changed_value_max_frequency(self, value: float) -> None:
        value = round(value, 3)
        region = Region.from_name(self.frequency_combo_box.currentText())
        if value not in region.values:
            show_message_box("Failed", f"{value} not in range.", success=False)
            self.max_frequency_spin_box.setValue(region.end_frequency)

    def __on_changed_index_work_mode(self, index: int) -> None:
        work_mode = WorkMode(index)
        enabled = work_mode == WorkMode.ACTIVE_MODE or work_mode == WorkMode.TRIGGER_MODE
        self.filter_time_spin_box.setEnabled(enabled)
        self.trigger_time_spin_box.setEnabled(enabled)
        self.inventory_interval_spin_box.setEnabled(enabled)

    def __on_changed_index_interface(self, index: int) -> None:
        interface = OutputInterface.from_index(index)
        is_wiegand = interface == OutputInterface.WIEGAND
        self.wiegand_combo_box.setEnabled(is_wiegand)
        self.wiegand_byte_first_type_combo_vox.setEnabled(is_wiegand)

    def __receive_signal_reader_settings(self, response: ResponseReaderSettings | Exception) -> None:
        self.read_button.setEnabled(True)

        if isinstance(response, ResponseReaderSettings):
            if response.status == Status.SUCCESS:
                self.reader_settings = response.reader_settings
            else:
                show_message_box("Failed", response.status.name, success=False)
        elif isinstance(response, Exception):
            message = str(response)
            if not message:
                message = "Something went wrong, can't get reader settings. If the reader is in Active Mode, " \
                          "consider tagging away from the reader for best communication."
            show_message_box("Failed", message)
        else:
            show_message_box("Failed", "Can't get reader settings. If the reader is in Active Mode, "
                                       "consider tagging away from the reader for best communication.", success=False)

    def __receive_signal_result_set_reader_settings(self, response: ReaderSettings | Exception) -> None:
        self.set_button.setEnabled(True)

        if isinstance(response, ReaderSettings):
            self.reader_settings = response
            show_message_box("Success", "Successful set reader settings", success=True)
        elif isinstance(response, Exception):
            message = str(response)
            if not message:
                message = "Something went wrong, can't set reader settings"
            show_message_box("Failed", message)
        else:
            show_message_box("Failed", "Can't set reader settings", success=False)

    def __receive_signal_reset_settings_and_reboot(self, response: Response | Exception) -> None:
        self.reset_button.setEnabled(True)

        if isinstance(response, Response):
            if response.status == Status.SUCCESS:
                show_message_box("Success", "Successful reset, wait until reader is ready.", success=True)
                self.__check_is_ready()
            else:
                show_message_box("Failed", response.status.name, success=False)
        elif isinstance(response, Exception):
            message = str(response)
            if not message:
                message = "Something went wrong, can't reset reader"
            show_message_box("Failed", message)

    @property
    def reader_settings(self) -> ReaderSettings:
        # Wiegand
        wiegand = self.__reader_settings.wiegand
        output_interface = OutputInterface.from_index(self.interface_combo_box.currentIndex())
        wiegand.is_open = True if output_interface == OutputInterface.WIEGAND else False
        wiegand.protocol = WiegandProtocol(self.wiegand_combo_box.currentIndex())
        wiegand.byte_first_type = WiegandByteFirstType(self.wiegand_byte_first_type_combo_vox.currentIndex())

        # Frequency
        region = Region.from_index(self.frequency_combo_box.currentIndex())
        frequency = Frequency(region,
                              min_frequency=self.min_frequency_spin_box.value(),
                              max_frequency=self.max_frequency_spin_box.value())

        return ReaderSettings(
            address=self.reader_address_spin_box.value(),
            rfid_protocol=self.__reader_settings.rfid_protocol,
            work_mode=WorkMode(self.work_mode_combo_box.currentIndex()),
            output_interface=output_interface,
            baud_rate=BaudRate(self.baud_rate_combo_box.currentIndex()),
            wiegand=wiegand,
            antenna=self.__reader_settings.antenna,
            frequency=frequency,
            power=self.power_spin_box.value(),
            output_memory_bank=MemoryBank(self.memory_bank_combo_box.currentIndex()),
            q_value=self.__reader_settings.q_value,
            session=self.__reader_settings.session,
            output_start_address=self.start_address_spin_box.value(),
            output_length=self.length_spin_box.value(),
            filter_time=self.filter_time_spin_box.value(),
            trigger_time=self.trigger_time_spin_box.value(),
            buzzer_time=self.buzzer_check_box.isChecked(),
            inventory_interval=self.inventory_interval_spin_box.value(),
        )

    @reader_settings.setter
    def reader_settings(self, value: ReaderSettings) -> None:
        if self.__reader_settings is not None and value.baud_rate != self.__reader_settings.baud_rate:
            self.__baud_rate_changed(value.baud_rate)

        self.__reader_settings = value
        self.work_mode_signal.emit(self.__reader_settings.work_mode)

        self.reader_address_spin_box.setValue(value.address)
        self.work_mode_combo_box.setCurrentIndex(value.work_mode.value)
        self.__on_changed_index_work_mode(value.work_mode.value)
        self.interface_combo_box.setCurrentIndex(value.output_interface.index)
        self.baud_rate_combo_box.setCurrentIndex(value.baud_rate.value)
        self.wiegand_combo_box.setCurrentIndex(value.wiegand.protocol.value)
        self.wiegand_byte_first_type_combo_vox.setCurrentIndex(value.wiegand.byte_first_type.value)
        self.frequency_combo_box.setCurrentIndex(value.frequency.region.index)
        self.min_frequency_spin_box.setRange(value.frequency.region.start_frequency,
                                             value.frequency.region.end_frequency)
        self.min_frequency_spin_box.setSingleStep(value.frequency.region.step)
        self.max_frequency_spin_box.setRange(value.frequency.region.start_frequency,
                                             value.frequency.region.end_frequency)
        self.max_frequency_spin_box.setSingleStep(value.frequency.region.step)
        self.min_frequency_spin_box.setValue(value.frequency.min_frequency)
        self.max_frequency_spin_box.setValue(value.frequency.max_frequency)
        self.power_spin_box.setValue(value.power)
        self.memory_bank_combo_box.setCurrentIndex(value.output_memory_bank.value)
        self.start_address_spin_box.setValue(value.output_start_address)
        self.length_spin_box.setValue(value.output_length)
        self.filter_time_spin_box.setValue(value.filter_time)
        self.buzzer_check_box.setChecked(value.buzzer_time)
        self.trigger_time_spin_box.setValue(value.trigger_time)
        self.inventory_interval_spin_box.setValue(value.inventory_interval)

    def __read_clicked(self) -> None:
        self.read_button.setEnabled(False)

        self.get_reader_settings_thread = GetReaderSettingsThread(self.reader)
        self.get_reader_settings_thread.reader_settings_signal.connect(self.__receive_signal_reader_settings)
        self.get_reader_settings_thread.start()

    def __set_clicked(self) -> None:
        self.set_button.setEnabled(False)

        self.set_reader_settings_thread = SetReaderSettingsThread(self.reader)
        self.set_reader_settings_thread.reader_settings = self.reader_settings
        self.set_reader_settings_thread.result_set_reader_settings_signal \
            .connect(self.__receive_signal_result_set_reader_settings)
        self.set_reader_settings_thread.start()

    def __reset_settings_and_reboot_clicked(self) -> None:
        self.reset_button.setEnabled(False)

        self.reset_settings_and_reboot_thread = ResetSettingsAndRebootThread(self.reader)
        self.reset_settings_and_reboot_thread.result_reset_settings_and_reboot_signal \
            .connect(self.__receive_signal_reset_settings_and_reboot)
        self.reset_settings_and_reboot_thread.start()
