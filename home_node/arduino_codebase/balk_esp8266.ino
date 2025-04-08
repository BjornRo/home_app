#define _BA 1

#include <Arduino.h>
#include <ArduinoJson.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <WiFiClientSecure.h>
#include <my_cfg.h>

#include "DHT.h"

// WEMOS D1 MINI, ORIENTATION ANTENNA UP

#define SSID _wssid
#define PASS _wpass
#define PORT _port
#define BROKER _broker
#define MQTT_USER _name
#define MQTT_PASS _pass
#define MQTT_ID _mqtt_id

#define PUB_RELAY_STATUS _name "/relay/status"
#define SUB_RELAY_CMD _name "/relay"

#define TIMEOUT 5000

// Buffers
#define BUFF_SIZE 128

// Safety variables
#define MAXTEMP_SAFETY 30
#define MAXTEMP_START 26
#define MAX_TIME 6 * 60

// Time variables
#define SCHEDULER_TICK_MS 5000
#define MINUTES_TO_MS_FACTOR 60000

// Relays with their state: active and timer. Does not correspond to indices in the code.
#define HIGH_LIGHT_BUTTON_PIN 5  // D1 Used async-polling on instead due to 'volatile'.
#define DHT22_PIN 4              // D2

// Actual Relays
#define RELAY_PINS 3
// 4th not used
#define HEATER_PIN 13      // D7
#define LOW_LIGHT_PIN 12   // D6
#define HIGH_LIGHT_PIN 14  // D5

#define BUTTON_TIMEOUT 750
#define BTN_DEBOUNCE_NUMBER 4

// Temperature sensor, 3.3v
DHT dht(DHT22_PIN, DHT22);
float temp, humid;

// WIFI, MQTT
WiFiClientSecure wifi;
PubSubClient mqtt(wifi);

StaticJsonDocument<BUFF_SIZE> json_buff;

char msg_buff_recv[BUFF_SIZE];
char msg_buff_tmp[BUFF_SIZE];
char msg_buff_send[BUFF_SIZE];

char* const command_list[] = {"relay_status", "set_relay"};

char* const pin_names[] = {"heater", "light_low", "light_high"};  // Heater has to be index 0!
uint8_t const pin_id[] = {HEATER_PIN, LOW_LIGHT_PIN, HIGH_LIGHT_PIN};

struct Pins {
    uint8_t id;
    char* name;
    uint32_t timer_start;
    uint32_t timer_length;
    bool active;
} pins[RELAY_PINS];

void init_pins() {
    for (uint8_t i = 0; i < RELAY_PINS; i++) {
        struct Pins* pin = &pins[i];
        pin->id = pin_id[i];
        pin->name = pin_names[i];
        pin->timer_start = 0;
        pin->timer_length = 0;
        pin->active = false;

        pinMode(pin->id, OUTPUT);
        digitalWrite(pin->id, LOW);
    }
    pinMode(HIGH_LIGHT_BUTTON_PIN, INPUT_PULLUP);
}

void publish_temp() {
    static char t[7], h[7];
    temp = dht.readTemperature();
    humid = dht.readHumidity();
    if (isnan(temp) || isnan(humid) || temp < -50 || temp > 90 || humid < 0 || humid > 105) {
        return;
    }
    dtostrf(temp, 3, 2, t);
    dtostrf(humid, 3, 2, h);
    snprintf(msg_buff_send, BUFF_SIZE, "{\"temperature\":%s,\"humidity\":%s}", t, h);
    mqtt.publish(PUBLISH_DATA, msg_buff_send);
}

void check_btn() {
    static uint8_t btn_counter = 0;
    static uint32_t btn_timeout = 0;
    static Pins* p = &pins[0];  // Lazy init
    if (p->id != HIGH_LIGHT_PIN) {
        for (uint8_t i = 0; i < RELAY_PINS; i++) {
            if (pins[i].id == HIGH_LIGHT_PIN) {
                p = &pins[i];
                break;
            }
        }
    }
    if ((digitalRead(HIGH_LIGHT_BUTTON_PIN) == 0) &&
        (millis() - btn_timeout > BUTTON_TIMEOUT) &&
        (btn_counter < BTN_DEBOUNCE_NUMBER)) {
        btn_counter++;
        if (btn_counter == BTN_DEBOUNCE_NUMBER) {
            if (p->active) {
                turn_off_pin_publish(p);
            } else {
                turn_on_pin(p, 10);
                publish_relay_status();
            }
            btn_timeout = millis();
        }
    } else {
        btn_counter = 0;
    }
}

void check_heater() {
    Pins* hp = &pins[0];
    if (hp->active && temp >= MAXTEMP_SAFETY) {
        turn_off_pin_publish(hp);
    }
}

void check_relay_timers() {
    bool publish = false;
    for (uint8_t i = 0; i < RELAY_PINS; i++) {
        Pins* p = &pins[i];
        if (p->active && (millis() - p->timer_start >= p->timer_length)) {
            turn_off_pin(p);
            publish = true;
        }
    }
    if (publish) {
        publish_relay_status();
    }
}

void turn_off_pin(Pins* pin) {
    digitalWrite(pin->id, LOW);
    pin->active = false;
}

void turn_off_pin_publish(Pins* pin) {
    turn_off_pin(pin);
    publish_relay_status();
}

void turn_on_pin(Pins* pin, uint16_t minutes) {
    if (minutes <= 0 || (pin->id == HEATER_PIN && temp > MAXTEMP_START)) {
        return;
    }
    pin->active = true;
    pin->timer_start = millis();
    pin->timer_length = minutes * MINUTES_TO_MS_FACTOR;
    digitalWrite(pin->id, HIGH);
}

void publish_relay_status() {
    uint8_t i, j, len, pos;
    pos = 0;
    for (i = 0; i < RELAY_PINS; i++) {  // Leave space for null
        const Pins& p = pins[i];        // poor persons json
        snprintf(msg_buff_tmp, BUFF_SIZE, ",\"%s\":%s", p.name, p.active ? "true" : "false");
        len = strlen(msg_buff_tmp);
        for (j = 0; j < len; j++) {
            msg_buff_send[pos++] = msg_buff_tmp[j];
        }
    }
    msg_buff_send[0] = '{';  // Replace ',' with {
    msg_buff_send[pos] = '}';
    msg_buff_send[pos + 1] = '\0';
    mqtt.publish(PUB_RELAY_STATUS, msg_buff_send, 1);
}

void command_handler() {
    const char* cmd = json_buff["cmd"];
    if (!(strcasecmp(cmd, command_list[0]))) {
        return publish_relay_status();
    }
    JsonVariant data = json_buff["data"];
    if (!strcasecmp(cmd, command_list[1])) {
        bool publish = false;
        if (data.is<const char*>()) {
            if (!strcasecmp(data, "all_off")) {
                publish = true;
                for (uint8_t i = 0; i < RELAY_PINS; i++) {
                    turn_off_pin(&pins[i]);
                }
            }
        } else if (data.is<JsonObject>()) {
            for (JsonPair kv : (JsonObject)data) {
                for (uint8_t i = 0; i < RELAY_PINS; i++) {
                    Pins* p = &pins[i];
                    if (!strcasecmp(kv.key().c_str(), p->name)) {
                        publish = true;
                        int16_t val = kv.value().as<int16_t>();
                        if (val == -1) {  // Toggle. Default times.
                            val = p->active ? 0 : (i == 0 ? 10 : 420);
                        }
                        if (val <= 0) {
                            turn_off_pin(p);
                        } else {
                            turn_on_pin(p, val);
                        }
                    }
                }
            }
        }
        if (publish) {
            publish_relay_status();
        }
    }
}

void on_message(char* topic, uint8_t* payload, unsigned int payload_length) {
    if (payload_length >= BUFF_SIZE) {
        return;
    }

    memcpy(msg_buff_recv, (char*)payload, payload_length);
    msg_buff_recv[payload_length] = '\0';

    DeserializationError error = deserializeJson(json_buff, msg_buff_recv);
    if (error) {
        return;
    }
    command_handler();
}

void reconnect() {
    while (!mqtt.connected()) {
        getTime();
        if (mqtt.connect(MQTT_ID, MQTT_USER, MQTT_PASS)) {
            mqtt.publish("void", MQTT_USER);
            mqtt.subscribe(SUB_RELAY_CMD, 1);
            delay(100);
            publish_relay_status();
        } else {
            delay(TIMEOUT);
        }
    }
}

void scheduler() {
    publish_temp();
    check_heater();
    check_relay_timers();
}

void setup() {
    dht.begin();
    init_pins();

    WiFi.mode(WIFI_STA);
    WiFi.begin(SSID, PASS);
    while (WiFi.status() != WL_CONNECTED)
        delay(250);

    wifi.setClientRSACert(&client_crt, &key);
    wifi.setFingerprint(mqtt_server_fingerprint);

    mqtt.setServer(BROKER, PORT);
    mqtt.setCallback(on_message);
}

void loop() {
    static uint32_t last = 0;
    reconnect();
    check_btn();
    mqtt.loop();
    // Tick-rate counter.
    if (millis() - last >= SCHEDULER_TICK_MS) {
        last = millis();
        scheduler();
    }
}
