from pymodbus.client import ModbusTcpClient
import time

client = ModbusTcpClient('plc', port=502)

while True:
    result = client.read_holding_registers(address=0, count=1, unit=1)
    if not result.isError():
        temp = result.registers[0]
        print(f"[HMI] Current Temperature: {temp}°C")
    else:
        print("[HMI] Error reading from PLC")
    time.sleep(3)
