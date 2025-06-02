import ipaddress
import socket
import psutil

from array import array

from psutil._common import snicaddr


def hex_readable(data_bytes: bytes | array, separator: str = " ") -> str:
    return separator.join("{:02X}".format(x) for x in data_bytes)


def ip_string(ip_bytes: bytes) -> str:
    assert len(ip_bytes) == 4
    return ".".join("{:d}".format(x) for x in ip_bytes)


def ip_bytes(ip_str: str) -> bytearray:
    ip_str_split = ip_str.split('.')
    assert len(ip_str_split) == 4

    return bytearray([int(ip) for ip in ip_str_split])


def generate_ip_range(network_cidr: str):
    network = ipaddress.ip_network(network_cidr)
    ip_list = [str(ip) for ip in network.hosts()]

    return ip_list


def netmask_to_cidr(netmask: str) -> int:
    netmask_ip = ipaddress.IPv4Address(netmask)
    cidr = bin(int(netmask_ip)).count('1')
    return cidr


def calculate_checksum(data: bytes) -> bytearray:
    value = 0xFFFF
    for d in data:
        value ^= d
        for _ in range(8):
            value = (value >> 1) ^ 0x8408 if value & 0x0001 else (value >> 1)
    crc_msb = value >> 0x08
    crc_lsb = value & 0xFF
    return bytearray([crc_msb, crc_lsb])


def calculate_rssi(rssi: bytes) -> int:
    return int.from_bytes(rssi, "big", signed=True)


def get_all_networks() -> list[dict]:
    net_if_addresses: dict[str, list[snicaddr]] = psutil.net_if_addrs()

    network_info: list[dict] = []

    for interface, addresses in net_if_addresses.items():
        for address in addresses:
            if address.family == socket.AF_INET:

                netmask = address.netmask
                network_info.append({
                    "interface": interface,
                    "address": address.address,
                    "netmask": netmask,
                })

    return network_info
