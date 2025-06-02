from dataclasses import dataclass
from rfid.status import Status, TagStatus
from rfid.utils import hex_readable


@dataclass
class ReadMemory:
    tag_status: TagStatus
    antenna: int
    crc: bytes
    pc: bytes
    epc_length: int
    epc: bytes
    data_word_length: int
    data: bytes
    count: int = 1

    def __str__(self) -> str:
        return f'ReadMemory(tag_status: {self.tag_status}, ' \
               f'antenna: {self.antenna}, crc: {hex_readable(self.crc)}, ' \
               f'pc: {hex_readable(self.pc)}, epc_length: {self.epc_length}, ' \
               f'epc: {hex_readable(self.epc)}, data_word_length: {self.data_word_length}, ' \
               f'data: {hex_readable(self.data)})'


@dataclass
class WriteMemory:
    tag_status: TagStatus
    antenna: int
    crc: bytes
    pc: bytes
    epc_length: int
    epc: bytes
    count: int = 1

    def __str__(self) -> str:
        return f'WriteMemory(tag_status: {self.tag_status}, ' \
               f'antenna: {self.antenna}, crc: {hex_readable(self.crc)}, ' \
               f'pc: {hex_readable(self.pc)}, epc_length: {self.epc_length}, ' \
               f'epc: {hex_readable(self.epc)})'


@dataclass
class LockMemory:
    tag_status: TagStatus
    antenna: int
    crc: bytes
    pc: bytes
    epc_length: int
    epc: bytes
    count: int = 1

    def __str__(self) -> str:
        return f'LockMemory(tag_status: {self.tag_status}, ' \
               f'antenna: {self.antenna}, crc: {hex_readable(self.crc)}, ' \
               f'pc: {hex_readable(self.pc)}, epc_length: {self.epc_length}, ' \
               f'epc: {hex_readable(self.epc)})'


@dataclass
class KillTag:
    tag_status: TagStatus
    antenna: int
    crc: bytes
    pc: bytes
    epc_length: int
    epc: bytes
    count: int = 1

    def __str__(self) -> str:
        return f'KillTag(tag_status: {self.tag_status}, ' \
               f'antenna: {self.antenna}, crc: {hex_readable(self.crc)}, ' \
               f'pc: {hex_readable(self.pc)}, epc_length: {self.epc_length}, ' \
               f'epc: {hex_readable(self.epc)})'
