# Demo Video Script

## Duration: ~5 minutes

---

### 0:00 — Intro (15s)

> "I built an AI-powered anomaly detection system for ICS/SCADA environments. It learns normal PLC behavior patterns using unsupervised learning — Isolation Forest — detects cyber attacks including register manipulation, replay attacks, and DoS in under 5 seconds with 90%+ accuracy, and automatically blocks malicious traffic. The entire stack runs in Docker, making it reproducible and demo-ready."

---

### 0:15 — Stack Overview (45s)

Show terminal:

```bash
# Architecture overview
docker compose ps
```

Narrate:
- "7 containers on a dedicated Docker network (172.20.0.0/24)"
- "PLC simulates a temperature sensor cycling between 25-30°C"
- "HMI reads temperature every 3 seconds — the legitimate operator"
- "Anomaly detector polls PLC every 5 seconds, runs Isolation Forest scoring"
- "Attacker container for simulating attacks (disabled by default)"
- "Snort IDS monitoring Modbus traffic, StrongSwan VPN, IoTGoat vulnerable VM"

---

### 1:00 — Normal Operation (45s)

```bash
# Show normal logs
docker compose logs plc --tail 5
docker compose logs hmi --tail 5
docker compose logs detector --tail 5
```

Narrate:
- "PLC cycling temperature between 25-30°C"
- "HMI reading normally"
- "Detector showing normal scores above threshold"
- "Model trained on 50 initial samples, continuously retrains every 250 samples"

---

### 1:45 — Attack 1: Register Manipulation (60s)

```bash
docker compose --profile attack run --rm attacker --mode manipulation --duration 30
```

Narrate:
- "Attacker writes extreme values — 99°C, -5°C, 120°C — to PLC holding register"
- "Detector picks up the anomaly on the next poll (within 5 seconds)"
- "Score drops below threshold → alert triggered"

Show detector logs:

```
[DETECTOR] ALERT: Anomaly detected! temp=99.0°C, score=-0.45
```

- "Detector writes block signal to PLC register 1"

Show PLC logs:

```
[PLC] Blocking attacker (172.20.0.60)...
[PLC] Attacker blocked
```

- "Attacker's IP is removed from iptables ACCEPT rules — traffic drops"

---

### 2:45 — Attack 2: Replay Attack (45s)

```bash
docker compose --profile attack run --rm attacker --mode replay --duration 30
```

Narrate:
- "Attacker records legitimate temperature values, then replays them rapidly"
- "Time deltas between writes are near-zero — this is physically impossible"
- "Detector flags the timing anomaly immediately"

Show detector log highlighting the time_delta:

```
[DETECTOR] ALERT: Anomaly detected! temp=27.0°C, time_delta=0.21s, score=-0.38
```

- "Auto-response triggers again, blocking the attacker"

---

### 3:30 — Attack 3: DoS (45s)

```bash
docker compose --profile attack run --rm attacker --mode dos --duration 30
```

Narrate:
- "Attacker floods Modbus writes at maximum rate"
- "PLC's rate limiter blocks excessive writes locally"
- "Detector also catches the frequency anomaly and triggers network-level block"
- "Defense in depth: application-level rate limiting + AI detection + iptables"

---

### 4:15 — Recovery (30s)

Show detector returning to normal after attack ends:

```
[DETECTOR] Normal: temp=27.0°C, time_delta=5.02s, score=0.12
[DETECTOR] Normal: temp=28.0°C, time_delta=4.98s, score=0.08
[DETECTOR] Normal: temp=28.0°C, time_delta=5.01s, score=0.15
[DETECTOR] Clearing block signal...
```

Narrate:
- "After 3 consecutive normal readings, detector clears the block"
- "Attacker ACCEPT rule is re-inserted"
- "System self-heals without manual intervention"

---

### 4:45 — Key Takeaways (15s)

- "Unsupervised learning — no labeled attack data needed"
- "Detection in under 5 seconds, 100% true positive rate in testing"
- "Fully automated response — no human-in-the-loop required"
- "Reproducible: one `docker compose up` brings the entire lab online"

> Links: [GitHub](https://github.com/RafayAmin/SCADA-Security-Lab)
