from __future__ import annotations

import logging
import time
from collections import deque
from typing import Deque, TypedDict

import joblib  # type: ignore[import]
import numpy as np
from pymodbus.client import ModbusTcpClient
from sklearn.ensemble import IsolationForest  # type: ignore[import]

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

PLC_HOST = "plc"
PLC_PORT = 502
POLL_INTERVAL = 5
WINDOW_SIZE = 100
TRAIN_SAMPLES = 50
MODEL_PATH = "/app/model.joblib"
ANOMALY_THRESHOLD = -0.3
CONTAMINATION = 0.05


class Sample(TypedDict):
    temp: float
    time_delta: float
    temp_delta: float
    timestamp: float


def _read_temperature(client: ModbusTcpClient) -> float | None:
    result = client.read_holding_registers(address=0, count=1, unit=1)
    return None if result.isError() else float(result.registers[0])  # type: ignore[union-attr]


def _extract_features(buffer: Deque[Sample]) -> np.ndarray:
    temps = np.array([r["temp"] for r in buffer])
    time_deltas = np.array([r["time_delta"] for r in buffer])
    temp_deltas = np.array([r["temp_delta"] for r in buffer])
    return np.column_stack([temps, time_deltas, temp_deltas])


def _collect_initial_data(client: ModbusTcpClient) -> Deque[Sample]:
    buffer: Deque[Sample] = deque(maxlen=WINDOW_SIZE)
    last_temp: float | None = None
    last_ts: float | None = None
    while len(buffer) < TRAIN_SAMPLES:
        try:
            temp = _read_temperature(client)
            if temp is not None:
                now = time.time()
                time_delta = now - last_ts if last_ts is not None else POLL_INTERVAL
                temp_delta = temp - last_temp if last_temp is not None else 0.0
                buffer.append(
                    {
                        "temp": temp,
                        "time_delta": time_delta,
                        "temp_delta": temp_delta,
                        "timestamp": now,
                    }
                )
                last_temp = temp
                last_ts = now
                logger.info(
                    "[DETECTOR] Training sample %d/%d: temp=%.1f°C",
                    len(buffer),
                    TRAIN_SAMPLES,
                    temp,
                )
            else:
                logger.warning("[DETECTOR] PLC read error during training")
            time.sleep(POLL_INTERVAL)
        except Exception:
            logger.exception("[DETECTOR] Training collection failed")
            time.sleep(POLL_INTERVAL)
    return buffer


def _train_model(buffer: Deque[Sample]) -> IsolationForest:
    X = _extract_features(buffer)
    model = IsolationForest(
        n_estimators=100,
        contamination=CONTAMINATION,  # type: ignore[arg-type]
        random_state=42,
    )
    model.fit(X)
    joblib.dump(model, MODEL_PATH)  # type: ignore[arg-type]
    logger.info("[DETECTOR] Model trained on %d samples, saved to %s", len(buffer), MODEL_PATH)
    return model


def _load_or_train(client: ModbusTcpClient) -> tuple[IsolationForest, Deque[Sample]]:
    try:
        model: IsolationForest = joblib.load(MODEL_PATH)  # type: ignore[assignment]
        logger.info("[DETECTOR] Loaded existing model from %s", MODEL_PATH)
        buffer = _collect_initial_data(client)
        return model, buffer
    except FileNotFoundError:
        logger.info("[DETECTOR] No existing model found, training from scratch")
        buffer = _collect_initial_data(client)
        model = _train_model(buffer)
        return model, buffer


def main() -> None:
    client = ModbusTcpClient(PLC_HOST, port=PLC_PORT)
    client.connect()
    model, buffer = _load_or_train(client)
    logger.info("[DETECTOR] Entering detection phase")

    last_temp = buffer[-1]["temp"]
    last_ts = time.time()

    while True:
        try:
            now = time.time()
            temp = _read_temperature(client)
            if temp is None:
                logger.warning("[DETECTOR] PLC read failed during detection")
                time.sleep(POLL_INTERVAL)
                continue

            time_delta = now - last_ts
            temp_delta = temp - last_temp
            last_temp = temp
            last_ts = now

            X = np.array([[temp, time_delta, temp_delta]])
            score = model.decision_function(X)[0]

            buffer.append(
                {
                    "temp": temp,
                    "time_delta": time_delta,
                    "temp_delta": temp_delta,
                    "timestamp": now,
                }
            )

            if score < ANOMALY_THRESHOLD:
                logger.warning(
                    "[DETECTOR] ALERT: Anomaly detected! temp=%.1f°C, time_delta=%.2fs, temp_delta=%.1f, score=%.4f",
                    temp,
                    time_delta,
                    temp_delta,
                    score,
                )
            else:
                logger.info(
                    "[DETECTOR] Normal: temp=%.1f°C, time_delta=%.2fs, score=%.4f",
                    temp,
                    time_delta,
                    score,
                )

            if len(buffer) % 50 == 0:
                model = _train_model(buffer)

            time.sleep(POLL_INTERVAL)
        except Exception:
            logger.exception("[DETECTOR] Detection loop error")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
