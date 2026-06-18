import collections
import subprocess
import threading
import time
from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext, ModbusSequentialDataBlock

# TODO: Make AUTHORIZED_WRITE_IPS configurable via environment variables
AUTHORIZED_WRITE_IPS = {"172.20.0.11", "172.20.0.12"}
WRITE_RATE_LIMIT = 10
WRITE_RATE_WINDOW = 10

def setup_firewall():
    print("[PLC] Configuring iptables firewall...")
    rules = [
        "iptables -A INPUT -p tcp --dport 502 -m state --state ESTABLISHED,RELATED -j ACCEPT",
        "iptables -A INPUT -p tcp --dport 502 -s 172.20.0.11 -j ACCEPT",
        "iptables -A INPUT -p tcp --dport 502 -s 172.20.0.12 -j ACCEPT",
        "iptables -A INPUT -p tcp --dport 502 -j DROP"
    ]
    for rule in rules:
        try:
            # Using subprocess to call iptables.
            # TODO: Look into the 'python-iptables' library so we don't have to rely on shell commands
            subprocess.run(rule.split(), check=True, stdout=subprocess.DEVNULL)
        except Exception as e:
            print(f"[PLC] Warning: iptables command failed: {e}")
    print("[PLC] Firewall configured.")

class RateLimitedSlaveContext(ModbusSlaveContext):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Using deque instead of a normal list because list.pop(0) is O(n) and was lagging the PLC loop
        self._write_timestamps = collections.deque()

    def setValues(self, fc, address, values):
        now = time.time()
        self._write_timestamps.append(now)
        while self._write_timestamps and self._write_timestamps[0] < now - WRITE_RATE_WINDOW:
            self._write_timestamps.popleft()
        if len(self._write_timestamps) > WRITE_RATE_LIMIT:
            print(f"[PLC] Write rate limit exceeded ({len(self._write_timestamps)} writes in {WRITE_RATE_WINDOW}s) — blocked")
            return
        super().setValues(fc, address, values)

def update_registers(store):
    holding = 25
    while True:
        holding += 1 if holding < 30 else -5
        # FIXME: This bypasses the rate limiter - should refactor to use context.setValues
        store.store['h'].setValues(0, [holding])
        time.sleep(5)

if __name__ == "__main__":
    setup_firewall()

    store = RateLimitedSlaveContext(
        zero_mode=True,
        co=ModbusSequentialDataBlock(0, [0] * 10),
        hr=ModbusSequentialDataBlock(0, [25]),
    )
    context = ModbusServerContext(slaves=store, single=True)

    thread = threading.Thread(target=update_registers, args=(store,), daemon=True)
    thread.start()

    print("Starting PLC (Modbus Server) on port 502...")
    StartTcpServer(context=context, address=("0.0.0.0", 502))
