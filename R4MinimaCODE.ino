// This is the code for the Sensor connected Arduino which sends LoRa-JSON payloads to the receiver Arduino

#include <SPI.h>
#include <LoRa.h>
#include <Wire.h>
#include <Adafruit_BME280.h>  // Install "Adafruit BME280 Library"
#include <Adafruit_Sensor.h>

const int NSS = 10, RST = 9, DIO0 = 2;

// Rain sensor pins (adjust if you wired differently)
const int RAIN_ANALOG_PIN  = A0;  // raw analog value (0–1023)
const int RAIN_DIGITAL_PIN = 3;   // optional digital (0/1) from comparator

Adafruit_BME280 bme;
uint32_t seq = 0;

bool beginBME() {
  if (bme.begin(0x76)) return true;
  if (bme.begin(0x77)) return true;
  return false;
}

void setup() {
  Serial.begin(115200);
  delay(200);

  pinMode(RAIN_ANALOG_PIN, INPUT);
  pinMode(RAIN_DIGITAL_PIN, INPUT);

  Wire.begin();
  if (!beginBME()) {
    Serial.println("BME280 not found on 0x76 or 0x77");
    while (1) { delay(1000); }
  }

  LoRa.setPins(NSS, RST, DIO0);
  if (!LoRa.begin(433E6)) { // you’re on 433 now; keep receiver the same
    Serial.println("LoRa init failed");
    while (1) { delay(1000); }
  }
  LoRa.setSpreadingFactor(7);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(5);
  // Optional but good: set a sync word so only your nodes talk
  LoRa.setSyncWord(0x12);

  Serial.println("Sender ready");
}

void loop() {
  // Read sensors
  float t = bme.readTemperature();         // °C
  float h = bme.readHumidity();            // %
  float p = bme.readPressure() / 100.0f;   // hPa
  int   rainAnalog = analogRead(RAIN_ANALOG_PIN); // 0(dry)…1023(wet) varies by board
  int   rainDigital = digitalRead(RAIN_DIGITAL_PIN); // 0/1 thresholded

  // Build compact JSON (no spaces to save airtime)
  // NOTE: Keys are generic; if your old Python subscriber expects specific names,
  // rename keys to match it later (e.g., "temperature", "humidity", etc.).
  unsigned long ts = millis();
  String json = String("{\"seq\":") + seq++ +
                ",\"ts\":" + ts +
                ",\"t\":" + String(t,1) +
                ",\"h\":" + String(h,1) +
                ",\"p\":" + String(p,1) +
                ",\"rainA\":" + rainAnalog +
                ",\"rainD\":" + rainDigital +
                "}";

  // Send
  LoRa.beginPacket();
  LoRa.print(json);
  LoRa.endPacket();

  Serial.println("TX: " + json);
  delay(2000); // keep duty-cycle reasonable
}
