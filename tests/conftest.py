from __future__ import annotations

import logging
from collections.abc import Generator

import pytest
from pymodbus.client import ModbusTcpClient

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

PLC_HOST = "plc"
PLC_PORT = 502
HMI_HOST = "hmi"
DETECTOR_HOST = "detector"


@pytest.fixture(scope="session")
def plc_client() -> Generator[ModbusTcpClient, None, None]:
    client = ModbusTcpClient(PLC_HOST, port=PLC_PORT)
    if not client.connect():
        pytest.skip("PLC container not reachable — is `docker compose up` running?")
    logger.info("[CONFTEST] Connected to PLC at %s:%d", PLC_HOST, PLC_PORT)
    yield client
    client.close()
