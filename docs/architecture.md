# Architecture

## Network Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                    scada_net (172.20.0.0/24)                      │
│                                                                   │
│  ┌──────────────┐       Modbus TCP (502)       ┌──────────────┐  │
│  │   PLC        │◄────────────────────────────►│    HMI       │  │
│  │   .10        │                              │    .11       │  │
│  │  iptables    │                              │  Reads temp  │  │
│  │  firewall    │                              │  every 3s    │  │
│  └──────┬───────┘                              └──────────────┘  │
│         │                                                        │
│         │ Modbus TCP (poll every 5s)                             │
│         ▼                                                        │
│  ┌──────────────────┐                    ┌──────────────────┐    │
│  │ Anomaly Detector │                    │    Attacker      │    │
│  │     .50          │                    │     .60          │    │
│  │  Isolation Forest│                    │ 3 attack modes:  │    │
│  │  Real-time scoring│                   │  - manipulation  │    │
│  │  Auto-response   │                    │  - replay        │    │
│  └────────┬─────────┘                    │  - dos           │    │
│           │                              └──────────────────┘    │
│           │ Modbus write (reg 1)                                 │
│           │ on anomaly alert                                     │
│           ▼                                                      │
│  ┌──────────────────┐                                            │
│  │   PLC iptables   │  Blocks 172.20.0.60 on alert              │
│  │   auto-block     │                                            │
│  └──────────────────┘                                            │
│                                                                   │
│  ┌──────────┐  ┌────────────┐  ┌──────────────────┐             │
│  │  Snort   │  │ StrongSwan │  │    IoTGoat       │             │
│  │  IDS .20 │  │ VPN .30    │  │    QEMU .40      │             │
│  └──────────┘  └────────────┘  └──────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

## Container Roles

### PLC (`172.20.0.10`)
Python-based Modbus TCP server simulating a temperature sensor (cycles 25-30°C). Runs iptables firewall to whitelist authorized write IPs. Monitors register 1 for block signals from the detector and executes iptables rules to isolate attackers.

### HMI (`172.20.0.11`)
Reads temperature from PLC every 3 seconds and logs it. Represents the legitimate operator interface.

### Anomaly Detector (`172.20.0.50`)
Polling engine using scikit-learn Isolation Forest for unsupervised anomaly detection. Trains on 50 initial samples, then scores each new reading. On anomaly (score < -0.3), writes block signal to PLC register 1. Clears the block after 3 consecutive normal readings.

### Attacker (`172.20.0.60`)
Simulates three ICS attack scenarios:
- **Register Manipulation**: writes extreme values (99, -5, 120, 255)
- **Replay Attack**: records legitimate values, replays them rapidly
- **DoS**: floods Modbus writes at maximum rate

### Snort IDS (`172.20.0.20`)
Network-based intrusion detection with 10 custom Modbus TCP rules covering function code abuse, rapid connections, and protocol anomalies.

### StrongSwan (`172.20.0.30`)
IKEv2 VPN server with certificate-based authentication (no PSK). Auto-generates CA and server certificates on build.

### IoTGoat (`172.20.0.40`)
OWASP IoTGoat vulnerable firmware running in QEMU with forwarded ports (2222/SSH, 8080/HTTP, 4443/HTTPS).

## Data Flow

```
Normal operation:
  PLC ──(temp 25-30°C)──► HMI (reads every 3s)
  PLC ──(temp 25-30°C)──► Detector (reads every 5s)
  Detector ──(score > -0.3)──► logs: normal

Attack detected:
  Attacker ──(write extreme value)──► PLC
  PLC ──(temp 99°C)──► Detector
  Detector ──(score < -0.3)──► ALERT
  Detector ──(write reg 1 = 1)──► PLC
  PLC ──(iptables -D ACCEPT .60)──► blocks attacker
```

## Auto-Response Sequence

```
1. Anomaly detected (score < threshold)
2. Detector writes 1 to PLC register 1
3. PLC update_registers loop reads reg 1 change
4. PLC calls block_attacker()
5. iptables removes ACCEPT rule for 172.20.0.60
6. Attacker traffic falls through to default DROP rule
7. After 3 consecutive normal readings, detector writes 0
8. PLC calls unblock_attacker()
9. iptables re-inserts ACCEPT rule for 172.20.0.60
```

## Security Layers

| Layer | Mechanism | Location |
|-------|-----------|----------|
| Network | iptables IP whitelist (port 502) | PLC container |
| Application | Write rate limiting (10 writes/10s) | PLC Python code |
| Detection | Isolation Forest anomaly scoring | Detector container |
| Response | Automatic iptables block on alert | PLC container |
| Monitoring | Snort IDS with custom Modbus rules | Snort container |
| Encryption | IKEv2 VPN with cert-based auth | StrongSwan container |
