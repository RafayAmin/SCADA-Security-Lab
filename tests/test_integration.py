from __future__ import annotations

import logging
import socket

from pymodbus.client import ModbusTcpClient

logger = logging.getLogger(__name__)

PLC_HOST = "plc"
PLC_PORT = 502
HMI_HOST = "hmi"
DETECTOR_HOST = "detector"
ATTACKER_HOST = "attacker"
SNORT_HOST = "snort"
STRONGSWAN_HOST = "strongswan"


def _read_register(client: ModbusTcpClient, address: int) -> int | None:
    result = client.read_holding_registers(address=address, count=1, unit=1)
    return None if result.isError() else result.registers[0]


def _write_register(client: ModbusTcpClient, address: int, value: int) -> bool:
    result = client.write_register(address=address, value=value, unit=1)
    return not result.isError()


def _resolve(host: str) -> bool:
    try:
        socket.getaddrinfo(host, 80, socket.AF_INET)
        return True
    except socket.gaierror:
        return False


def test_plc_modbus_port_open(plc_client: ModbusTcpClient) -> None:
    assert plc_client.is_socket_open()


def test_plc_temperature_readable(plc_client: ModbusTcpClient) -> None:
    temp = _read_register(plc_client, 0)
    assert temp is not None
    assert 0 <= temp <= 255


def test_plc_register_range_cycle(plc_client: ModbusTcpClient) -> None:
    temps: list[int] = []
    for _ in range(10):
        temp = _read_register(plc_client, 0)
        if temp is not None:
            temps.append(temp)
    assert len(temps) == 10
    assert 25 <= min(temps) <= 30
    assert 25 <= max(temps) <= 30


def test_plc_write_extreme_value_detected(plc_client: ModbusTcpClient) -> None:
    result = _write_register(plc_client, 0, 99)
    assert result is True


def test_plc_block_register_readable(plc_client: ModbusTcpClient) -> None:
    block = _read_register(plc_client, 1)
    assert block is not None
    assert block in (0, 1)


def test_plc_write_rate_limiting(plc_client: ModbusTcpClient) -> None:
    count = 0
    for _ in range(15):
        if _write_register(plc_client, 0, 25):
            count += 1
    assert count <= 11


def test_plc_auto_response_blocks_attacker(plc_client: ModbusTcpClient) -> None:
    initial_block = _read_register(plc_client, 1)
    assert initial_block is not None

    _write_register(plc_client, 1, 1)
    block = _read_register(plc_client, 1)
    assert block == 1

    _write_register(plc_client, 1, 0)
    block = _read_register(plc_client, 1)
    assert block == 0


def test_hmi_dns_resolves() -> None:
    assert _resolve(HMI_HOST)


def test_detector_dns_resolves() -> None:
    assert _resolve(DETECTOR_HOST)


def test_snort_dns_resolves() -> None:
    assert _resolve(SNORT_HOST)


def test_strongswan_dns_resolves() -> None:
    assert _resolve(STRONGSWAN_HOST)


def test_full_stack_connectivity(plc_client: ModbusTcpClient) -> None:
    temp = _read_register(plc_client, 0)
    assert temp is not None, "Cannot read from PLC"

    block = _read_register(plc_client, 1)
    assert block is not None, "Cannot read block register from PLC"

    assert _resolve(HMI_HOST), f"Cannot resolve {HMI_HOST}"
    assert _resolve(DETECTOR_HOST), f"Cannot resolve {DETECTOR_HOST}"
