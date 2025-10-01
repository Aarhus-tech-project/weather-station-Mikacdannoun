// This is the Receiver Arduino, the middleman between the sensor arduino and the linux server

#include <SPI.h>
#include <LoRa.h>
#include <WiFiS3.h>
#include <PubSubClient.h>

const int NSS = 10, RST = 9, DIO0 = 2;

// Wi-Fi / MQTT
const char* ssid       = "YOUR_SSID";
const char* pass       = "YOUR_PASS";
const char* mqttServer = "192.168.1.10"; // Linux server IP running Mosquitto
const int   mqttPort   = 1883;
const char* mqttTopic  = "vejrstationsproject/data";

WiFiClient net;
PubSubClient mqtt(net);

void ensureNet() {
  if (WiFi.status() != WL_CONNECTED) {
    WiFi.begin(ssid, pass);
    while (WiFi.status() != WL_CONNECTED) { delay(400); }
  }
  if (!mqtt.connected()) {
    while (!mqtt.connect("uno-r4-gateway")) { delay(400); }
  }
}

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\n[LoRa→MQTT gateway boot]");

  // LoRa radio
  LoRa.setPins(NSS, RST, DIO0);
  if (!LoRa.begin(433E6)) { Serial.println("LoRa init failed"); while (1) {} }
  LoRa.setSpreadingFactor(7);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(5);
  LoRa.setSyncWord(0x12);
  Serial.println("LoRa ready…");

  // Wi-Fi + MQTT
  WiFi.begin(ssid, pass);
  mqtt.setServer(mqttServer, mqttPort);
  Serial.println("Wi-Fi/MQTT init…");
}

String appendRssiToJson(const String& json, long rssi) {
  String out = json;
  int open = out.indexOf('{');
  int close = out.lastIndexOf('}');
  if (open != -1 && close != -1 && close > open) {
    if (out.charAt(close - 1) != '{') out = out.substring(0, close) + ",";
    else out = out.substring(0, close);
    out += "\"RSSI\":" + String(rssi) + "}";
    return out;
  } else {
    // Not JSON, wrap it
    String esc = "";
    for (size_t i = 0; i < json.length(); i++) {
      char c = json[i];
      if (c == '\"' || c == '\\') esc += '\\';
      esc += c;
    }
    return String("{\"payload\":\"") + esc + "\",\"RSSI\":" + String(rssi) + "}";
  }
}

void loop() {
  ensureNet();
  mqtt.loop();

  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    String msg;
    while (LoRa.available()) msg += (char)LoRa.read();
    long rssi = LoRa.packetRssi();

    // Print raw payload to Serial
    Serial.print("LoRa RX raw: ");
    Serial.println(msg);

    // Append RSSI and forward to MQTT
    String merged = appendRssiToJson(msg, rssi);
    mqtt.publish(mqttTopic, merged.c_str());
    Serial.println(String("MQTT → ") + mqttTopic + ": " + merged);
  }
}
