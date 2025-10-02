#define _BA 1
// #define TLS
// 100mhz
#include <Arduino.h>
#include <DallasTemperature.h>
#include <OneWire.h>
#include <PubSubClient.h>
#include <WiFiClientSecure.h>
#include <my_cfg.h>

#include "DHT.h"

#define SSID _wssid
#define PASS _wpass
#define PORT _port
#define BROKER _broker
#define MQTT_USER _name
#define MQTT_PASS _pass
#define MQTT_ID _mqtt_id

#define PUB_RELAY_STATUS _name "/relay/status"
#define SUB_RELAY_CMD _name "/relay/"

#define TIMEOUT 5000

// Buffers
#define BUFF_SIZE 128

// Safety variables
#define MAXTEMP_SAFETY 30
#define MAXTEMP_START 26
#define MAX_TIME 420

// Time variables
#define CONN_TIMEOUT_TICK_MS 10000
#define SCHEDULER_TICK_MS 5000
#define MINUTES_TO_MS_FACTOR 60000

// Relays - Design is due to ESP8266 ordering, keeping it the same for Pico
// i.e can be start, then use n-pins used
#define RELAY_PINS 4
#define RELAY_PIN0 10
#define RELAY_PIN1 11
#define RELAY_PIN2 12
#define RELAY_PIN3 13  // Using for heating
#define HEATER_PIN 3   // index 0-3, 3 is last index

// Temperature pins
#define DS18B20_PIN 22
#define DHT22_PIN 18

DHT sensor0(DHT22_PIN, DHT22);
float temp, humid;  // Store for periodically check temp
OneWire oneWire(DS18B20_PIN);
DallasTemperature sensor1(&oneWire);

// WIFI, MQTT
WiFiClientSecure client;
PubSubClient mqtt(BROKER, PORT, client);

char buffer0[BUFF_SIZE];
char buffer1[BUFF_SIZE];

struct Pins {
    uint8_t io;
    uint8_t idx;
    uint32_t timer_start;
    uint32_t timer_length;
    bool active;
} pins[RELAY_PINS];

void check_remote() {
    if (!Serial2.available()) return;

    uint8_t payload = Serial2.read();
    Tuple_u8 data = dev2dev_balc_unpack(payload);

    bool publish = false;
    if (data.idx == RELAY_PINS) {
        // Turn off all pins if active
        for (uint8_t i = 0; i < RELAY_PINS; i++) {
            Pins* p = &pins[i];
            if (p->active) {
                turn_pin_off(p);
                publish = true;
            }
        }
    } else {
        Pins* p = &pins[data.idx];
        p->active ? turn_pin_off(p) : turn_pin_on(p, MAX_TIME);
        publish = true;
    }
    if (publish) publish_relay_status();
}

void init_pins() {
    uint8_t const pin_ids[] = {RELAY_PIN0, RELAY_PIN1, RELAY_PIN2, RELAY_PIN3};

    for (uint8_t i = 0; i < RELAY_PINS; i++) {
        struct Pins* p = &pins[i];
        p->io = pin_ids[i];
        p->idx = i;
        p->timer_start = 0;
        p->timer_length = 0;
        p->active = false;

        pinMode(p->io, OUTPUT);
        digitalWrite(p->io, LOW);
    }
}

void publish_temp() {
    static char t[7], h[7];
    unsigned int len;

    temp = sensor0.readTemperature();
    humid = sensor0.readHumidity();
    if (!(isnan(temp) || isnan(humid) || temp < -50 || temp > 90 || humid < 0 || humid > 105)) {
        dtostrf(temp, 3, 2, t);
        dtostrf(humid, 3, 2, h);
        len = (unsigned int)sprintf(buffer0, "{\"temperature\":%s,\"humidity\":%s}", t, h);
        mqtt.publish(_name "/sensor/0", (const uint8_t*)buffer0, len, false);
    }

    sensor1.requestTemperatures();
    float sensor1_temp = sensor1.getTempCByIndex(0);
    if (-60 <= sensor1_temp && sensor1_temp <= 80) {
        len = sprintf(buffer0, "{\"temperature\":%.2f}", sensor1_temp);
        mqtt.publish(_name "/sensor/1", (const uint8_t*)buffer0, len, false);
    }
}

void check_heater() {
    Pins* p = &pins[HEATER_PIN];
    if (p->active && temp > MAXTEMP_SAFETY) {
        turn_pin_off(p);
        publish_relay_status();
    }
}

void check_relay_timers() {
    bool publish = false;

    uint32_t now = millis();
    for (uint8_t i = 0; i < RELAY_PINS; i++) {
        Pins* p = &pins[i];
        if (p->active && (now - p->timer_start >= p->timer_length)) {
            turn_pin_off(p);
            publish = true;
        }
    }
    if (publish) publish_relay_status();
}

void turn_pin_off(Pins* p) {
    p->active = false;
    digitalWrite(p->io, LOW);
    uint8_t payload = dev2dev_balc_pack(p->idx, 0);
    Serial2.write(payload);
}

void turn_pin_on(Pins* p, uint16_t minutes) {
    if (minutes <= 0) return;
    if (p->idx == HEATER_PIN && temp > MAXTEMP_START) return;

    p->active = true;
    p->timer_start = millis();
    p->timer_length = minutes * MINUTES_TO_MS_FACTOR;
    digitalWrite(p->io, HIGH);
    uint8_t payload = dev2dev_balc_pack(p->idx, 1);
    Serial2.write(payload);
}

void publish_relay_status() {
    uint8_t pos = 0;

    // poor persons json
    for (uint8_t i = 0; i < RELAY_PINS; i++) {
        const Pins* p = &pins[i];

        int len = sprintf(buffer1, ",\"%u\":%s", i, p->active ? "true" : "false");
        for (uint8_t j = 0; j < len; j++) buffer0[pos++] = buffer1[j];
    }
    buffer0[0] = '{';
    buffer0[pos] = '}';
    buffer0[pos + 1] = '\0';
    mqtt.publish(PUB_RELAY_STATUS, buffer0, 1);
}

void publish_relay_remaining() {
    uint8_t pos = 0;
    uint32_t now = millis();

    for (uint8_t i = 0; i < RELAY_PINS; i++) {
        const Pins* p = &pins[i];

        uint32_t timeleft = p->active ? (p->timer_length - (now - p->timer_start)) / 1000 : 0;
        int len = sprintf(buffer1, ",\"%u\":%u", i, timeleft);
        for (uint8_t j = 0; j < len; j++) buffer0[pos++] = buffer1[j];
    }
    buffer0[0] = '{';
    buffer0[pos] = '}';
    buffer0[pos + 1] = '\0';
    mqtt.publish(SUB_RELAY_CMD "remaining", buffer0, false);
}

void on_message(char* topic, unsigned char* payload, unsigned int payload_length) {
    if (payload_length == 0 || payload_length > 15) return;

    char buf[BUFF_SIZE];
    memcpy(buf, payload, payload_length);
    buf[payload_length] = '\0';

    char last_char = topic[strlen(topic) - 1];
    if (last_char == 'd') {  // command
        if (strcmp(buf, "remaining") == 0) publish_relay_remaining();
        return;
    }

    uint8_t start = 0;
    uint8_t end = RELAY_PINS;
    if (last_char != 'l') {
        start = last_char - '0';
        end = start + 1;
    }

    char* end_char;
    long val = strtol(buf, &end_char, 10);
    if (end_char == buf) return;

    if (val > MAX_TIME) {
        val = MAX_TIME;
    } else if (val < 0) {
        val = 0;
    }
    uint16_t value = (uint16_t)val;

    bool publish = false;
    if (value == 0) {
        for (uint8_t i = start; i < end; i++) {
            Pins* p = &pins[i];
            if (p->active) {
                turn_pin_off(p);
                publish = true;
            }
        }
    } else {
        for (uint8_t i = start; i < end; i++) {
            Pins* p = &pins[i];
            if (!p->active) publish = true;
            // Different here as to update the value to pin should run. "Upsert"
            turn_pin_on(p, value);
        }
    }
    if (publish) publish_relay_status();
}

void connect_wifi() {
    WiFi.mode(WIFI_STA);
    WiFi.begin(SSID, PASS);
}

void setup() {
    Serial2.setTX(4);
    Serial2.setRX(5);
    Serial2.begin(115200);

    sensor0.begin();
    sensor1.begin();

    init_pins();

    connect_wifi();
    while (WiFi.status() != WL_CONNECTED) delay(250);

    client.setCACert(ca_cert);
    client.setCertificate(client_cert);
    client.setPrivateKey(client_key);

    mqtt.setCallback(on_message);
}

void loop() {
    static uint32_t last_scheduler_tick = 0, connection_conn_timeout = 0;
    uint32_t now = millis();

    if (WiFi.status() == WL_CONNECTED) {
        if (!mqtt.loop()) {
            if (mqtt.connect(MQTT_ID, MQTT_USER, MQTT_PASS)) {
                mqtt.publish("void", MQTT_USER);

                for (uint8_t i = 0; i < RELAY_PINS; i++) {
                    sprintf(buffer0, SUB_RELAY_CMD "%u", i);
                    mqtt.subscribe(buffer0, 1);
                }
                mqtt.subscribe(SUB_RELAY_CMD "all", 1);
                mqtt.subscribe(SUB_RELAY_CMD "command", 1);
                delay(100);
                publish_relay_status();
            } else {
                delay(TIMEOUT);
            }
        }
    } else if (now - connection_conn_timeout >= CONN_TIMEOUT_TICK_MS) {
        connection_conn_timeout = now;
        connect_wifi();
    }

    check_remote();

    if (now - last_scheduler_tick >= SCHEDULER_TICK_MS) {
        last_scheduler_tick = now;

        publish_temp();
        check_heater();
        check_relay_timers();
    }
}
