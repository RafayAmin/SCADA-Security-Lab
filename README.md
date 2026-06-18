# SCADA Security Lab

A Docker-based SCADA/ICS security lab for testing intrusion detection, anomaly detection, and VPN security in a realistic industrial control environment.

## Architecture

```
┌────────────────────────────────────────────┐
│              Docker Network                 │
│              scada_net                      │
│                                              │
│  ┌──────────┐   Modbus TCP   ┌──────────┐   │
│  │   PLC    │◄──────────────►│   HMI    │   │
│  │ :502     │                │ :Read    │   │
│  └────┬─────┘                └──────────┘   │
│       │                                      │
│       │ Network monitoring                   │
│       ▼                                      │
│  ┌──────────┐                                │
│  │  Snort   │  IDS monitoring Modbus traffic │
│  │  IDS     │                                │
│  └──────────┘                                │
│                                              │
│  ┌────────────┐   ┌──────────────┐          │
│  │ StrongSwan │   │   IoTGoat    │          │
│  │ VPN Server │   │ Vuln. IoT OS │          │
│  └────────────┘   └──────────────┘          │
└────────────────────────────────────────────┘
```

## Services

| Service | Description |
|---------|-------------|
| **PLC** | Modbus TCP simulator with temperature simulation, iptables IP whitelisting, and write rate limiting |
| **HMI** | Reads temperature from PLC every 3 seconds |
| **Snort** | Network IDS monitoring Modbus traffic on port 502 with custom SCADA detection rules |
| **StrongSwan** | IKEv2 VPN server with certificate-based authentication |
| **IoTGoat** | OWASP IoTGoat vulnerable firmware running in QEMU (intentionally vulnerable) |

## Quick Start

```bash
docker compose up --build -d
```

Verify all services are running:

```bash
docker compose ps
```

Check HMI is reading temperature from PLC:

```bash
docker compose logs hmi
```

## Security Features

- **IP whitelisting**: PLC only accepts Modbus traffic from authorized IPs (iptables)
- **Write rate limiting**: Max 10 Modbus writes per 10-second window
- **Snort IDS rules**: 10 custom SCADA-specific detection rules for Modbus attacks
- **IKEv2 VPN**: Certificate-based VPN with strongSwan (PSK disabled)
- **Local-only port binding**: PLC port 502 bound to 127.0.0.1 only

## Custom Snort Rules

The lab includes 10 custom Snort rules covering:

- Modbus write function codes (05, 06, 0F, 10)
- Modbus read function codes (01, 03) from external sources
- Non-standard function code detection
- Invalid protocol ID detection
- Rapid connection DoS detection
- Function code scanning detection

## Requirements

- Docker Engine 24+
- Docker Compose v2

## Troubleshooting / Known Issues

- **StrongSwan failing to start**: If the VPN container crashes on startup, the certificate generation script may have failed silently. Check `docker logs scada-security-lab-strongswan-1`. If the CA cert expired, rebuild the image with `docker compose build strongswan --no-cache`.
- **HMI cannot connect to PLC**: Make sure you aren't running a local Modbus server on your host on port 502 — Docker might route traffic there instead of the container. Also verify the PLC iptables rules haven't blocked the HMI IP.
- **Snort not detecting Modbus traffic**: The container needs `NET_ADMIN` and `NET_RAW` capabilities for packet capture. If you see "Failed to open eth0" in the logs, the interface name might differ on your system — update the `-i` flag in `Dockerfile.snort`.

## License

MIT
