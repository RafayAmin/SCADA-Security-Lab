import threading
import time
from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext, ModbusSequentialDataBlock

def update_registers(store):
    holding = 25
    while True:
        holding += 1 if holding < 30 else -5
        store.store['h'].setValues(0, [holding])
        time.sleep(5)

if __name__ == "__main__":
    store = ModbusSlaveContext(
        zero_mode=True,
        co=ModbusSequentialDataBlock(0, [0] * 10),
        hr=ModbusSequentialDataBlock(0, [25]),
    )
    context = ModbusServerContext(slaves=store, single=True)

    thread = threading.Thread(target=update_registers, args=(store,), daemon=True)
    thread.start()

    print("Starting PLC (Modbus Server) on port 502...")
    StartTcpServer(context=context, address=("0.0.0.0", 502))
