from array import array
from time import sleep
from typing import Iterator
from PySide6.QtCore import Signal, QObject
from usb import USBError

from rfid.command import Command
from rfid.reader_settings import AnswerModeInventoryParameter, WorkMode, MemoryBank, LockMemoryBank, LockAction, \
    StopAfter
from rfid.transport import Transport, UsbTransport, SerialTransport, TcpTransport
from rfid.response import *

logger = getLogger()


class Reader(QObject):
    send_request_bytes_signal = Signal(bytes)
    receive_response_bytes_signal = Signal(bytes)

    def __init__(self, transport: Transport) -> None:
        super().__init__()
        self.transport = transport
        self.is_inventory = False
        logger.info(f"Reader() > __init__() > transport: {transport}")

    def close(self) -> None:
        logger.info(f"Reader() > close() > transport: {self.transport}")
        self.transport.close()

    def __send_request(self, command: Command, clear_buffer: bool = True) -> None:
        serialize = command.serialize()
        logger.info(f"Reader() > __send_request() > command: {command}")
        self.send_request_bytes_signal.emit(serialize)
        if clear_buffer:
            self.transport.clear_buffer()
        self.transport.write_bytes(serialize)

    def __receive_response(self, command_request: CommandRequest, verify_header: bool = True, loop_usb: bool = True) \
            -> bytes | None:
        def __receive():
            raw_resp: bytes | None = None

            if isinstance(self.transport, UsbTransport):
                raw_resp = self.transport.read_bytes()

                if loop_usb:
                    all_len = 4 + raw_resp[
                        4] + 2  # header(1) + address(1) + command(2) + length(index: 4) + checksum(2)
                    while len(raw_resp) < all_len:
                        raw_resp += self.transport.read_bytes()

            elif isinstance(self.transport, (SerialTransport, TcpTransport)):
                response_header_section = self.transport.read_bytes(length=5)

                if (len(response_header_section) <= 0) or (
                        not verify_header and response_header_section[0] != HEADER):
                    self.transport.clear_buffer()
                    return raw_resp

                assert len(response_header_section) == 5  # header(1) + address(1) + command(2) + length(1)

                # Get body section
                body_length = response_header_section[-1]
                response_body_section = self.transport.read_bytes(length=body_length + 2)  # 2(checksum)

                raw_resp = response_header_section + response_body_section
            return raw_resp

        raw_response = None
        for i in range(20):
            raw_response = __receive()

            if isinstance(raw_response, bytes) \
                    or isinstance(raw_response, bytearray) \
                    or isinstance(raw_response, array):
                logger.info(f"Reader() > {i} __receive() > raw_response: {hex_readable(raw_response)}")
            else:
                logger.info(f"Reader() > {i} __receive() > raw_response: {raw_response}")

            if raw_response is None:
                return
            self.receive_response_bytes_signal.emit(raw_response)

            if len(raw_response) > 0 and raw_response[0] != HEADER:
                self.transport.clear_buffer()

            command_response: CommandRequest | None = None

            try:
                command_response = CommandRequest(int.from_bytes(raw_response[2:4], "big"))
            except ValueError as e:
                logger.info(f"Reader() > {i} __receive() > ValueError: {e}")
            logger.info(f"Reader() > {i} __receive() > "
                        f"command_response: {command_response}, command_request: {command_request}")

            if command_response == command_request:
                break

        logger.info(f"Reader() > raw_response: {hex_readable(raw_response)}")

        return raw_response

    def init(self) -> None | Response:
        logger.info(f"Reader() > init()")
        cmd_request = CommandRequest.MODULE_INIT
        command = Command(cmd_request)
        self.__send_request(command)
        raw_response = self.__receive_response(cmd_request)
        if raw_response is None or len(raw_response) <= 0:
            return None
        return Response(raw_response)

    def reset_factory(self) -> Response:
        logger.info(f"Reader() > reset_factory()")

        cmd_request = CommandRequest.REBOOT
        command = Command(cmd_request)
        self.__send_request(command)
        return Response(self.__receive_response(cmd_request))

    def get_device_info(self) -> ResponseDeviceInfo:
        logger.info(f"Reader() > get_device_info()")

        cmd_request = CommandRequest.GET_DEVICE_INFO
        command = Command(cmd_request)
        self.__send_request(command)
        device_info = ResponseDeviceInfo(self.__receive_response(cmd_request))
        return device_info

    def set_power(self, power: int, reserve: int = 0x00) -> Response:
        logger.info(f"Reader() > set_power() > power: {power}")

        assert (0 <= power <= 33) and (0x00 <= reserve <= 0x01)

        cmd_request = CommandRequest.SET_POWER
        command = Command(cmd_request, data=bytearray([power, reserve]))
        self.__send_request(command)
        return Response(self.__receive_response(cmd_request))

    def set_relay(self, release: bool, valid_time: int = 1) -> Response:
        """
        :param release: If `True` release/open the relay
        :param valid_time: The effective time when closing
        """
        assert type(release) is bool and (0x00 <= valid_time <= 0xFF)

        release_value = 0x01
        if not release:  # Close
            release_value = 0x02

        cmd_request = CommandRequest.RELEASE_CLOSE_RELAY
        command = Command(cmd_request, data=bytearray([release_value, valid_time]))
        self.__send_request(command)
        return Response(self.__receive_response(cmd_request))

    def get_rfid_protocol(self) -> ResponseGetRfidProtocol:
        """
        Only for ISO 18000-6C
        """
        cmd_request = CommandRequest.SET_GET_RFID_PROTOCOL
        command = Command(cmd_request, data=bytearray([CommandOption.GET.value, 0x00]))  # ? 0x00 ? NC or 1Byte
        self.__send_request(command)
        return ResponseGetRfidProtocol(self.__receive_response(cmd_request))

    def set_rfid_protocol(self, rfid_protocol: RfidProtocol) -> Response:
        """
        Only for ISO 18000-6C
        """
        cmd_request = CommandRequest.SET_GET_RFID_PROTOCOL
        command = Command(cmd_request, data=bytearray([CommandOption.SET.value, rfid_protocol.value]))
        self.__send_request(command)
        return Response(self.__receive_response(cmd_request))

    def get_reader_settings(self) -> ResponseReaderSettings:
        logger.info(f"Reader() > get_reader_settings()")

        cmd_request = CommandRequest.GET_ALL_PARAM
        command = Command(cmd_request)
        self.__send_request(command)
        return ResponseReaderSettings(self.__receive_response(cmd_request))

    def set_reader_settings(self, reader_settings: ReaderSettings) -> Response:
        logger.info(f"Reader() > set_reader_settings() > reader_settings: {reader_settings}")

        cmd_request = CommandRequest.SET_ALL_PARAM
        command = Command(cmd_request, data=reader_settings.to_command_data())
        self.__send_request(command)
        return Response(self.__receive_response(cmd_request))

    def get_network_settings(self) -> ResponseNetworkSettings:
        logger.info(f"Reader() > get_network_settings()")

        cmd_request = CommandRequest.SET_GET_NETWORK
        command = Command(cmd_request, data=bytearray([CommandOption.GET.value]))
        self.__send_request(command)
        return ResponseNetworkSettings(self.__receive_response(cmd_request))

    def set_network_settings(self, network_settings: NetworkSettings) -> Response:
        logger.info(f"Reader() > set_network_settings() > network_settings: {network_settings}")

        cmd_request = CommandRequest.SET_GET_NETWORK
        data = bytearray([CommandOption.SET.value])
        data.extend(network_settings.to_command_data())
        command = Command(cmd_request, data=data)
        self.__send_request(command)
        return Response(self.__receive_response(cmd_request))

    def get_remote_network_settings(self) -> ResponseRemoteNetworkSettings:
        logger.info(f"Reader() > get_remote_network_settings()")

        cmd_request = CommandRequest.SET_GET_REMOTE_NETWORK
        command = Command(cmd_request, data=bytearray([CommandOption.GET.value]))
        self.__send_request(command)
        return ResponseRemoteNetworkSettings(self.__receive_response(cmd_request))

    def set_remote_network_settings(self, remote_network_settings: RemoteNetworkSettings) -> Response:
        logger.info(f"Reader() > set_remote_remote_network_settings() "
                    f"> remote_network_settings: {remote_network_settings}")

        cmd_request = CommandRequest.SET_GET_REMOTE_NETWORK
        data = bytearray([CommandOption.SET.value])
        data.extend(remote_network_settings.to_command_data())
        command = Command(cmd_request, data=data)
        self.__send_request(command)
        return Response(self.__receive_response(cmd_request))

    def set_max_temperature(self, max_temperature: int) -> Response:
        cmd_request = CommandRequest.SET_MAX_TEMPERATURE
        command = Command(cmd_request, data=bytearray([max_temperature]))
        self.__send_request(command)
        return Response(self.__receive_response(cmd_request))

    def get_current_temperature(self) -> ResponseCurrentTemperature:
        cmd_request = CommandRequest.GET_CURRENT_TEMPERATURE
        command = Command(cmd_request)
        self.__send_request(command)
        return ResponseCurrentTemperature(self.__receive_response(cmd_request))

    def get_antenna_power(self) -> ResponseGetAntennaPower:
        cmd_request = CommandRequest.SET_GET_ANTENNA_POWER
        command = Command(cmd_request, data=bytearray([CommandOption.GET.value]))
        self.__send_request(command)
        return ResponseGetAntennaPower(self.__receive_response(cmd_request))

    # Failed
    def set_antenna_power(self, enable: bool, antenna_1_power: int,
                          antenna_2_power: int = 0, antenna_3_power: int = 0, antenna_4_power: int = 0,
                          antenna_5_power: int = 0, antenna_6_power: int = 0, antenna_7_power: int = 0,
                          antenna_8_power: int = 0) -> Response:
        cmd_request = CommandRequest.SET_GET_ANTENNA_POWER
        command = Command(cmd_request, data=bytearray([CommandOption.SET.value, int(enable),
                                                       antenna_1_power, antenna_2_power, antenna_3_power,
                                                       antenna_4_power, antenna_5_power, antenna_6_power,
                                                       antenna_7_power, antenna_8_power
                                                       ]))
        self.__send_request(command)
        return Response(self.__receive_response(cmd_request))

    def select_mask(self, mask: bytes, start_address: int = 0) -> Response:
        """
                :param mask: The EPC value (odd length)
                :param start_address: Start address in byte
                :return:
        """

        start_address = start_address * 8  # Pointer in bits
        start_address = start_address.to_bytes(2, "big")

        data = bytearray(start_address)

        length = len(mask) * 8  # Length in bits
        data.extend([length])

        if len(mask) % 2 != 0:
            mask = mask + bytes(1)

        data.extend(mask)
        logger.info(f"Reader() > select_mask() > length: {length}, mask: {hex_readable(mask)}, "
                    f"data: {hex_readable(data)}")

        cmd_request = CommandRequest.SELECT_MASK
        command = Command(cmd_request, data=data)
        self.__send_request(command)
        return Response(self.__receive_response(cmd_request))

    def read_memory(self, memory_bank: MemoryBank,
                    start_address: int = 0, length: int = 0, access_password: bytes = bytes(4)) \
            -> Iterator[ResponseReadMemory] | None:
        """
                :param memory_bank: Select the memory bank
                :param start_address: Start address (in word) to read
                :param length: Length (in word) data to read
                :param access_password: Default is bytes(4) 0x00000000
                :return:

        Can use `select_mask(...)` for filter
        """
        logger.info(f"Reader() > read_memory() > memory_bank: {memory_bank}, start_address: {start_address}, "
                    f"length: {length}, access_password: {hex_readable(access_password)}")

        assert (0x00 <= start_address <= 0xFFFF) and (0x00 <= length <= 0xFF)

        self.is_inventory = True

        data = bytearray([0x00])  # Option (default 0x00)
        data.extend(access_password)
        data.extend([memory_bank.value])
        data.extend(start_address.to_bytes(2, "big"))
        data.extend([length])
        logger.info(f"Reader() > read_memory() > data: {hex_readable(data)}")

        cmd_request = CommandRequest.READ_ISO_TAG
        command = Command(cmd_request, data=data)
        self.__send_request(command)

        response: ResponseReadMemory | None = None
        while self.is_inventory:
            raw_response = self.__receive_response(cmd_request)
            if raw_response is None:
                logger.info(f"Reader() > read_memory() > raw_response: {raw_response}")

                yield raw_response  # None
                continue

            response = ResponseReadMemory(raw_response)
            yield response
            if response.status == Status.NO_COUNT_LABEL:
                break

        self.is_inventory = False

        logger.info(f"Reader() > read_memory() > response: {response}")

    def write_memory(self, memory_bank: MemoryBank, data: bytes,
                     start_address: int = 0, length: int = 0, access_password: bytes = bytes(4)) \
            -> Iterator[ResponseWriteMemory] | None:
        """
                :param memory_bank: Select the memory bank
                :param data: Data to write
                :param start_address: Start address (in word) to read
                :param length: Length (in word) data to read
                :param access_password: Default is bytes(4) 0x00000000
                :return:

        Can use `select_mask(...)` for filter
        """
        logger.info(f"Reader() > write_memory() > memory_bank: {memory_bank}, start_address: {start_address}, "
                    f"length: {length}, access_password: {hex_readable(access_password)}, "
                    f"data: {hex_readable(data)}")

        assert len(data) > 0
        if length == 0:
            length = len(data)
        assert (0x00 <= start_address <= 0xFFFF) and (0x00 < length <= 0xFF)

        self.is_inventory = True

        cmd_data = bytearray([0x00])  # Option (default 0x00)
        cmd_data.extend(access_password)
        cmd_data.extend([memory_bank.value])
        cmd_data.extend(start_address.to_bytes(2, "big"))
        cmd_data.extend([length])
        cmd_data.extend(data)

        cmd_request = CommandRequest.WRITE_ISO_TAG
        command = Command(cmd_request, data=cmd_data)
        self.__send_request(command)

        response: ResponseWriteMemory | None = None
        while self.is_inventory:
            raw_response = self.__receive_response(cmd_request)
            print(f"Reader() > write_memory() > raw_response: {raw_response}")

            if raw_response is None:
                continue

            response = ResponseWriteMemory(raw_response)
            yield response
            if response.status == Status.NO_COUNT_LABEL:
                break

        self.is_inventory = False

        logger.info(f"Reader() > write_memory() > response: {response}")

    def lock_memory(self, lock_memory_bank: LockMemoryBank, lock_action: LockAction,
                    access_password: bytes = bytes(4)) -> Iterator[ResponseLockMemory] | None:
        """
            :param lock_memory_bank: Select the lock memory bank
            :param lock_action: Select the lock type
            :param access_password: Default is bytes(4) 0x00000000
            :return:

        Can use `select_mask(...)` for filter
        """
        logger.info(f"Reader() > lock_memory() > lock_memory_bank: {lock_memory_bank}, "
                    f"lock_action: {lock_action}, access_password: {hex_readable(access_password)}")

        cmd_data = bytearray(access_password)
        cmd_data.extend([lock_memory_bank.value])
        cmd_data.extend([lock_action.value])

        self.is_inventory = True

        cmd_request = CommandRequest.LOCK_ISO_TAG
        command = Command(cmd_request, data=cmd_data)
        self.__send_request(command)

        response: ResponseLockMemory | None = None
        while self.is_inventory:
            raw_response = self.__receive_response(cmd_request)
            logger.info(f"Reader() > lock_memory() > raw_response: {raw_response}")

            if raw_response is None:
                continue

            response = ResponseLockMemory(raw_response)
            yield response
            if response.status == Status.NO_COUNT_LABEL:
                break

        self.is_inventory = False

        logger.info(f"Reader() > lock_memory() > response: {response}")

    def kill_tag(self, kill_password: bytes = bytes(4)) -> Iterator[ResponseKillTag] | None:
        """
            :param kill_password: Default is bytes(4) 0x00000000
            :return:

        Can use `select_mask(...)` for filter
        """
        logger.info(f"Reader() > kill_tag() > kill_password: {hex_readable(kill_password)}")

        self.is_inventory = True

        cmd_data = bytearray(kill_password)
        cmd_request = CommandRequest.KILL_ISO_TAG
        command = Command(cmd_request, data=cmd_data)
        self.__send_request(command)

        response: ResponseKillTag | None = None
        while self.is_inventory:
            raw_response = self.__receive_response(cmd_request)
            logger.info(f"Reader() > kill_tag() > raw_response: {raw_response}")

            if raw_response is None:
                continue

            response = ResponseKillTag(raw_response)
            yield response
            if response.status == Status.NO_COUNT_LABEL:
                break

        self.is_inventory = False

        logger.info(f"Reader() > kill_tag() > response: {response}")

    def get_output_control(self) -> ResponseOutputControl:
        logger.info(f"Reader() > get_output_control()")

        cmd_request = CommandRequest.SET_GET_OUTPUT_PARAMETERS
        data = bytearray([CommandOption.GET.value])
        command = Command(cmd_request, data=data)
        self.__send_request(command)
        return ResponseOutputControl(self.__receive_response(cmd_request))

    def set_output_control(self, output_control: OutputControl) -> Response:
        logger.info(f"Reader() > set_output_control()")

        cmd_request = CommandRequest.SET_GET_OUTPUT_PARAMETERS
        data = bytearray([CommandOption.SET.value])
        data.extend(output_control.to_command_data())
        command = Command(cmd_request, data=data)
        self.__send_request(command)
        return Response(self.__receive_response(cmd_request))

    def get_mask_inventory_permission(self) -> ResponseMaskInventoryPermission:
        logger.info(f"Reader() > get_mask_inventory_permission()")

        cmd_request = CommandRequest.SET_GET_PERMISSION
        command = Command(cmd_request, data=bytearray([CommandOption.GET.value]))

        self.__send_request(command)
        return ResponseMaskInventoryPermission(self.__receive_response(cmd_request))

    def set_mask_inventory_permission(self, mask_inventory_permission: MaskInventoryPermission) -> Response:
        logger.info(f"Reader() > set_mask_inventory() > mask_inventory_permission: {mask_inventory_permission}")

        cmd_request = CommandRequest.SET_GET_PERMISSION
        data = bytearray([CommandOption.SET.value])
        data.extend(mask_inventory_permission.to_command_data())

        command = Command(cmd_request, data=data)
        self.__send_request(command)

        response: Response = Response(self.__receive_response(cmd_request))

        # Start inventory - Handle inventory buffer after set filter
        data = bytearray([StopAfter.NUMBER.value])
        data.extend((2).to_bytes(4, "big"))  # Stop after 2 cycle
        command = Command(CommandRequest.INVENTORY_ISO_CONTINUE, data=data)
        self.__send_request(command, clear_buffer=True)

        sleep(0.2)

        # Stop inventory
        self.__send_request(Command(CommandRequest.INVENTORY_STOP), clear_buffer=False)
        return response

    def stop_inventory(self, work_mode: WorkMode = WorkMode.ANSWER_MODE) -> None:
        """
        To stop inventory `counting type == TIME and time == 0`
        """
        logger.info(f"Reader() > stop_inventory() > START > is_inventory: {self.is_inventory}")

        cmd_request = CommandRequest.INVENTORY_STOP

        if work_mode == WorkMode.ANSWER_MODE:
            if self.is_inventory:
                command = Command(cmd_request)
                self.__send_request(command, clear_buffer=False)

            try:
                self.__receive_response(cmd_request)
            except (USBError, TimeoutError) as _:
                logger.info(f'Reader() > stop_inventory() > timeout')

        self.is_inventory = False

        logger.info(f"Reader() > stop_inventory() > DONE > is_inventory: {self.is_inventory}")

    def start_inventory(self, work_mode: WorkMode,
                        answer_mode_inventory_parameter: AnswerModeInventoryParameter | None = None) \
            -> Iterator[ResponseInventory] | None:
        """
        :param work_mode: Work mode type
        :param answer_mode_inventory_parameter: By Time or by number, and the value

        :return:

        When Using `counting type == TIME and time == 0`, to stop inventory needs call `stop_inventory()` method
        """
        logger.info(f"Reader() > start_inventory() > START")

        cmd_request = CommandRequest.INVENTORY_ISO_CONTINUE

        self.is_inventory = True

        if work_mode == WorkMode.ANSWER_MODE and answer_mode_inventory_parameter is None:
            raise ValueError("Answer mode inventory parameter is None")

        if work_mode == WorkMode.ANSWER_MODE and answer_mode_inventory_parameter is not None:
            data = bytearray([answer_mode_inventory_parameter.stop_after.value])
            data.extend(answer_mode_inventory_parameter.value.to_bytes(4, "big"))
            command = Command(cmd_request, data=data)
            self.__send_request(command, clear_buffer=True)

        response = []
        while self.is_inventory:
            try:
                if response is None:
                    response = self.__receive_response(cmd_request, verify_header=False, loop_usb=False)
                # Sisa buffer diabaikan, kalau diambil takutnya tidak relevan (1 tag, tapi ada 2 di UI)
                # elif len(response) > 8 and isinstance(self.transport, UsbTransport):
                #     response = response[len(frame):]
                else:
                    response = self.__receive_response(cmd_request, verify_header=False, loop_usb=False)
            except (USBError, TimeoutError) as _:
                response = []
                yield None
                continue

            if response is None or len(response) <= 0:
                logger.info(f"Reader() > start_inventory() > continue, response > {response}")
                response = []
                yield None
                continue

            if response[0] != HEADER:  # Next
                logger.info(f"Reader() > start_inventory() > break, response[0] != HEADER > {response[0]}")
                response = []
                continue

            header_section = response[0:5]
            length = response[4]
            command_request = CommandRequest(int.from_bytes(header_section[2:4], "big"))
            if command_request == CommandRequest.INVENTORY_STOP:
                response = []
                continue
            body_n_checksum_section = response[5: 4 + length + 2 + 1]  # length(N) + 2(checksum) + 1 (end of index)
            status = InventoryStatus(body_n_checksum_section[0])
            body_section = body_n_checksum_section[1:-2]

            # Check length of the payload/body (for USB)
            if len(body_n_checksum_section) - 2 != length:  # 2 is checksum  # Next
                response = []
                continue

            # Check length of data tag (for USB)
            if isinstance(self.transport, UsbTransport) and status == InventoryStatus.SUCCESS:
                tag_length = body_section[4]
                tag_data = body_section[0:tag_length]
                if len(tag_data) != tag_length:  # Next
                    response = []
                    continue

            # Get one frame
            frame = header_section + body_n_checksum_section
            response_inventory = ResponseInventory(frame)
            yield response_inventory

            if status == InventoryStatus.NO_COUNT_LABEL:
                break

        self.is_inventory = False

        logger.info(f"Reader() > start_inventory() > DONE")

    # Analytics purpose
    def get_inventory_range(self) -> Response:
        logger.info(f"Reader() > get_inventory_range()")

        cmd_request = CommandRequest.INVENTORY_RANGE
        command = Command(cmd_request, data=bytearray([CommandOption.GET.value]))
        self.__send_request(command)
        return ResponseInventoryRange(self.__receive_response(cmd_request))

    # Analytics purpose
    def set_inventory_range(self, start_address: int, length: int) -> Response:
        """
        :param start_address: Start address in byte
        :param length: Length in byte. if length 0x00 = All output
        """
        logger.info(f"Reader() > set_inventory_range() > start_address: {start_address}, length: {length}")

        assert 0x00 <= start_address <= 0xFF
        assert 0x00 <= length <= 0xFF

        cmd_request = CommandRequest.INVENTORY_RANGE
        data = bytearray([CommandOption.SET.value])
        data.extend([start_address, length])
        data.extend([0x00, 0x00])  # Reserve (2 bytes)
        command = Command(cmd_request, data=data)
        self.__send_request(command)
        return Response(self.__receive_response(cmd_request))
