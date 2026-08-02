/*
 * pn5180_reader.ino — PN5180 (13.56 MHz) reader/writer smoke-test for ESP32-S3
 *
 * PURPOSE
 *   Verify a PN5180 module and demonstrate the two things it does BETTER than
 *   the PN532:
 *     1. ISO15693 "vicinity" tags  -> long range (up to ~10-20 cm), read+write
 *     2. ISO14443 (Mifare/NTAG)    -> reads UID (shorter range, ~5-8 cm)
 *
 *   This is the first step of the PN5180 upgrade: get the hardware proven and
 *   the UID/read/write path working. The ESP32-DIV RFID menu flows can then be
 *   moved onto this backend (see ../radar-integration.md, section 2).
 *
 * HONEST LIMITATION
 *   The common PN5180 Arduino library focuses on ISO15693 + basic ISO14443
 *   UID. It does NOT implement MIFARE Classic sector authentication / block
 *   read-write the way Adafruit_PN532 does. So:
 *     - If your access cards are ISO15693 -> PN5180 is a big win (range + R/W).
 *     - If they are MIFARE Classic (ISO14443) -> PN5180 reads the UID (enough
 *       for UID-clone to a magic card) but full sector cloning still wants the
 *       PN532 path. Check your card type first with the current "Card Reader".
 *
 * LIBRARY
 *   Install "PN5180-Library" by ATrappmann
 *   (https://github.com/ATrappmann/PN5180-Library).
 *
 * WIRING (PN5180 needs SPI + NSS + BUSY + RST)
 *   PN5180 SCK  -> ESP SCK   (PN5180_SCK)
 *   PN5180 MISO -> ESP MISO
 *   PN5180 MOSI -> ESP MOSI
 *   PN5180 NSS  -> PN5180_NSS
 *   PN5180 BUSY -> PN5180_BUSY
 *   PN5180 RST  -> PN5180_RST
 *   PN5180 5V/3V3 + GND as per your module (many need 5V for the RF stage).
 */

#include <PN5180.h>
#include <PN5180ISO15693.h>
#include <PN5180ISO14443.h>

// --- pins: match your wiring (defaults reuse the ESP32-DIV V2 SPI trio) ---
#define PN5180_SCK   12
#define PN5180_MISO  11
#define PN5180_MOSI  13
#define PN5180_NSS    4
#define PN5180_BUSY   5   // extra vs PN532 — pick a free GPIO
#define PN5180_RST   14   // extra vs PN532 — pick a free GPIO

PN5180ISO15693 nfc15(PN5180_NSS, PN5180_BUSY, PN5180_RST);
PN5180ISO14443 nfc14(PN5180_NSS, PN5180_BUSY, PN5180_RST);

void setup() {
  Serial.begin(115200);
  SPI.begin(PN5180_SCK, PN5180_MISO, PN5180_MOSI, PN5180_NSS);

  nfc15.begin();
  nfc15.reset();
  uint8_t productVersion[2];
  nfc15.readEEprom(PRODUCT_VERSION, productVersion, sizeof(productVersion));
  Serial.print("PN5180 product version: ");
  Serial.print(productVersion[1]); Serial.print('.'); Serial.println(productVersion[0]);
  if (productVersion[1] == 0xFF) {
    Serial.println("PN5180 not responding - check wiring/power (needs 5V RF).");
  }
  Serial.println("Ready. Present a tag...\n");
}

void loop() {
  // ---- 1) Try ISO15693 (long-range vicinity) ----
  nfc15.reset();
  nfc15.setupRF();
  uint8_t uid15[8];
  ISO15693ErrorCode rc = nfc15.getInventory(uid15);
  if (rc == ISO15693_EC_OK) {
    Serial.print("[ISO15693] UID: ");
    for (int i = 7; i >= 0; i--) { if (uid15[i] < 16) Serial.print('0'); Serial.print(uid15[i], HEX); Serial.print(' '); }
    Serial.println();

    // Demo: read block 0, then write it back unchanged (safe round-trip).
    uint8_t blockSize = 4, blockData[4];
    if (nfc15.readSingleBlock(uid15, 0, blockData, blockSize) == ISO15693_EC_OK) {
      Serial.print("  block0: ");
      for (int i = 0; i < blockSize; i++) { Serial.print(blockData[i], HEX); Serial.print(' '); }
      Serial.println();
      // To PROGRAM a new tag, change blockData then:
      //   nfc15.writeSingleBlock(uid15, 0, blockData, blockSize);
      // (left commented so this demo never alters your tag)
    }
    delay(1200);
    return;
  }

  // ---- 2) Fall back to ISO14443 (Mifare/NTAG) — UID only ----
  nfc14.reset();
  nfc14.setupRF();
  uint8_t uid14[10];
  uint8_t len = nfc14.readCardSerial(uid14);
  if (len > 0) {
    Serial.print("[ISO14443] UID: ");
    for (int i = 0; i < len; i++) { if (uid14[i] < 16) Serial.print('0'); Serial.print(uid14[i], HEX); Serial.print(' '); }
    Serial.println("  (Mifare/NTAG — UID read OK; full Classic sectors need the PN532 path)");
    delay(1200);
    return;
  }

  delay(150);
}
