from enum import Enum
from rfid.utils import hex_readable, calculate_checksum


HEADER = 0xCF
BROADCAST_ADDRESS = 0xFF


class CommandOption(Enum):
    SET = 0x01
    GET = 0x02


class CommandRequest(Enum):
    MODULE_INIT = 0x0050
    REBOOT = 0x0052
    SET_POWER = 0x0053
    SET_GET_RFID_PROTOCOL = 0x0059
    SET_GET_NETWORK = 0x005F
    SET_GET_REMOTE_NETWORK = 0x0064
    GET_DEVICE_INFO = 0x0070
    SET_ALL_PARAM = 0x0071
    GET_ALL_PARAM = 0x0072
    SET_GET_PERMISSION = 0x0073
    SET_GET_IO_PUT = 0x0074
    SET_GET_WIFI = 0x0075
    RELEASE_CLOSE_RELAY = 0x0077
    INVENTORY_ISO_CONTINUE = 0x0001
    INVENTORY_STOP = 0x0002
    INVENTORY_ACTIVE = 0x0001
    SELECT_MASK = 0x0007
    READ_ISO_TAG = 0x0003
    WRITE_ISO_TAG = 0x0004
    LOCK_ISO_TAG = 0x0005
    KILL_ISO_TAG = 0x0006
    SET_MAX_TEMPERATURE = 0x0060
    GET_CURRENT_TEMPERATURE = 0x0061
    SET_GET_ANTENNA_POWER = 0x0063
    INVENTORY_RANGE = 0x0018
    SET_GET_OUTPUT_PARAMETERS = 0x0074


class Command(object):
    def __init__(self,
                 command: CommandRequest,
                 address=BROADCAST_ADDRESS,
                 data: bytes | bytearray = bytearray()) -> None:
        self.address = address
        self.command = command
        self.data = data

    def serialize(self, with_checksum: bool = True) -> bytes:
        base_data = bytearray(
            [HEADER, self.address]) + \
                    self.command.value.to_bytes(2, "big") + \
                    bytearray([len(self.data)]) + \
                    bytearray(self.data)
        if with_checksum:
            checksum = calculate_checksum(base_data)
            base_data.extend(checksum)
        return base_data

    def __str__(self) -> str:
        return_value = ''
        serialize = self.serialize()
        value = '>>> START REQUEST  ================================'
        return_value = f'{return_value}\n{value}'
        value = f'COMMAND   << {self.command}'
        return_value = f'{return_value}\n{value}'
        if self.data:
            value = f'DATA      << length: ({len(self.data)}) -> {hex_readable(self.data)}'
            return_value = f'{return_value}\n{value}'
        value = f'SERIALIZE << {hex_readable(serialize)}'
        return_value = f'{return_value}\n{value}'
        value = '>>> END REQUEST    ================================'
        return_value = f'{return_value}\n{value}'
        return return_value.strip().upper()


