# subscriber.py
import os
import json
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import mysql.connector

# ── MQTT settings ───────────────────────────────────────────────────────────────
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT   = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC  = os.getenv("MQTT_TOPIC", "vejrstationsproject/data")

# ── MySQL settings ─────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "user":     os.getenv("DB_USER", "weather"),
    "password": os.getenv("DB_PASS", "Datait2025!"),
    "database": os.getenv("DB_NAME", "weather"),
    "autocommit": False,
}

# ── Table & insert ─────────────────────────────────────────────────────────────
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS weather_readings (
  id            BIGINT AUTO_INCREMENT PRIMARY KEY,
  received_at   DATETIME(6) NOT NULL,
  temp_c        DOUBLE NULL,
  humidity_pct  DOUBLE NULL,
  pressure_hpa  DOUBLE NULL,
  rain_analog   INT NULL,
  rain_digital  TINYINT NULL,
  rssi_dbm      INT NULL,
  INDEX idx_received_at (received_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

INSERT_SQL = """
INSERT INTO weather_readings
(received_at, temp_c, humidity_pct, pressure_hpa, rain_analog, rain_digital, rssi_dbm)
VALUES (%s, %s, %s, %s, %s, %s, %s);
"""

# ── Helpers ────────────────────────────────────────────────────────────────────
def to_float(x):
    try:
        return float(x) if x is not None else None
    except (ValueError, TypeError):
        return None

def to_int(x):
    try:
        return int(float(x)) if x is not None else None
    except (ValueError, TypeError):
        return None

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def ensure_schema():
    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(CREATE_TABLE_SQL)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("[WARN] Could not ensure schema:", e)

# ── MQTT callbacks ─────────────────────────────────────────────────────────────
def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Connected with code {rc}. Subscribing to '{MQTT_TOPIC}'")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        raw = msg.payload.decode("utf-8", errors="replace")
        data = json.loads(raw)

        # Expecting these keys from the gateway:
        # t (°C), h (%), p (hPa), RainA (int), RainD (0/1), RSSI (dBm)
        temp     = to_float(data.get("t"))
        humidity = to_float(data.get("h"))
        pressure = to_float(data.get("p"))
        rainA    = to_int(data.get("RainA"))
        rainD    = to_int(data.get("RainD"))
        rssi     = to_int(data.get("RSSI"))

        # Require at least one main sensor field
        if temp is None and humidity is None and pressure is None:
            print(f"[SKIP] Missing main fields in message: {raw}")
            return

        received_at = datetime.now(timezone.utc)

        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            INSERT_SQL,
            (received_at, temp, humidity, pressure, rainA, rainD, rssi)
        )
        conn.commit()
        cur.close()
        conn.close()

        print(
            f"[OK] {received_at.isoformat()} "
            f"t={temp}C h={humidity}% p={pressure}hPa RainA={rainA} RainD={rainD} RSSI={rssi}dBm"
        )

    except json.JSONDecodeError:
        print(f"[ERR] Invalid JSON: {msg.payload!r}")
    except Exception as e:
        print("[ERR] DB/message error:", e)

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    ensure_schema()

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    print(f"[RUN] Listening on mqtt://{MQTT_BROKER}:{MQTT_PORT} topic '{MQTT_TOPIC}'")
    client.loop_forever()

if __name__ == "__main__":
    main()
