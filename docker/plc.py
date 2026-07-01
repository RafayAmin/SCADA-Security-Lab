import logging
import subprocess
import threading
import time
from collections import deque
from typing import Any, Deque

from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext, ModbusSlaveContext
from pymodbus.server import StartTcpServer  # type: ignore[import]
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

AUTHORIZED_WRITE_IPS = {"172.20.0.11", "172.20.0.12", "172.20.0.60"}
WRITE_RATE_LIMIT = 10
WRITE_RATE_WINDOW = 10


def setup_firewall() -> None:
    logger.info("[PLC] Configuring iptables firewall...")
    rules = [
        "iptables -A INPUT -p tcp --dport 502 -m state --state ESTABLISHED,RELATED -j ACCEPT",
        *[f"iptables -A INPUT -p tcp --dport 502 -s {ip} -j ACCEPT" for ip in AUTHORIZED_WRITE_IPS],
        "iptables -A INPUT -p tcp --dport 502 -j DROP",
    ]
    for rule in rules:
        try:
            subprocess.run(rule.split(), check=True, stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            logger.warning("[PLC] iptables command failed: %s", rule)
    logger.info("[PLC] Firewall configured.")


class RateLimitedSlaveContext(ModbusSlaveContext):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[call-arg]
        self._write_timestamps: Deque[float] = deque()

    def setValues(self, fc_as_hex: Any, address: int, values: Any) -> None:
        now = time.time()
        self._write_timestamps.append(now)
        while self._write_timestamps and self._write_timestamps[0] < now - WRITE_RATE_WINDOW:
            self._write_timestamps.popleft()
        if len(self._write_timestamps) > WRITE_RATE_LIMIT:
            logger.warning(
                "[PLC] Write rate limit exceeded (%d writes in %ds) - blocked",
                len(self._write_timestamps),
                WRITE_RATE_WINDOW,
            )
            return
        super().setValues(fc_as_hex, address, values)  # type: ignore[attr-defined]


def update_registers(store: RateLimitedSlaveContext) -> None:
    holding = 25
    while True:
        holding += 1 if holding < 30 else -5
        store.store["h"].setValues(0, [holding])  # type: ignore[attr-defined]
        time.sleep(5)


def main() -> None:
    setup_firewall()
    store = RateLimitedSlaveContext(
        zero_mode=True,
        co=ModbusSequentialDataBlock(0, [0] * 10),
        hr=ModbusSequentialDataBlock(0, [25]),
    )
    context = ModbusServerContext(slaves=store, single=True)
    thread = threading.Thread(target=update_registers, args=(store,), daemon=True)
    thread.start()
    logger.info("[PLC] Starting Modbus Server on port 502...")
    StartTcpServer(context=context, address=("0.0.0.0", 502))


if __name__ == "__main__":
    main()
