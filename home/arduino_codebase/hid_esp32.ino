#define _KI 1
#define USE_DEBUG 0  // disable debug in EPD files

#include <Arduino.h>
#include <BME280I2C.h>
#include <PubSubClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <Wire.h>
#include <inttypes.h>
#include <my_cfg.h>
#include <stdlib.h>

#include "DEV_Config.h"
#include "EPD.h"
#include "GUI_Paint.h"

#define SSID _wssid
#define PASS _wpass
#define PORT _port
#define BROKER _broker
#define MQTT_ID _mqtt_id
#define MQTT_USER _name
#define MQTT_PASS _pass
#define SUB_DATA "balcony/sensor/%u"

#define LED_GPIO 2

#define SCHEDULER_TICK_MS 5000
#define EPD_UPDATE_TICK_MS 20000

WiFiClientSecure client;
PubSubClient mqtt(BROKER, PORT, client);

BME280I2C bme;
BME280::TempUnit tempUnit(BME280::TempUnit_Celsius);
BME280::PresUnit presUnit(BME280::PresUnit_Pa);

#define SEND_RECV_BUFFER_SIZE 64
char buffer0[SEND_RECV_BUFFER_SIZE];

// Read payload, simple json data
#define MAX_KEYS 5
float payload_values[MAX_KEYS];
char* keys[MAX_KEYS];
char separator[] = "[]),";
char* token;

char balcony0_temp[] = "-99.6";
char balcony0_humid[] = "999.6";
char balcony1_temp[] = "-99.6";

char temp[] = "-99.6";
char humid[] = "999.6";
char air_pressure[] = "5555.7";

// Pre-allocate real values for publish and strings for lcd printing.
float temp_f = -99.66;
float humid_f = 555.66;
float air_pressure_f = 5555.66;

uint8_t* canvas = (uint8_t[(EPD_4IN2_V2_WIDTH / 4) * EPD_4IN2_V2_HEIGHT]){0};

void read_bme() {
    bme.read(air_pressure_f, temp_f, humid_f, tempUnit, presUnit);
    air_pressure_f /= 100.0;
    dtostrf(air_pressure_f, 4, 1, air_pressure);
    dtostrf(temp_f, 3, 1, temp);
    dtostrf(humid_f, 3, 1, humid);
}

void mqtt_publish_data() {
    if ((temp_f < -50 || temp_f > 60) ||
        (humid_f < 0 || humid_f > 105) ||
        (air_pressure_f < 300 || air_pressure_f > 1300)) return;

    const char* const fmt = "{\"temperature\":%.2f,\"humidity\":%.2f,\"airpressure\":%.2f}";
    unsigned int len = (unsigned int)sprintf(buffer0, fmt, temp_f, humid_f, air_pressure_f);
    mqtt.publish(_name "/sensor/0", (const uint8_t*)buffer0, len, false);
}

// For setting up values that will not change, only during setup()
const uint16_t margin = 16;
const uint16_t degree_symbol = 170;  // Paint before C to get "celcius" symbol.
void print_static_epd() {
    Paint_DrawString_EN(margin, margin + 24 * 0, "Inne:", &Font24, WHITE, BLACK);
    Paint_DrawString_EN(margin, margin + 24 * 3, "Ute:", &Font24, WHITE, BLACK);
    Paint_DrawString_EN(margin, margin + 24 * 6, "Balkong:", &Font24, WHITE, BLACK);
    Paint_DrawString_EN(margin, margin + 24 * 9, "Lufttryck:", &Font24, WHITE, BLACK);
}

void update_epd() {
    Paint_DrawRectangle(margin, margin + 24 * 1, EPD_4IN2_V2_WIDTH, margin + 24 * 1 + 20, WHITE, DOT_PIXEL_1X1, DRAW_FILL_FULL);
    sprintf(buffer0, "    %5sC | %5s%%", temp, humid);
    Paint_DrawCircle(degree_symbol, margin + 24 * 1 + 3, 3, BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);
    Paint_DrawCircle(degree_symbol, margin + 24 * 1 + 3, 1, WHITE, DOT_PIXEL_1X1, DRAW_FILL_FULL);
    Paint_DrawString_EN(margin, margin + 24 * 1, buffer0, &Font24, WHITE, BLACK);

    Paint_DrawRectangle(margin, margin + 24 * 4, EPD_4IN2_V2_WIDTH, margin + 24 * 4 + 20, WHITE, DOT_PIXEL_1X1, DRAW_FILL_FULL);
    sprintf(buffer0, "    %5sC", balcony1_temp);
    Paint_DrawCircle(degree_symbol, margin + 24 * 4 + 3, 3, BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);
    Paint_DrawCircle(degree_symbol, margin + 24 * 4 + 3, 1, WHITE, DOT_PIXEL_1X1, DRAW_FILL_FULL);
    Paint_DrawString_EN(margin, margin + 24 * 4, buffer0, &Font24, WHITE, BLACK);

    Paint_DrawRectangle(margin, margin + 24 * 7, EPD_4IN2_V2_WIDTH, margin + 24 * 7 + 20, WHITE, DOT_PIXEL_1X1, DRAW_FILL_FULL);
    sprintf(buffer0, "    %5sC | %5s%%", balcony0_temp, balcony0_humid);
    Paint_DrawCircle(degree_symbol, margin + 24 * 7 + 3, 3, BLACK, DOT_PIXEL_1X1, DRAW_FILL_FULL);
    Paint_DrawCircle(degree_symbol, margin + 24 * 7 + 3, 1, WHITE, DOT_PIXEL_1X1, DRAW_FILL_FULL);
    Paint_DrawString_EN(margin, margin + 24 * 7, buffer0, &Font24, WHITE, BLACK);

    Paint_DrawRectangle(margin, margin + 24 * 10, EPD_4IN2_V2_WIDTH, margin + 24 * 10 + 20, WHITE, DOT_PIXEL_1X1, DRAW_FILL_FULL);
    sprintf(buffer0, "    %6shPa", air_pressure);
    Paint_DrawString_EN(margin, margin + 24 * 10, buffer0, &Font24, WHITE, BLACK);

    EPD_4IN2_V2_Display(canvas);
}

uint8_t read_simple_json(char* payload, float* payload_vals) {
    uint8_t i = 0;
    char* contents = strtok(payload, "{\"");
    while (contents != NULL) {
        keys[i] = contents;
        contents = strtok(NULL, "\":,}");
        if (contents == NULL) {
            return 0;
        }
        sscanf(contents, "%f", &payload_vals[i]);
        contents = strtok(NULL, "\":,}");
        i += 1;
    }
    return i;
}

void on_message(char* topic, uint8_t* payload, unsigned int payload_len) {
    if (payload_len < 10 || payload_len >= SEND_RECV_BUFFER_SIZE) return;

    char buf[SEND_RECV_BUFFER_SIZE];
    memcpy(buf, (char*)payload, payload_len);
    buf[payload_len] = '\0';
    char last_char = topic[strlen(topic) - 1];

    uint8_t n_keys = read_simple_json(buf, payload_values);
    if (last_char == '0' && n_keys == 2) {
        dtostrf(payload_values[0], 5, 1, balcony0_temp);
        dtostrf(payload_values[1], 5, 1, balcony0_humid);
        return;
    }
    if (last_char == '1' && n_keys == 1) {
        dtostrf(payload_values[0], 5, 1, balcony1_temp);
        return;
    }
}

void setup() {
    pinMode(LED_GPIO, OUTPUT);
    digitalWrite(LED_GPIO, HIGH);

    Wire.begin();
    bme.begin();

    WiFi.mode(WIFI_STA);
    WiFi.begin(SSID, PASS);
    while (WiFi.status() != WL_CONNECTED) delay(250);

    client.setCACert(ca_cert);
    client.setCertificate(client_cert);
    client.setPrivateKey(client_key);

    mqtt.setCallback(on_message);

    DEV_Module_Init();
    EPD_4IN2_V2_Init();
    EPD_4IN2_V2_Clear();

    Paint_NewImage(canvas, EPD_4IN2_V2_WIDTH, EPD_4IN2_V2_HEIGHT, 0, WHITE);
    Paint_SetScale(2);
    Paint_Clear(WHITE);

    print_static_epd();
    EPD_4IN2_Sleep();
}

void loop() {
    if (!mqtt.loop()) {
        if (mqtt.connect(MQTT_ID, MQTT_USER, MQTT_PASS)) {
            digitalWrite(LED_GPIO, LOW);
            mqtt.publish("void", MQTT_USER);

            for (uint8_t i = 0; i < 2; i++) {
                sprintf(buffer0, SUB_DATA, i);
                mqtt.subscribe(buffer0, 1);
            }
        } else {
            digitalWrite(LED_GPIO, HIGH);
        }
    }

    static uint32_t epd_timer = 0, scheduler_timer = 0;
    uint32_t now = millis();
    if (now - scheduler_timer >= SCHEDULER_TICK_MS) {
        scheduler_timer = now;
        read_bme();
        mqtt_publish_data();
    }
    if (now - epd_timer >= EPD_UPDATE_TICK_MS) {
        epd_timer = now;
        EPD_4IN2_V2_Init();
        update_epd();
        EPD_4IN2_Sleep();
    }
}