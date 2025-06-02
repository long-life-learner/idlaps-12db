from dataclasses import dataclass
from enum import Enum
from typing import TypeVar, Type

from rfid.utils import hex_readable, ip_string

T = TypeVar('T', bound='Parent')


class RfidProtocol(Enum):
    """Only for ISO 18000-6C"""
    ISO_18000_6C = 0x00
    GBT_29768 = 0x01
    GJB_7377_1 = 0x02

    _ignore_ = ["DISPLAY_STRINGS"]
    DISPLAY_STRINGS = []

    def __str__(self) -> str:
        return RfidProtocol.DISPLAY_STRINGS[self.value]


RfidProtocol.DISPLAY_STRINGS = [
    "ISO 18000-6C",
    "GB/T 29768",
    "GJB 7377.1"
]


class BaudRate(Enum):
    BPS_9600 = 0x00
    BPS_19200 = 0x01
    BPS_38400 = 0x02
    BPS_57600 = 0x03
    BPS_115200 = 0x04

    _ignore_ = ["INT"]
    INT = []

    def __str__(self) -> str:
        return f'{self.to_int} bps'

    @property
    def to_int(self) -> int:
        return self.INT[self.value]

    @classmethod
    def from_int(cls, value: int) -> T:
        for baud_rate in BaudRate:
            if baud_rate.to_int == value:
                return baud_rate


BaudRate.INT = [9600, 19200, 38400, 57600, 115200]


@dataclass
class ReaderSeries:
    name: str
    enabled_select_query_parameters: bool
    enabled_stop_after_by_cycles: bool
    enabled_read_write: bool
    enabled_network_settings: bool
    enabled_inventory_filter: bool
    enabled_output_control: bool
    enabled_set_temperature: bool
    max_power: int


@dataclass
class DeviceInfo:
    hardware_version: bytes
    firmware_version: bytes
    serial_number: bytes
    series: ReaderSeries = None

    def __post_init__(self) -> None:
        firmware_version_ascii = self.firmware_version.decode("ascii").strip()
        if 'UHF Access Reader'.lower() in firmware_version_ascii.lower():
            self.series = ReaderSeries("Electron EL-UHF-RC3 Series", True, True, True, False, False, False, True, 33)
        elif 'UHF Prime Reader'.lower() in firmware_version_ascii.lower():
            self.series = ReaderSeries("Electron EL-UHF-RC4 Series", False, False, False, True, True, True, False, 30)

    @classmethod
    def from_bytes(cls: Type[T], data: bytes) -> T:
        # Reserve
        # reserve_1: bytes = data[76:108]
        # reserve_2: bytes = data[108:140]
        # reserve_3: bytes = data[140:152]
        return DeviceInfo(data[0:32], data[32:64], data[64:76])


class Relay(Enum):
    OPEN = 0x01
    CLOSE = 0x02

    _ignore_ = ["DISPLAY_STRINGS"]
    DISPLAY_STRINGS = []

    def __str__(self) -> str:
        return Relay.DISPLAY_STRINGS[self.value - 1]

    def to_index(self) -> int:
        return self.value - 1


Relay.DISPLAY_STRINGS = ["Open", "Close"]


class WorkMode(Enum):
    ANSWER_MODE = 0x00
    ACTIVE_MODE = 0x01
    TRIGGER_MODE = 0x02

    _ignore_ = ["DISPLAY_STRINGS"]
    DISPLAY_STRINGS = []

    def __str__(self) -> str:
        return WorkMode.DISPLAY_STRINGS[self.value]


WorkMode.DISPLAY_STRINGS = ["Answer Mode", "Active Mode", "Trigger Mode"]


class OutputInterface(Enum):
    WIEGAND = 0x99
    RS232 = 0x80
    RS485 = 0x40
    RJ45 = 0x20
    # WiFi = 0x10
    USB = 0x01
    KEYBOARD = 0x02
    # CDC_COM = 0x04

    _ignore_ = ["DISPLAY_STRINGS"]

    DISPLAY_STRINGS = []

    @property
    def index(self) -> int:
        for index, value in enumerate(OutputInterface):
            if self == value:
                return index

    def __str__(self) -> str:
        return OutputInterface.DISPLAY_STRINGS[self.index]

    @classmethod
    def from_index(cls: Type[T], index: int) -> T:
        for i, value in enumerate(OutputInterface):
            if index == i:
                return value


OutputInterface.DISPLAY_STRINGS = [
    "Wiegand",
    "RS232",
    "RS485",
    "RJ45",
    "USB",
    "Keyboard",
    # "CDC_COM"
]


class Session(Enum):
    SESSION_0 = 0x00
    SESSION_1 = 0x01
    SESSION_2 = 0x02
    SESSION_3 = 0x03

    _ignore_ = ["DISPLAY_STRINGS"]
    DISPLAY_STRINGS = []

    def __str__(self) -> str:
        return Session.DISPLAY_STRINGS[self.value]


Session.DISPLAY_STRINGS = [
    "S0",
    "S1",
    "S2",
    "S3"
]


class MemoryBank(Enum):
    PASSWORD = 0x00
    EPC = 0x01
    TID = 0x02
    USER = 0x03

    _ignore_ = ["DISPLAY_STRINGS"]
    DISPLAY_STRINGS = []

    def __str__(self) -> str:
        return MemoryBank.DISPLAY_STRINGS[self.value]


MemoryBank.DISPLAY_STRINGS = [
    "Password",
    "EPC",
    "TID",
    "User"
]


class LockMemoryBank(Enum):
    KILL_PASSWORD = 0x00
    ACCESS_PASSWORD = 0x01
    EPC = 0x02
    # TID = 0x03  # Unlock/lock response is None
    USER = 0x04

    _ignore_ = ["DISPLAY_STRINGS"]
    DISPLAY_STRINGS = []

    def to_index(self) -> int:
        for index, lock_memory_bank in enumerate(LockMemoryBank):
            if lock_memory_bank.value == self.value:
                return index

    @classmethod
    def from_index(cls: Type[T], index: int) -> T:
        for i, value in enumerate(LockMemoryBank):
            if index == i:
                return value

    def __str__(self) -> str:
        return LockMemoryBank.DISPLAY_STRINGS[self.to_index()]


LockMemoryBank.DISPLAY_STRINGS = [
    "Access Password",
    "Kill Password",
    "EPC",
    "User"
]


class LockAction(Enum):
    UNLOCK = 0x00
    UNLOCK_PERMANENT = 0x01
    LOCK = 0x02
    LOCK_PERMANENT = 0x03

    _ignore_ = ["DISPLAY_STRINGS"]
    DISPLAY_STRINGS = []

    def __str__(self) -> str:
        return LockAction.DISPLAY_STRINGS[self.value]


LockAction.DISPLAY_STRINGS = [
    "Unlock",
    "Unlock (Permanent)",
    "Lock",
    "Lock (Permanent)",
]


class Region:
    def __init__(self, name: str, value: int,
                 start_frequency: float, end_frequency: float, default_channel_number: int) -> None:
        self.name = name
        self.value = value
        self.start_frequency = start_frequency
        self.end_frequency = end_frequency
        self.default_channel_number = default_channel_number
        self.step = round((self.end_frequency - self.start_frequency) / (self.default_channel_number - 1), 2)

    def __str__(self) -> str:
        return self.name

    @property
    def index(self) -> int:
        for index, region in enumerate(REGIONS):
            if self.value == region.value:
                return index

    @property
    def values(self) -> list[float]:
        return [round(self.start_frequency + i * self.step, 3) for i in range(self.default_channel_number)]

    @classmethod
    def from_value(cls: Type[T], value: int) -> T:
        for region in REGIONS:
            if region.value != value:
                continue
            return region

    @classmethod
    def from_name(cls: Type[T], name: str) -> T:
        for region in REGIONS:
            if region.name != name:
                continue
            return region

    @classmethod
    def from_index(cls: Type[T], index: int) -> T:
        for i, region in enumerate(REGIONS):
            if i != index:
                continue
            return region


REGION_CUSTOM = Region("Custom", 0x00, 840, 960, 0)  # ? CN-nya?
REGION_USA = Region("USA", 0x01, 902.75, 927.25, 50)
REGION_KOREA = Region("Korea", 0x02, 917.1, 923.3, 32)
REGION_EUROPE = Region("Europe", 0x03, 865.1, 867.9, 15)
REGION_JAPAN = Region("Japan", 0x04, 952.2, 953.6, 8)
REGION_MALAYSIA = Region("Malaysia", 0x05, 919.5, 922.5, 7)
REGION_EUROPE_3 = Region("Europe 3", 0x06, 865.7, 867.5, 4)
REGION_CHINA_1 = Region("China 1", 0x07, 840.125, 844.875, 20)
REGION_CHINA_2 = Region("China 2", 0x08, 920.125, 924.875, 20)
REGIONS = [REGION_USA, REGION_KOREA, REGION_EUROPE, REGION_JAPAN, REGION_MALAYSIA,
           REGION_EUROPE_3, REGION_CHINA_1, REGION_CHINA_2]


@dataclass
class Frequency:
    region: Region
    min_frequency: float
    max_frequency: float

    @property
    def channel_number(self) -> int:
        hop = 1
        temp = self.min_frequency
        while True:  # REFACTOR
            if temp == self.max_frequency:
                return hop
            temp = round(temp + self.region.step, 3)
            hop += 1

    @classmethod
    def from_bytes(cls: Type[T], data: bytes) -> T:
        assert len(data) == 8
        region = Region.from_value(data[0])
        start_fred = int.from_bytes(data[3:5], "big") / 1000
        channel_number = data[-1]
        step = int.from_bytes(data[5:7], "big")
        min_frequency_int = int.from_bytes(data[1:3], "big")
        min_frequency = min_frequency_int + start_fred
        max_frequency = min_frequency + (channel_number - 1) * step / 1000
        return Frequency(region, min_frequency, max_frequency)

    def to_command_data(self) -> bytes:
        assert self.min_frequency <= self.max_frequency

        step: int = int(self.region.step * 1000)
        min_frequency_int: int = int(self.min_frequency)
        min_frequency_fraction: int = int((self.min_frequency - min_frequency_int) * 1000)

        data = bytearray([self.region.value])
        data.extend(min_frequency_int.to_bytes(2, "big"))
        data.extend(min_frequency_fraction.to_bytes(2, "big"))
        data.extend(step.to_bytes(2, "big"))
        data.extend(self.channel_number.to_bytes(1, "big"))
        return data

    def __str__(self) -> str:
        return_value = ''
        value = f'REGION        >> {self.region}'
        return_value = f'{return_value}\n{value}'
        value = f'MIN FREQUENCY >> {self.min_frequency}'
        return_value = f'{return_value}\n{value}'
        value = f'MAX FREQUENCY >> {self.max_frequency}'
        return_value = f'{return_value}\n{value}'
        return return_value.strip().upper()


class WiegandProtocol(Enum):
    WG_26 = 0x00
    WG_34 = 0x01

    _ignore_ = ["DISPLAY_STRINGS"]
    DISPLAY_STRINGS = []

    def __str__(self) -> str:
        return WiegandProtocol.DISPLAY_STRINGS[self.value]


WiegandProtocol.DISPLAY_STRINGS = ["WG26", "WG34"]


class WiegandByteFirstType(Enum):
    LOW_BYTE_FIRST = 0x00
    HIGH_BYTE_FIRST = 0x01

    _ignore_ = ["DISPLAY_STRINGS"]
    DISPLAY_STRINGS = []

    def __str__(self) -> str:
        return WiegandByteFirstType.DISPLAY_STRINGS[self.value]


WiegandByteFirstType.DISPLAY_STRINGS = ["Low byte first", "High byte first"]


@dataclass
class Wiegand:
    is_open: bool
    protocol: WiegandProtocol
    byte_first_type: WiegandByteFirstType

    @classmethod
    def from_bytes(cls: Type[T], data: int) -> T:
        bits: list[int] = [int(x) for x in list('{0:08b}'.format(data))]
        # bit_4, bit_3, bit_2, bit_1, bit_0 = bits[3:8]  # Reserved
        return Wiegand(bool(bits[0]), WiegandProtocol(bits[1]), WiegandByteFirstType(bits[2]))

    def to_int(self) -> int:
        bits_int = [int(self.is_open), self.protocol.value, self.byte_first_type.value,
                    0, 0, 0, 0, 0]
        bits_str = ''.join(str(bit) for bit in bits_int)
        return int(bits_str, 2)

    def __str__(self) -> str:
        return f'Wiegand -> is_open: {self.is_open}, ' \
               f'protocol: {self.protocol}, byte_first_type: {self.byte_first_type}'


@dataclass
class Antenna:
    ant_8: bool
    ant_7: bool
    ant_6: bool
    ant_5: bool
    ant_4: bool
    ant_3: bool
    ant_2: bool
    ant_1: bool

    @classmethod
    def from_bytes(cls: Type[T], data: int) -> T:
        bits = [bool(int(x)) for x in list('{0:08b}'.format(data))]
        ant_8, ant_7, ant_6, ant_5, ant_4, ant_3, ant_2, ant_1 = bits
        return Antenna(ant_8, ant_7, ant_6, ant_5, ant_4, ant_3, ant_2, ant_1)

    def to_int(self) -> int:
        bits_int = [int(self.ant_8), int(self.ant_7), int(self.ant_6), int(self.ant_5),
                    int(self.ant_4), int(self.ant_3), int(self.ant_2), int(self.ant_1)]
        bits_str = ''.join(str(bit) for bit in bits_int)
        return int(bits_str, 2)

    def __str__(self) -> str:
        return f'Antenna: ant 1({self.ant_1}) -> ant 2({self.ant_2}) -> ant 3({self.ant_3}) -> ant 4({self.ant_4})' \
               f' -> ant 5({self.ant_5}) -> ant 6({self.ant_6}) -> ant 7({self.ant_7}) -> ant 8({self.ant_8})'


@dataclass
class ReaderSettings:
    address: int
    rfid_protocol: RfidProtocol
    work_mode: WorkMode
    output_interface: OutputInterface
    baud_rate: BaudRate
    wiegand: Wiegand
    antenna: Antenna
    frequency: Frequency
    power: int
    output_memory_bank: MemoryBank
    q_value: int
    session: Session
    output_start_address: int
    output_length: int
    filter_time: int
    trigger_time: int
    buzzer_time: int
    inventory_interval: int

    def __post_init__(self):
        assert 0x00 <= self.address <= 0xFF
        assert 0 <= self.power <= 33
        assert 0 <= self.q_value <= 15
        assert 0x00 <= self.output_start_address <= 0xFF
        assert 0x00 <= self.output_length <= 0xFF
        assert 0x00 <= self.filter_time <= 0xFF
        assert 0x00 <= self.trigger_time <= 0xFF
        assert 0x00 <= self.buzzer_time <= 0xFF
        assert 0x00 <= self.inventory_interval <= 0xFF

    @classmethod
    def from_bytes(cls: Type[T], data: bytes) -> T:
        wiegand = Wiegand.from_bytes(data[5])
        output_interface = OutputInterface.WIEGAND if wiegand.is_open else OutputInterface(data[3])
        return ReaderSettings(data[0], RfidProtocol(data[1]), WorkMode(data[2]), output_interface,
                              BaudRate(data[4]), wiegand, Antenna.from_bytes(data[6]),
                              Frequency.from_bytes(data[7:15]), data[15], MemoryBank(data[16]), data[17],
                              Session(data[18]), data[19], data[20], data[21], data[22], bool(data[23]), data[24])

    def to_command_data(self) -> bytes:
        # Wiegand
        wiegand = self.wiegand
        if self.output_interface == OutputInterface.WIEGAND:
            wiegand.is_open = True
        output_interface = OutputInterface.RS232 \
            if self.output_interface == OutputInterface.WIEGAND else self.output_interface

        data = bytearray([self.address, self.rfid_protocol.value, self.work_mode.value,
                          output_interface.value, self.baud_rate.value,
                          wiegand.to_int(), self.antenna.to_int()])
        data.extend(self.frequency.to_command_data())
        data.extend([self.power, self.output_memory_bank.value, self.q_value, self.session.value,
                     self.output_start_address, self.output_length,
                     self.filter_time, self.trigger_time, self.buzzer_time, self.inventory_interval])
        return data

    def __str__(self) -> str:
        return_value = ''
        value = '<<< START READER SETTINGS ================================'
        return_value = f'{return_value}\n{value}'
        value = f'ADDRESS            >> {hex(self.address)}'
        return_value = f'{return_value}\n{value}'
        value = f'RFID PROTOCOL      >> {self.rfid_protocol}'
        return_value = f'{return_value}\n{value}'
        value = f'WORK MODE          >> {self.work_mode}'
        return_value = f'{return_value}\n{value}'
        value = f'OUT INTERFACE      >> {self.output_interface}'
        return_value = f'{return_value}\n{value}'
        value = f'BAUD RATE          >> {self.baud_rate}'
        return_value = f'{return_value}\n{value}'
        value = f'WIEGAND            >> {self.wiegand}'
        return_value = f'{return_value}\n{value}'
        value = f'ANTENNA            >> {self.antenna}'
        return_value = f'{return_value}\n{value}'
        value = f'FREQUENCY          >>\n{self.frequency}'
        return_value = f'{return_value}\n{value}'
        value = f'POWER              >> {self.power}'
        return_value = f'{return_value}\n{value}'
        value = f'OUT MEMORY BANK    >> {self.output_memory_bank}'
        return_value = f'{return_value}\n{value}'
        value = f'Q VALUE            >> {self.q_value}'
        return_value = f'{return_value}\n{value}'
        value = f'SESSION            >> {self.session}'
        return_value = f'{return_value}\n{value}'
        value = f'OUT START ADDRESS  >> {self.output_start_address}'
        return_value = f'{return_value}\n{value}'
        value = f'OUT LENGTH         >> {self.output_length}'
        return_value = f'{return_value}\n{value}'
        value = f'FILTER TIME        >> {self.filter_time}'
        return_value = f'{return_value}\n{value}'
        value = f'TRIGGER TIME       >> {self.trigger_time}'
        return_value = f'{return_value}\n{value}'
        value = f'BUZZER TIME        >> {self.buzzer_time}'
        return_value = f'{return_value}\n{value}'
        value = f'INVENTORY INTERVAL >> {self.inventory_interval}'
        return_value = f'{return_value}\n{value}'
        value = '<<< END READER SETTINGS   ================================'
        return_value = f'{return_value}\n{value}'
        return return_value.strip().upper()


@dataclass
class NetworkSettings:
    ip_address: bytes
    mac_address: bytes
    port: int
    netmask: bytes
    gateway: bytes

    def __post_init__(self):
        assert len(self.ip_address) == 4
        assert len(self.mac_address) == 6
        assert 0x00 <= self.port <= 0xFFFF
        assert len(self.netmask) == 4
        assert len(self.gateway) == 4

    @classmethod
    def from_bytes(cls: Type[T], data: bytes) -> T:
        assert len(data) == 20

        return NetworkSettings(data[0:4], data[4:10], int.from_bytes(data[10:12], "big"), data[12:16], data[16:20])

    def to_command_data(self) -> bytes:
        data = bytearray(self.ip_address)
        data.extend(self.mac_address)
        data.extend(self.port.to_bytes(2, "big"))
        data.extend(self.netmask)
        data.extend(self.gateway)
        return data

    def __str__(self) -> str:
        return_value = ''
        value = '<<< START NETWORK SETTINGS ================================'
        return_value = f'{return_value}\n{value}'
        value = f'IP ADDRESS  >> {ip_string(self.ip_address)}'
        return_value = f'{return_value}\n{value}'
        value = f'MAC ADDRESS >> {hex_readable(self.mac_address)}'
        return_value = f'{return_value}\n{value}'
        value = f'PORT        >> {self.port}'
        return_value = f'{return_value}\n{value}'
        value = f'NETMASK     >> {ip_string(self.netmask)}'
        return_value = f'{return_value}\n{value}'
        value = f'GATEWAY     >> {ip_string(self.gateway)}'
        return_value = f'{return_value}\n{value}'
        value = '<<< END NETWORK SETTINGS   ================================'
        return_value = f'{return_value}\n{value}'
        return return_value.strip().upper()


@dataclass
class RemoteNetworkSettings:
    enable: bool
    ip_address: bytes
    port: int
    heart_time: int

    def __post_init__(self):
        assert isinstance(self.enable, bool)
        assert len(self.ip_address) == 4
        assert 0x00 <= self.port <= 0xFFFF
        assert 0x00 <= self.heart_time <= 0xFF

    @classmethod
    def from_bytes(cls: Type[T], data: bytes) -> T:
        assert len(data) == 8

        return RemoteNetworkSettings(bool(data[0]), data[1:5], int.from_bytes(data[5:7], "big"), data[7])

    def to_command_data(self) -> bytes:
        data = bytearray([int(self.enable)])
        data.extend(self.ip_address)
        data.extend(self.port.to_bytes(2, "big"))
        data.extend([self.heart_time])
        return data

    def __str__(self) -> str:
        return_value = ''
        value = '<<< START REMOTE NETWORK SETTINGS ================================'
        return_value = f'{return_value}\n{value}'
        value = f'ENABLE     >> {self.enable}'
        return_value = f'{return_value}\n{value}'
        value = f'IP ADDRESS >> {ip_string(self.ip_address)}'
        return_value = f'{return_value}\n{value}'
        value = f'PORT       >> {self.port}'
        return_value = f'{return_value}\n{value}'
        value = f'HEART TIME >> {self.heart_time}'
        return_value = f'{return_value}\n{value}'
        value = '<<< END REMOTE NETWORK SETTINGS   ================================'
        return_value = f'{return_value}\n{value}'
        return return_value.strip().upper()


class StopAfter(Enum):
    """\
    TIME: int = According to the time (in seconds)

    NUMBER: int = According to the number or cycles
    """
    TIME = 0x00
    NUMBER = 0x01

    _ignore_ = ["DISPLAY_STRINGS", "UNIT_STRINGS"]
    DISPLAY_STRINGS = []
    UNIT_STRINGS = []

    def __str__(self) -> str:
        return StopAfter.DISPLAY_STRINGS[self.value]

    @property
    def unit(self) -> str:
        return StopAfter.UNIT_STRINGS[self.value]


StopAfter.DISPLAY_STRINGS = [
    "Time",
    "Number"
]

StopAfter.UNIT_STRINGS = [
    "seconds",
    "cycles"
]


class AnswerModeInventoryParameter:
    def __init__(self, stop_after: StopAfter, value: int) -> None:
        self.stop_after = stop_after
        self.value = value

    def __str__(self) -> str:
        return f'AnswerModeInventoryParameter(stop_after: {self.stop_after}, value: {self.value})'


class MaskInventoryPermissionCondition(Enum):
    PASSWORD_OR_MASK = 0x00
    PASSWORD_AND_MASK = 0x01

    _ignore_ = ["DISPLAY_STRINGS"]
    DISPLAY_STRINGS = []

    def __str__(self) -> str:
        return MaskInventoryPermissionCondition.DISPLAY_STRINGS[self.value]


MaskInventoryPermissionCondition.DISPLAY_STRINGS = [
    "Password OR Mask",
    "Password AND Mask"
]


@dataclass
class MaskInventoryPermission:
    enable_access_password: bool = False
    enable_mask: bool = False
    mask_start_address: int = 0
    condition: MaskInventoryPermissionCondition = MaskInventoryPermissionCondition.PASSWORD_OR_MASK
    mask: bytes = bytes(12)
    access_password: bytes = bytes(4)

    def __str__(self) -> str:
        return f"MaskInventoryPermission(\n- enable_access_password: {self.enable_access_password}\n" \
               f"- enable_mask: {self.enable_mask}\n- mask_start_address: {self.mask_start_address}\n" \
               f"- condition: {self.condition}\n- mask: {hex_readable(self.mask)}\n" \
               f"- access_password: {hex_readable(self.access_password)}\n)"

    def to_command_data(self) -> bytes:
        assert len(self.access_password) == 4
        assert len(self.mask) <= 12

        mask_send = bytearray()
        mask_send.extend(self.mask)
        if len(mask_send) < 12:
            mask_send.extend(bytes(12 - len(mask_send)))

        data = bytearray()
        data.extend([int(self.enable_access_password)])
        data.extend(self.access_password)
        data.extend([int(self.enable_mask)])
        data.extend([self.mask_start_address, len(self.mask)])
        data.extend(mask_send)
        data.extend([self.condition.value])
        return data

    @classmethod
    def from_bytes(cls: Type[T], data: bytes) -> T:
        return MaskInventoryPermission(
            enable_access_password=bool(data[0]),
            access_password=data[1:5],
            enable_mask=bool(data[5]),
            mask_start_address=data[6],
            # mask_length=data[7],
            mask=data[8:20],
            condition=MaskInventoryPermissionCondition(data[20]),
        )


class QuerySelect(Enum):
    ALL_0 = 0x00
    ALL_1 = 0x01
    NOT_SL = 0x02
    SL = 0x03

    _ignore_ = ["DISPLAY_STRINGS"]
    DISPLAY_STRINGS = []

    def __str__(self) -> str:
        return QuerySelect.DISPLAY_STRINGS[self.value]


QuerySelect.DISPLAY_STRINGS = [
    "ALL",
    "ALL",
    "~SL",
    "SL"
]


class Target(Enum):
    A = 0x00
    B = 0x01

    _ignore_ = ["DISPLAY_STRINGS"]
    DISPLAY_STRINGS = []

    def __str__(self) -> str:
        return Target.DISPLAY_STRINGS[self.value]


Target.DISPLAY_STRINGS = [
    "A", "B"
]


@dataclass
class QueryParameters:
    query_select: QuerySelect
    session: Session
    target: Target
    protocol: int = 0

    def __str__(self) -> str:
        return f"QueryParameters(protocol: {self.protocol}, query_select: {self.query_select}, " \
               f"session: {self.session}, target: {self.target})"

    @classmethod
    def from_bytes(cls: Type[T], data: bytes) -> T:
        return QueryParameters(
            protocol=data[0],
            query_select=QuerySelect(data[1]),
            session=Session(data[2]),
            target=Target(data[3]),
        )

    def to_command_data(self) -> bytes:
        return bytearray([self.protocol, self.query_select.value, self.session.value, self.target.value])


class Truncate(Enum):
    DO_NOT_TRUNCATE = 0x00  # No
    CUT_OFF = 0x01  # Yes


class SelectAction(Enum):
    MATCH_SL_OR_A_ELSE_NON_SL_OR_B = 0x00
    MATCH_SL_OR_A = 0x01
    NOT_MATCH_NON_SL_OR_B = 0x02
    MATCH_NEG_SL_OR_A_TO_B_B_TO_A = 0x03
    MATCH_NON_SL_OR_B_AND_NOT_SL_OR_A = 0x04
    MATCH_NON_SL_OR_B = 0x05
    NOT_MATCH_SL_OR_A = 0x06
    NOT_MATCH_NEG_SL_OR_A_TO_B_B_TO_A = 0x07


class SelectMemoryBank(Enum):
    EPC = 0x10
    TID = 0x20
    USER = 0x30

    _ignore_ = ["DISPLAY_STRINGS"]
    DISPLAY_STRINGS = []

    def to_index(self) -> int:
        for index, memory_bank in enumerate(SelectMemoryBank):
            if memory_bank.value == self.value:
                return index

    @classmethod
    def from_index(cls: Type[T], index: int) -> T:
        for i, value in enumerate(SelectMemoryBank):
            if index == i:
                return value

    def __str__(self) -> str:
        return SelectMemoryBank.DISPLAY_STRINGS[self.to_index()]


SelectMemoryBank.DISPLAY_STRINGS = [
    "EPC",
    "TID",
    "User"
]


class SelectTarget(Enum):
    SESSION_0 = 0x00
    SESSION_1 = 0x01
    SESSION_2 = 0x02
    SESSION_3 = 0x03
    SL = 0x04

    _ignore_ = ["DISPLAY_STRINGS"]
    DISPLAY_STRINGS = []

    def __str__(self) -> str:
        return SelectTarget.DISPLAY_STRINGS[self.value]


SelectTarget.DISPLAY_STRINGS = [
    "S0",
    "S1",
    "S2",
    "S3",
    "SL",
]


@dataclass
class SelectParameters:
    target: SelectTarget
    truncate: bool
    action: SelectAction
    memory_bank: SelectMemoryBank
    start_address: int  # In bits
    mask: bytes = bytes()
    length: int = 0 # In bits
    protocol: int = 0

    def __str__(self) -> str:
        return f"SelectParameters(\nprotocol: {self.protocol},\ntarget: {self.target},\n" \
               f"truncate: {self.truncate},\naction: {self.action},\nmemory_bank: {self.memory_bank},\n" \
               f"start_address: {self.start_address},\nlength: {self.length},\n" \
               f"mask: {hex_readable(self.mask)}\n)"

    @classmethod
    def from_bytes(cls: Type[T], data: bytes) -> T:
        return SelectParameters(
            protocol=data[0],
            target=SelectTarget(data[1]),
            truncate=bool(data[2]),
            action=SelectAction(data[3]),
            memory_bank=SelectMemoryBank(data[4]),
            start_address=int.from_bytes(data[5:7], "big"),
            length=data[7],
            mask=data[8:],
        )

    def to_command_data(self) -> bytes:
        self.length = len(self.mask) * 8
        data = bytearray([self.protocol, self.target.value, self.truncate,
                          self.action.value, self.memory_bank.value])
        data.extend(self.start_address.to_bytes(2, "big"))
        data.extend(bytearray([self.length]))
        data.extend(self.mask)
        return data


class OutputProtocolType(Enum):
    MOD_BUS = 0x00
    ASCII = 0x01
    HEX = 0x02

    _ignore_ = ["DISPLAY_STRINGS"]
    DISPLAY_STRINGS = []

    def __str__(self) -> str:
        return OutputProtocolType.DISPLAY_STRINGS[self.value]


OutputProtocolType.DISPLAY_STRINGS = [
    "ModBus",
    "ASCII",
    "Hex",
]


class TriggerWay(Enum):
    LOW_LEVEL = 0x00
    HIGH_LEVEL = 0x01

    _ignore_ = ["DISPLAY_STRINGS"]
    DISPLAY_STRINGS = []

    def __str__(self) -> str:
        return TriggerWay.DISPLAY_STRINGS[self.value]


TriggerWay.DISPLAY_STRINGS = [
    "Low level (< 0.5v)",
    "High level (2v ~ 5v)",
]


@dataclass
class OutputControl:
    enable_relay: bool = False
    relay_valid_time: int = 3
    enable_relay_power: bool = False
    trigger_way: TriggerWay = TriggerWay.HIGH_LEVEL
    enable_buffer: bool = False
    enable_protocol: bool = False
    protocol_type: OutputProtocolType = OutputProtocolType.ASCII
    protocol_format: bytes = bytes(10)

    def __str__(self) -> str:
        return f"OutputControl(enable_relay: {self.enable_relay}, " \
               f"relay_valid_time: {self.relay_valid_time}, enable_relay_power: {self.enable_relay_power}, " \
               f"trigger_way: {self.trigger_way}, " \
               f"enable_buffer: {self.enable_buffer}, enable_protocol: {self.enable_protocol}, " \
               f"protocol_type: {self.protocol_type}, protocol_format: {hex_readable(self.protocol_format)})"

    def to_command_data(self) -> bytes:
        protocol_format_send = bytearray()
        protocol_format_send.extend(self.protocol_format)
        if len(protocol_format_send) < 10:
            protocol_format_send.extend(bytes(10 - len(protocol_format_send)))

        data = bytearray()
        data.extend([int(self.enable_relay), self.relay_valid_time, int(self.enable_relay_power),
                     self.trigger_way.value, int(self.enable_buffer), int(self.enable_protocol),
                     self.protocol_type.value])
        data.extend(protocol_format_send)
        return data

    @classmethod
    def from_bytes(cls: Type[T], data: bytes) -> T:
        return OutputControl(
            enable_relay=bool(data[0]),
            relay_valid_time=data[1],
            enable_relay_power=bool(data[2]),
            trigger_way=TriggerWay(data[3]),
            enable_buffer=bool(data[4]),
            enable_protocol=bool(data[5]),
            protocol_type=OutputProtocolType(data[6]),
            protocol_format=data[7:],
        )



