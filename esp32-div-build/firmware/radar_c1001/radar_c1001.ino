/*
 * radar_c1001.ino — DFRobot C1001 (SEN0623, 60GHz mmWave) vitals reader
 * for ESP32 / ESP32-S3.
 *
 * WHAT IT DOES
 *   Reads human PRESENCE, HEART RATE, BREATHING RATE and SLEEP STATE
 *   (asleep / awake) from the C1001 radar over UART and prints them to the
 *   Serial monitor. This is the standalone driver you use to (a) verify the
 *   sensor works and (b) copy the read logic into the ESP32-DIV firmware as a
 *   new "Radar / Vitals" menu screen (see radar-integration.md).
 *
 * WHY C1001 (not C4001)
 *   C1001 (60GHz) has built-in sleep monitoring + heart rate + respiration.
 *   C4001 (24GHz) only reports presence / distance / motion — no vitals,
 *   no asleep-vs-awake. If you have a C4001, use the DFRobot_C4001 library
 *   instead and expect presence data only.
 *
 * LIBRARY
 *   Install "DFRobot_HumanDetection" (Arduino Library Manager or
 *   https://github.com/DFRobot/DFRobot_HumanDetection ). The API names below
 *   follow that library's own examples — verify against the version you
 *   install if a call does not resolve.
 *
 * WIRING (pick spare pins on your board; UART2 shown)
 *   C1001 TX -> ESP RX (GPIO 18 here)      C1001 5V -> 5V
 *   C1001 RX -> ESP TX (GPIO 17 here)      C1001 GND -> GND
 *   NOTE: on the ESP32-DIV V2 the GPS already uses UART2 (47/48). Give the
 *   radar its own free pins/UART and update RADAR_RX/RADAR_TX accordingly.
 *
 * RESPONSIBLE USE
 *   Vitals/sleep sensing should only be used on people who have consented.
 */

#include "DFRobot_HumanDetection.h"

#define RADAR_RX 18   // ESP RX  <- C1001 TX
#define RADAR_TX 17   // ESP TX  -> C1001 RX

DFRobot_HumanDetection hu(&Serial1);

void setup() {
  Serial.begin(115200);
  Serial1.begin(115200, SERIAL_8N1, RADAR_RX, RADAR_TX);

  Serial.println("C1001: starting...");
  while (hu.begin() != 0) {
    Serial.println("C1001 init failed - check wiring/power");
    delay(1000);
  }

  // Sleep mode exposes presence + heart rate + breathing + sleep state.
  Serial.println("C1001: switching to sleep/vitals mode...");
  while (hu.configWorkMode(hu.eSleepMode) != 0) {
    Serial.println("C1001 mode set failed, retrying...");
    delay(1000);
  }
  Serial.print("C1001 work mode = ");
  Serial.println(hu.getWorkMode());
  Serial.println("C1001 ready.\n");
}

void loop() {
  // Presence: 0 = no one, 1 = person present (incl. still / sleeping)
  int present   = hu.smHumanData(hu.eHumanPresence);
  int movement  = hu.smHumanData(hu.eHumanMovement);   // 0 none,1 still,2 active
  int heart     = hu.getHeartRate();                   // bpm
  int breathe   = hu.getBreatheValue();                // breaths/min
  int sleepState= hu.smSleepData(hu.eSleepState);      // see mapping below

  Serial.println("---------------------------------");
  Serial.print("Presence : "); Serial.println(present ? "YES" : "no");
  Serial.print("Movement : "); Serial.println(movement); // 0/1/2
  Serial.print("Heart    : "); Serial.print(heart);   Serial.println(" bpm");
  Serial.print("Breathe  : "); Serial.print(breathe); Serial.println(" rpm");

  // Sleep state mapping (per DFRobot library): 0 = deep sleep, 1 = light
  // sleep, 2 = awake, 3 = none. We fold it into a simple asleep/awake flag.
  const char* label =
      (sleepState == 2) ? "AWAKE" :
      (sleepState == 0 || sleepState == 1) ? "ASLEEP" : "unknown";
  Serial.print("Sleep    : "); Serial.print(sleepState);
  Serial.print("  -> ");       Serial.println(label);

  delay(1000);
}
