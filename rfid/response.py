from logging import getLogger
from rfid.command import CommandRequest, HEADER, CommandOption
from rfid.read_write import ReadMemory, WriteMemory, LockMemory, KillTag
from rfid.reader_settings import RfidProtocol, DeviceInfo, ReaderSettings, NetworkSettings, RemoteNetworkSettings, \
    MaskInventoryPermission, OutputControl, SelectParameters, QueryParameters
from rfid.tag import Tag
from rfid.utils import calculate_checksum, hex_readable
from rfid.status import Status, InventoryStatus, TagStatus

logger = getLogger()


class Response:
    def __init__(self, response: bytes) -> None:
        if response is None:
            raise ValueError("Response is None")

        header_section: bytes = response[0:5]
        assert header_section[0] == HEADER
        self.header: int = response[0]
        self.address: int = response[1]
        self.command: CommandRequest = CommandRequest(int.from_bytes(response[2:4], "big"))
        self.length: int = response[4]
        self.status: Status = Status(response[5])

        __body_n_checksum_section: bytes = response[6: 4 + self.length + 2 + 1]
        self.payload: bytes = __body_n_checksum_section[0:-2]
        self.checksum: bytes = __body_n_checksum_section[-2:]

        # Verify checksum
        data = bytearray(header_section)
        data.extend(bytearray([self.status.value]))
        if self.payload:
            data.extend(self.payload)
        crc_msb, crc_lsb = calculate_checksum(data)
        assert self.checksum[0] == crc_msb and self.checksum[1] == crc_lsb

    def __str__(self) -> str:
        return_value = ''
        value = '<<< START RESPONSE ================================'
        return_value = f'{return_value}\n{value}'
        value = f'COMMAND   >> {self.command}'
        return_value = f'{return_value}\n{value}'
        value = f'STATUS    >> {self.status}'
        return_value = f'{return_value}\n{value}'
        if self.payload:
            value = f'PAYLOAD   >> {hex_readable(self.payload)}'
            return_value = f'{return_value}\n{value}'
        value = '<<< END RESPONSE   ================================'
        return_value = f'{return_value}\n{value}'
        return return_value.strip().upper()

    def serialize(self) -> bytes:
        res = bytearray([self.header, self.address])
        res.extend(self.command.value.to_bytes(2, "big"))
        res.extend(bytearray([self.length, self.status.value]))
        if self.payload:
            res.extend(self.payload)
        res.extend(self.checksum)
        return res


class ResponseDeviceInfo(Response):
    def __init__(self, response: bytes) -> None:
        super().__init__(response)
        # hardware_version(32), firmware_version(32), serial_number(12), reserve_1(32), reserve_2(32), reserve_3(12)
        assert len(self.payload) == 152

        self.device_info = DeviceInfo.from_bytes(self.payload)


class ResponseGetRfidProtocol(Response):
    def __init__(self, response: bytes) -> None:
        super().__init__(response)
        self.protocol = RfidProtocol(self.payload[0])

    def __str__(self) -> str:
        return self.protocol.name


class ResponseReaderSettings(Response):
    def __init__(self, response: bytes) -> None:
        super().__init__(response)
        assert len(self.payload) == 25

        self.reader_settings = ReaderSettings.from_bytes(self.payload)

    def __str__(self) -> str:
        return str(self.reader_settings)


class ResponseNetworkSettings(Response):
    def __init__(self, response: bytes) -> None:
        super().__init__(response)
        assert len(self.payload) == 21

        self.network_settings = NetworkSettings.from_bytes(self.payload[1:22])

    def __str__(self) -> str:
        return str(self.network_settings)


class ResponseRemoteNetworkSettings(Response):
    def __init__(self, response: bytes) -> None:
        super().__init__(response)
        assert len(self.payload) == 9
        self.option = CommandOption(self.payload[0])

        self.remote_network_settings = RemoteNetworkSettings.from_bytes(self.payload[1:9])

    def __str__(self) -> str:
        return str(self.remote_network_settings)


class ResponseCurrentTemperature(Response):
    def __init__(self, response: bytes) -> None:
        super().__init__(response)
        assert len(self.payload) == 2

        self.current_temperature = self.payload[0]
        self.max_temperature = self.payload[1]

    def __str__(self) -> str:
        return f'ResponseCurrentTemperature(current: {self.current_temperature}, max: {self.max_temperature})'


class ResponseGetAntennaPower(Response):
    def __init__(self, response: bytes) -> None:
        super().__init__(response)
        assert len(self.payload) == 10

        self.option = CommandOption(self.payload[0])
        self.enable = bool(self.payload[1])
        self.antenna_1_power = self.payload[2]
        self.antenna_2_power = self.payload[3]
        self.antenna_3_power = self.payload[4]
        self.antenna_4_power = self.payload[5]
        self.antenna_5_power = self.payload[6]
        self.antenna_6_power = self.payload[7]
        self.antenna_7_power = self.payload[8]
        self.antenna_8_power = self.payload[9]

    def __str__(self) -> str:
        return f'ResponseGetAntennaPower(enable: {self.enable}, ' \
               f'antenna 1: {self.antenna_1_power}, ' \
               f'antenna 2: {self.antenna_2_power}, ' \
               f'antenna 3: {self.antenna_3_power}, ' \
               f'antenna 4: {self.antenna_4_power}, ' \
               f'antenna 5: {self.antenna_5_power}, ' \
               f'antenna 6: {self.antenna_6_power}, ' \
               f'antenna 7: {self.antenna_7_power}, ' \
               f'antenna 8: {self.antenna_8_power})'


class ResponseInventoryRange(Response):
    """\
    start_address: in byte, length: in byte
    """

    def __init__(self, response: bytes) -> None:
        super().__init__(response)
        assert len(self.payload) == 5

        self.option = CommandOption(self.payload[0])
        self.start_address = self.payload[1]
        self.length = self.payload[2]
        self.reserve = self.payload[3:5]

    def __str__(self) -> str:
        return f'ResponseInventoryRange(start_address: {self.start_address}, length: {self.length})'


class ResponseInventory:
    """\
    Little bits different from `Response`, the status inside the payload/body
    """

    def __init__(self, response: bytes) -> None:
        logger.info(f"ResponseInventory() > __init__() > response: {hex_readable(response)}")

        self.tag = None

        header_section = response[0:5]
        assert header_section[0] == HEADER
        length = response[4]
        command = CommandRequest(int.from_bytes(header_section[2:4], "big"))
        body_n_checksum_section = response[5: 4 + length + 2 + 1]  # length(N) + 2(checksum) + 1 (end of index)
        self.status = InventoryStatus(body_n_checksum_section[0])
        if self.status != InventoryStatus.SUCCESS:
            return

        body_section = body_n_checksum_section[1:-2]
        checksum = response[-2:]

        # Verify checksum
        check = bytearray(header_section)
        check.extend(bytearray([body_n_checksum_section[0]]))
        check.extend(body_section)
        crc_msb, crc_lsb = calculate_checksum(check)
        if not(checksum[0] == crc_msb and checksum[1] == crc_lsb):
            return

        tag_length = body_section[4]
        tag_data = body_section[5: tag_length + 5]
        if tag_length != len(tag_data):
            raise ValueError("Length of tag data != tag length from byte response")

        self.tag = Tag(rssi=body_section[0:2], antenna=body_section[2], channel=body_section[3], data=body_section[5:])

    def __str__(self) -> str:
        return f'ResponseInventory(status: {self.status}, tag: {self.tag})'


class ResponseReadMemory(Response):
    def __init__(self, response: bytes) -> None:
        super().__init__(response)
        self.read_memory: ReadMemory | None = None

        if self.status == Status.NO_COUNT_LABEL:
            return

        assert len(self.payload) >= 8

        epc_length = self.payload[6]
        end_epc_length = epc_length + 7
        data_word_length = self.payload[end_epc_length]  # In word

        self.read_memory = ReadMemory(
            tag_status=TagStatus(self.payload[0]),
            antenna=self.payload[1],
            crc=self.payload[2:4],
            pc=self.payload[4:6],
            epc_length=epc_length,
            epc=self.payload[7:end_epc_length],
            data_word_length=data_word_length,
            data=self.payload[end_epc_length + 1: end_epc_length + (data_word_length * 2) + 1]
        )

    def __str__(self) -> str:
        return f'ResponseReadMemory(status: {self.status}, read_memory: {str(self.read_memory)})'


class ResponseWriteMemory(Response):
    def __init__(self, response: bytes) -> None:
        super().__init__(response)
        self.write_memory: WriteMemory | None = None

        if self.status == Status.NO_COUNT_LABEL:
            return

        assert len(self.payload) >= 7

        epc_length = self.payload[6]
        end_epc_length = epc_length + 7

        self.write_memory = WriteMemory(
            tag_status=TagStatus(self.payload[0]),
            antenna=self.payload[1],
            crc=self.payload[2:4],
            pc=self.payload[4:6],
            epc_length=epc_length,
            epc=self.payload[7:end_epc_length]
        )

    def __str__(self) -> str:
        return f'ResponseWriteMemory(status: {self.status}, write_memory: {str(self.write_memory)})'


class ResponseLockMemory(Response):
    def __init__(self, response: bytes) -> None:
        super().__init__(response)
        self.lock_memory: LockMemory | None = None

        if self.status == Status.NO_COUNT_LABEL:
            return

        assert len(self.payload) >= 7

        epc_length = self.payload[6]
        end_epc_length = epc_length + 7

        self.lock_memory = LockMemory(
            tag_status=TagStatus(self.payload[0]),
            antenna=self.payload[1],
            crc=self.payload[2:4],
            pc=self.payload[4:6],
            epc_length=epc_length,
            epc=self.payload[7:end_epc_length]
        )

    def __str__(self) -> str:
        return f'ResponseLockMemory(status: {self.status}, lock_memory: {str(self.lock_memory)})'


class ResponseKillTag(Response):
    def __init__(self, response: bytes) -> None:
        super().__init__(response)
        self.kill_tag: KillTag | None = None

        if self.status == Status.NO_COUNT_LABEL:
            return

        assert len(self.payload) >= 7

        epc_length = self.payload[6]
        end_epc_length = epc_length + 7

        self.kill_tag = KillTag(
            tag_status=TagStatus(self.payload[0]),
            antenna=self.payload[1],
            crc=self.payload[2:4],
            pc=self.payload[4:6],
            epc_length=epc_length,
            epc=self.payload[7:end_epc_length]
        )

    def __str__(self) -> str:
        return f'ResponseKillTag(status: {self.status}, kill_tag: {str(self.kill_tag)})'


class ResponseMaskInventoryPermission(Response):
    def __init__(self, response: bytes) -> None:
        super().__init__(response)
        assert len(self.payload) == 22

        self.mask_inventory_permission = MaskInventoryPermission.from_bytes(self.payload[1:])

    def __str__(self) -> str:
        return f'ResponseMaskInventoryPermission(mask_inventory_permission: {self.mask_inventory_permission})'


class ResponseQueryParameters(Response):
    def __init__(self, response: bytes) -> None:
        super().__init__(response)

        self.query_parameters = QueryParameters.from_bytes(self.payload)

    def __str__(self) -> str:
        return f'ResponseInventoryParameter(query_parameters: {self.query_parameters})'


class ResponseSelectParameters(Response):
    def __init__(self, response: bytes) -> None:
        super().__init__(response)

        self.select_parameters = SelectParameters.from_bytes(self.payload)

    def __str__(self) -> str:
        return f'ResponseSelectParameters(select_parameters: {self.select_parameters})'


class ResponseOutputControl(Response):
    def __init__(self, response: bytes) -> None:
        super().__init__(response)

        assert len(self.payload) == 18

        self.output_control = OutputControl.from_bytes(self.payload[1:])

    def __str__(self) -> str:
        return f'ResponseOutputControl(output_control: {self.output_control})'


