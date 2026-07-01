# SCADA Security Lab — AI-Powered ICS Anomaly Detection

A Docker-based SCADA/ICS security lab with AI-powered anomaly detection, attack simulation, and automated response in a realistic industrial control environment.

> *"Unsupervised learning (Isolation Forest) detects cyber attacks on PLCs — register manipulation, replay attacks, and DoS — in under 5 seconds with 90%+ accuracy, and automatically blocks malicious traffic."*

## Architecture

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

## Services

| Service | IP | Description |
|---------|----|-------------|
| **PLC** | .10 | Modbus TCP simulator with iptables firewall, rate limiting, and auto-block response |
| **HMI** | .11 | Reads temperature from PLC every 3 seconds |
| **Anomaly Detector** | .50 | Isolation Forest model trained on PLC behavior, real-time scoring, auto-response trigger |
| **Attacker** | .60 | Simulates register manipulation, replay, and DoS attacks (disabled by default) |
| **Snort** | .20 | Network IDS with 10 custom Modbus TCP detection rules |
| **StrongSwan** | .30 | IKEv2 VPN server with certificate-based authentication |
| **IoTGoat** | .40 | OWASP IoTGoat vulnerable firmware in QEMU |

## Quick Start

```bash
# Start the core stack
docker compose up --build -d plc hmi detector snort strongswan

# Wait for detector to finish training (approx 5 min)
docker compose logs -f detector
```

### Run Attacks

```bash
# Register manipulation (writes extreme values 99°C, -5°C, etc.)
docker compose --profile attack run --rm attacker --mode manipulation --duration 30

# Replay attack (records and replays stale values rapidly)
docker compose --profile attack run --rm attacker --mode replay --duration 30

# DoS attack (floods Modbus writes)
docker compose --profile attack run --rm attacker --mode dos --duration 30
```

### View Auto-Response

```bash
# Watch detector detect and trigger block
docker compose logs -f detector

# Watch PLC execute iptables block
docker compose logs -f plc
```

### Calibration

```bash
# Run baseline calibration (simulated 1440 samples, ~2 hours of data)
docker compose --profile calibrate run --rm calibrator --source simulate --samples 1440

# Or collect live data from a running PLC
docker compose --profile calibrate run --rm calibrator --source live --samples 500
```

## Auto-Response Flow

1. Anomaly Detector polls PLC temperature every 5 seconds
2. Isolation Forest scores each reading (features: temp, time_delta, temp_delta)
3. Score below threshold → detector writes `1` to PLC register 1
4. PLC detects register 1 change, runs `iptables -D INPUT` to remove attacker's ACCEPT rule
5. Attacker traffic falls through to default DROP rule
6. After 3 consecutive normal readings, detector writes `0` → PLC re-adds attacker ACCEPT rule

## Security Features

- **AI Anomaly Detection**: Unsupervised Isolation Forest trained on benign PLC behavior
- **Auto-Response**: Automatic iptables block within seconds of anomaly detection
- **IP Whitelisting**: PLC only accepts Modbus traffic from authorized IPs
- **Write Rate Limiting**: Max 10 Modbus writes per 10-second window
- **Snort IDS Rules**: 10 custom SCADA-specific detection rules
- **IKEv2 VPN**: Certificate-based VPN (no PSK)
- **Local-Only Binding**: PLC port 502 bound to 127.0.0.1

## Custom Snort Rules

10 custom rules covering: Modbus write function codes (05, 06, 0F, 10), read function codes from external sources, non-standard function codes, invalid protocol ID, rapid connection DoS, and function code scanning.

## Validation Results

| Criterion | Target | Measured | Status |
|-----------|--------|----------|--------|
| Detection latency | <5s | 3.7s avg | ✅ |
| True positive rate | >90% | 100% | ✅ |
| False positive rate | <5% | 0.21% | ✅ |
| Auto-response | <5s | 0.3s avg | ✅ |

Full report in [`docs/validation.md`](docs/validation.md).

## Requirements

- Docker Engine 24+
- Docker Compose v2

## Troubleshooting

- **StrongSwan fails**: Check `docker compose logs strongswan-1`. Rebuild with `docker compose build strongswan --no-cache` if certs expired.
- **HMI can't connect**: Verify no local Modbus server on port 502. Check PLC iptables haven't blocked the HMI IP.
- **Snort not detecting**: Container needs `NET_ADMIN` and `NET_RAW`. If interface name differs, update `-i` flag in `Dockerfile.snort`.

## License

MIT
