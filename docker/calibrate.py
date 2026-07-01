from __future__ import annotations

import argparse
import json
import logging
import random
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, TypedDict

import joblib  # type: ignore[import]
import numpy as np
from sklearn.ensemble import IsolationForest  # type: ignore[import]

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

PLC_HOST = "plc"
PLC_PORT = 502
POLL_INTERVAL = 5
MODEL_PATH = "model.joblib"


class Sample(TypedDict):
    temp: float
    time_delta: float
    temp_delta: float


def _simulate_normal_temp(cycle: int) -> float:
    if (cycle // 10) % 2 == 0:
        base = 25.0 + (cycle % 10)
        return base + random.uniform(-0.5, 0.5)
    return 30.0 - (cycle % 10) + random.uniform(-0.5, 0.5)


def _collect_live(client: Any, count: int) -> Deque[Sample]:
    buffer: Deque[Sample] = deque(maxlen=count)
    last_temp: float | None = None
    last_ts: float | None = None
    collected = 0
    logger.info(
        "[CALIBRATE] Collecting %d live samples from PLC (est. %.1f min)...",
        count,
        count * POLL_INTERVAL / 60,
    )
    while collected < count:
        try:
            result = client.read_holding_registers(address=0, count=1, unit=1)
            if not result.isError():
                temp = float(result.registers[0])
                now = time.time()
                time_delta = now - last_ts if last_ts is not None else POLL_INTERVAL
                temp_delta = temp - last_temp if last_temp is not None else 0.0
                buffer.append({"temp": temp, "time_delta": time_delta, "temp_delta": temp_delta})
                last_temp = temp
                last_ts = now
                collected += 1
                if collected % 100 == 0:
                    logger.info("[CALIBRATE] %d/%d samples collected", collected, count)
            time.sleep(POLL_INTERVAL)
        except Exception:
            logger.exception("[CALIBRATE] Read error, retrying...")
            time.sleep(POLL_INTERVAL)
    return buffer


def _collect_simulated(count: int) -> Deque[Sample]:
    logger.info("[CALIBRATE] Generating %d simulated normal samples...", count)
    buffer: Deque[Sample] = deque(maxlen=count)
    last_temp = 27.0
    last_ts = time.time()
    for i in range(count):
        temp = _simulate_normal_temp(i)
        now = last_ts + POLL_INTERVAL + random.uniform(-0.2, 0.2)
        time_delta = now - last_ts
        temp_delta = temp - last_temp
        buffer.append({"temp": temp, "time_delta": time_delta, "temp_delta": temp_delta})
        last_temp = temp
        last_ts = now
    return buffer


def _extract_features(buffer: Deque[Sample]) -> np.ndarray:
    temps = np.array([r["temp"] for r in buffer])
    time_deltas = np.array([r["time_delta"] for r in buffer])
    temp_deltas = np.array([r["temp_delta"] for r in buffer])
    return np.column_stack([temps, time_deltas, temp_deltas])


def _analyze_scores(
    features: np.ndarray,
    model: IsolationForest,
    current_threshold: float,
) -> Dict[str, Any]:
    scores = model.decision_function(features)
    fp_count = int(np.sum(scores < current_threshold))
    p5 = float(np.percentile(scores, 5))
    p1 = float(np.percentile(scores, 1))
    p01 = float(np.percentile(scores, 0.1))
    min_score = float(np.min(scores))
    margin = abs(min_score) * 0.2
    recommended = round(min_score - margin, 4)

    return {
        "sample_count": len(scores),
        "score_stats": {
            "min": min_score,
            "max": float(np.max(scores)),
            "mean": float(np.mean(scores)),
            "median": float(np.median(scores)),
            "std": float(np.std(scores)),
            "p5": p5,
            "p1": p1,
            "p0.1": p01,
        },
        "temp_stats": {
            "min": float(np.min(features[:, 0])),
            "max": float(np.max(features[:, 0])),
            "mean": float(np.mean(features[:, 0])),
            "std": float(np.std(features[:, 0])),
        },
        "threshold": {
            "current": current_threshold,
            "recommended": recommended,
            "current_fp_count": fp_count,
            "current_fp_rate": round(fp_count / len(scores), 4),
            "margin_below_min": round(margin, 4),
        },
    }


def _print_report(report: Dict[str, Any], source: str) -> None:
    fp_rate = report["threshold"]["current_fp_rate"] * 100
    s = report["score_stats"]
    t = report["temp_stats"]
    h = report["threshold"]

    lines = [
        "=" * 60,
        "BASELINE CALIBRATION REPORT",
        "=" * 60,
        f"Source:           {source}",
        f"Samples:          {report['sample_count']}",
        f"Temp range:       {t['min']:.1f} - {t['max']:.1f} C",
        f"Temp mean+/-std:  {t['mean']:.1f} +/- {t['std']:.1f} C",
        "",
        "Score Distribution:",
        f"  Min:     {s['min']:.4f}",
        f"  P0.1:    {s['p0.1']:.4f}",
        f"  P1:      {s['p1']:.4f}",
        f"  P5:      {s['p5']:.4f}",
        f"  Median:  {s['median']:.4f}",
        f"  Max:     {s['max']:.4f}",
        "",
        "Threshold Analysis:",
        f"  Current:        {h['current']}",
        f"  Recommended:    {h['recommended']}",
        f"  Current FPs:    {h['current_fp_count']} / {report['sample_count']} ({fp_rate:.1f}%)",
        f"  Margin below min: {h['margin_below_min']:.4f}",
        "",
    ]
    if h["current_fp_rate"] > 0:
        lines.append(
            f"> Current threshold produces FPs. Set ANOMALY_THRESHOLD = {h['recommended']} in anomaly-detector.py"
        )
    else:
        lines.append("> Current threshold produces zero FPs on this baseline.")
    lines.append("=" * 60)

    logger.info("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate anomaly detector threshold")
    parser.add_argument("--source", choices=["live", "simulate"], default="simulate")
    parser.add_argument("--samples", type=int, default=1440)
    parser.add_argument("--output", type=str, default="baseline_report.json")
    args = parser.parse_args()

    if args.source == "live":
        from pymodbus.client import ModbusTcpClient

        client = ModbusTcpClient(PLC_HOST, port=PLC_PORT)
        client.connect()
        buffer = _collect_live(client, args.samples)
        client.close()
    else:
        buffer = _collect_simulated(args.samples)

    X = _extract_features(buffer)
    model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)  # type: ignore[arg-type]
    model.fit(X)
    joblib.dump(model, MODEL_PATH)  # type: ignore[arg-type]

    report = _analyze_scores(X, model, -0.3)
    report["source"] = args.source
    report["collected_at"] = datetime.now(timezone.utc).isoformat()

    output_path = Path(args.output)
    output_path.write_text(json.dumps(report, indent=2))
    logger.info("[CALIBRATE] Report saved to %s", args.output)

    _print_report(report, args.source)


if __name__ == "__main__":
    main()
