import logging
import time

from pymodbus.client import ModbusTcpClient

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    client = ModbusTcpClient("plc", port=502)
    while True:
        try:
            result = client.read_holding_registers(address=0, count=1, unit=1)
            if not result.isError():  # type: ignore[union-attr]
                temp = result.registers[0]  # type: ignore[union-attr]
                logger.info("[HMI] Current Temperature: %d°C", temp)
            else:
                logger.error("[HMI] Error reading from PLC")
        except Exception:
            logger.exception("[HMI] Connection failed")
        time.sleep(3)


if __name__ == "__main__":
    main()
