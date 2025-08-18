import json
import mysql.connector
import paho.mqtt.client as mqtt

#MQTT settings
MQTT_BROKER = "localhost"
MQTT_PRT = 1883
MQTT_TOPIC = "vejrstationsproject/data"

#MySQL settings
DB_CONFIG = {
  "host": "localhost",
  "user": "weather",
  "password": "Datait2025!",
  "database": "weather"
}

#Handle connection to MQTT broker
def on_connect(client, userdata, flags, rc):
  print("Connected to MQTT broker with result code " + str(rc))
  client.subscribe(MQTT_TOPIC)

#Handle incoming messages
def on_connect(client, userfata, msg):
  try:
    payload = json.loads(msg.payload.decode())
    temp = payload.get("temp")
    humidity = payload.get("humidity")
    pressure = payload.get("pressure")

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(
      "INSERT INTO readings (temp_c, humidity_pct, pressure_hpa) values (%s, %s, %s)",
      (temp, humidity, pressure)
    )
    conn.commit()
    cursor.close()
    conn.close()

    print(f"Inserted into DB: Temp={temp}, Hum={humidity}, Pressure={pressure}")

  except Exception as e:
    print("Error processing message:", e)

#Setup MQTT client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()
