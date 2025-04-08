#define _BR 1

#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <WiFiClientSecure.h>
#include <my_cfg.h>

#define SSID _wssid
#define PASS _wpass
#define PORT _port
#define BROKER _broker
#define MQTT_ID _mqtt_id
#define MQTT_USER _name
#define MQTT_PASS _pass

#define TIMEOUT 10000
#define UPDATE_TICK 5000
uint32_t last_tick;

// WIFI, MQTT
WiFiClientSecure wifi;
PubSubClient mqtt(wifi);

void _reconnect() {
    while (!mqtt.connected()) {
        getTime();
        if (mqtt.connect(MQTT_ID, MQTT_USER, MQTT_PASS)) {
            mqtt.publish("void", MQTT_USER);
        } else {
            delay(TIMEOUT);
        }
    }
}

void setup(void) {
    WiFi.mode(WIFI_STA);
    WiFi.begin(SSID, PASS);
    while (WiFi.status() != WL_CONNECTED)
        delay(250);

    // wifi.setTrustAnchors(&cert);
    wifi.setClientRSACert(&client_crt, &key);
    wifi.setFingerprint(mqtt_server_fingerprint);

    mqtt.setServer(BROKER, PORT);
}

uint8_t x = 0;
char b[10];
void loop(void) {
    _reconnect();
    if (millis() - last_tick >= UPDATE_TICK) {
        last_tick = millis();
        snprintf(b, 10, "%d", x);
        mqtt.publish("void", b);
        x++;
    }
}