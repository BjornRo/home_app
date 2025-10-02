#define _BA 1

#include <Arduino.h>
#include <DallasTemperature.h>
#include <ESP8266WiFi.h>
#include <OneWire.h>
#include <PubSubClient.h>
#include <WiFiClientSecure.h>
#include <my_cfg.h>

#include "DHT.h"

// WEMOS D1 MINI

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
#define SCHEDULER_TICK_MS 5000
#define MINUTES_TO_MS_FACTOR 60000

// Relays
#define RELAY_PINS 4
#define RELAY_PIN0 14  // D5
#define RELAY_PIN1 12  // D6
#define RELAY_PIN2 13  // D7
#define RELAY_PIN3 16  // D0 -- "Special" usage pin. Using for heating
#define HEATER_PIN 3

// Temperature pins
#define DS18B20_PIN 5  // D1
#define DHT22_PIN 4    // D2

DHT sensor0(DHT22_PIN, DHT22);
float temp, humid;  // Store for periodically check temp
OneWire oneWire(DS18B20_PIN);
DallasTemperature sensor1(&oneWire);

// WIFI, MQTT
WiFiClientSecure wifi;
PubSubClient mqtt(wifi);

char msg_buff_tmp[BUFF_SIZE];
char msg_buff[BUFF_SIZE];

struct Pins {
    uint8_t id;
    uint32_t timer_start;
    uint32_t timer_length;
    bool active;
} pins[RELAY_PINS];

void init_pins() {
    uint8_t const pin_ids[] = {RELAY_PIN0, RELAY_PIN1, RELAY_PIN2, RELAY_PIN3};

    for (uint8_t i = 0; i < RELAY_PINS; i++) {
        struct Pins* pin = &pins[i];
        pin->id = pin_ids[i];
        pin->timer_start = 0;
        pin->timer_length = 0;
        pin->active = false;

        pinMode(pin->id, OUTPUT);
        digitalWrite(pin->id, LOW);
    }
}

void publish_temp() {
    static char t[7], h[7];
    temp = sensor0.readTemperature();
    humid = sensor0.readHumidity();
    if (!(isnan(temp) || isnan(humid) || temp < -50 || temp > 90 || humid < 0 || humid > 105)) {
        dtostrf(temp, 3, 2, t);
        dtostrf(humid, 3, 2, h);
        sprintf(msg_buff, "{\"temperature\":%s,\"humidity\":%s}", t, h);
        mqtt.publish(_name "/sensor/0", msg_buff);
    }

    sensor1.requestTemperatures();
    float sensor1_temp = sensor1.getTempCByIndex(0);
    if (-60 <= sensor1_temp && sensor1_temp <= 80) {
        sprintf(msg_buff, "{\"temperature\":%.2f}", sensor1_temp);
        mqtt.publish(_name "/sensor/1", msg_buff);
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
    for (uint8_t i = 0; i < RELAY_PINS; i++) {
        Pins* p = &pins[i];
        if (p->active && (millis() - p->timer_start >= p->timer_length)) {
            turn_pin_off(p);
            publish = true;
        }
    }
    if (publish) publish_relay_status();
}

void turn_pin_off(Pins* pin) {
    digitalWrite(pin->id, LOW);
    pin->active = false;
}

void turn_pin_on(Pins* p, uint16_t minutes) {
    if (minutes <= 0) return;
    if (p->id == (&pins[HEATER_PIN])->id && temp > MAXTEMP_START) return;

    p->active = true;
    p->timer_start = millis();
    p->timer_length = minutes * MINUTES_TO_MS_FACTOR;
    digitalWrite(p->id, HIGH);
}

void publish_relay_status() {
    uint8_t pos = 0;

    // poor persons json
    for (uint8_t i = 0; i < RELAY_PINS; i++) {
        const Pins* p = &pins[i];

        int len = sprintf(msg_buff_tmp, ",\"%u\":%s", p->id, p->active ? "true" : "false");
        for (uint8_t j = 0; j < len; j++) msg_buff[pos++] = msg_buff_tmp[j];
    }
    msg_buff[0] = '{';
    msg_buff[pos] = '}';
    msg_buff[pos + 1] = '\0';
    mqtt.publish(PUB_RELAY_STATUS, msg_buff, 1);
}

void on_message(char* topic, unsigned char* payload, unsigned int payload_length) {
    if (payload_length == 0 || payload_length > 10) return;

    memcpy(msg_buff, payload, payload_length);
    msg_buff[payload_length] = '\0';

    char* end_char;
    long val = strtol(msg_buff, &end_char, 10);
    if (end_char == msg_buff) return;

    if (val > MAX_TIME) {
        val = MAX_TIME;
    } else if (val < 0) {
        val = 0;
    }
    uint16_t value = (uint16_t)val;

    char last_char = topic[strlen(topic) - 1];
    uint8_t start = 0;
    uint8_t end = RELAY_PINS;
    if (last_char != 'l') {
        start = last_char - '0';
        end = start + 1;
    }

    if (value == 0) {
        for (uint8_t i = start; i < end; i++) turn_pin_off(&pins[i]);
    } else {
        for (uint8_t i = start; i < end; i++) turn_pin_on(&pins[i], value);
    }
}

void setup() {
    // sensor0.begin();
    // sensor1.begin();

    init_pins();

    WiFi.mode(WIFI_STA);
    WiFi.begin(SSID, PASS);
    while (WiFi.status() != WL_CONNECTED) delay(250);

    wifi.setClientRSACert(&client_crt, &key);
    wifi.setFingerprint(mqtt_server_fingerprint);

    mqtt.setServer(BROKER, PORT);
    mqtt.setCallback(on_message);
}

void loop() {
    while (!mqtt.connected()) {
        if (mqtt.connect(MQTT_ID, MQTT_USER, MQTT_PASS)) {
            mqtt.publish("void", MQTT_USER);

            // for (uint8_t i; i < RELAY_PINS; i++) {
            //     sprintf(msg_buff, SUB_RELAY_CMD "%u", i);
            //     mqtt.subscribe(msg_buff, 1);
            // }
            // mqtt.subscribe(SUB_RELAY_CMD "all", 1);
            // delay(100);
            // publish_relay_status();
        } else {
            delay(TIMEOUT);
        }
    }
    mqtt.loop();

    mqtt.publish("void", MQTT_USER);
    turn_pin_on(&pins[0], 1);
    delay(5000);
    mqtt.publish("void", MQTT_USER);
    turn_pin_off(&pins[0]);
    delay(5000);

    static uint32_t last = 0;
    if (millis() - last >= SCHEDULER_TICK_MS) {
        last = millis();

        // publish_temp();
        // check_heater();
        // check_relay_timers();
    }
}
