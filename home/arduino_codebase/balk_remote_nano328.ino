#include <Arduino.h>
#include <HardwareSerial.h>
#include <my_cfg.h>

// Buttons
#define NO_ACTIVITY 500  // After a button is pressed, do not read anything for this
#define BUTTON_TIMEOUT 750
#define PIN_ALL_OFF 10  // D10
#define PIN_OFFSET 4    // GPIO6 controls GPIO10 if given value is 4
#define PIN0 A0
#define PIN1 A1
#define PIN2 A2
#define PIN3 A3
#define PINS 5

struct Pin {
    uint8_t io;
    bool active;
} pins[PINS];

void check_buttons() {
    static uint32_t timeout[PINS] = {0};
    static uint32_t button_any_pressed_timeout = 0;

    uint32_t now = millis();
    if (now - button_any_pressed_timeout >= NO_ACTIVITY) {
        for (uint8_t i = 0; i < PINS; i++) {
            Pin* p = &pins[i];

            if (digitalRead(p->io) == LOW && now - timeout[i] >= BUTTON_TIMEOUT) {
                timeout[i] = now;
                button_any_pressed_timeout = now;

                uint8_t payload = dev2dev_balc_pack(i, 0);
                Serial.write(payload);
                break;
            }
        }
    }
}

void read_serial() {
    if (Serial.available()) {
        uint8_t payload = Serial.read();
        Tuple_u8 data = dev2dev_balc_unpack(payload);
        if (data.idx == PINS - 1) return;

        Pin* p = &pins[data.idx];
        data.payload == 1 ? turn_pin_on(p) : turn_pin_off(p);
        if (p->io == PIN3) {
            digitalWrite(LED_BUILTIN, p->active ? HIGH : LOW);
        }
    }
}

void turn_pin_off(Pin* p) {
    p->active = false;
    digitalWrite(p->io + PIN_OFFSET, LOW);
}

void turn_pin_on(Pin* p) {
    p->active = true;
    digitalWrite(p->io + PIN_OFFSET, HIGH);
}

void init_pins() {
    pinMode(LED_BUILTIN, OUTPUT);

    uint8_t const pin_ids[] = {PIN0, PIN1, PIN2, PIN3, PIN_ALL_OFF};
    for (uint8_t i = 0; i < PINS; i++) {
        struct Pin* p = &pins[i];
        p->io = pin_ids[i];
        p->active = false;
        pinMode(p->io, INPUT_PULLUP);
        if (p->io != PIN_ALL_OFF) {
            pinMode(p->io + PIN_OFFSET, OUTPUT);
        }
    }
}

void setup() {
    Serial.begin(115200);
    init_pins();
}

void loop() {
    check_buttons();
    read_serial();
}
