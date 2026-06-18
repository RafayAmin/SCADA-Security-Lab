from pymodbus.client import ModbusTcpClient
import time

# client = ModbusTcpClient('127.0.0.1', port=502)  # didn't work with docker dns
client = ModbusTcpClient('plc', port=502)

while True:
    try:
        result = client.read_holding_registers(address=0, count=1, unit=1)
        if not result.isError():
            temp = result.registers[0]
            # print(f"Polling PLC... Current temp: {temp}") # used this to debug timeout
            print(f"[HMI] Current Temperature: {temp}°C")
        else:
            print("[HMI] Error reading from PLC")
    except Exception as e:
        print(f"[HMI] Connection failed: {e}")
    time.sleep(3)
