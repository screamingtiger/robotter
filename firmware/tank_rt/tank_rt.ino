/*
 * Arduino UNO Q RT tank controller.
 *
 * The Linux MPU requests high-level movement through Arduino Router Bridge.
 * This STM32U585 sketch owns PWM generation, ESC arming, and the watchdog.
 * It deliberately cannot attach a PWM pin until both pin macros are supplied.
 */

#include <Arduino_RouterBridge.h>
#include <Servo.h>

#ifndef LEFT_ESC_PIN
#define LEFT_ESC_PIN 255
#endif

#ifndef RIGHT_ESC_PIN
#define RIGHT_ESC_PIN 255
#endif

constexpr uint8_t UNCONFIGURED_PIN = 255;
constexpr int NEUTRAL_US = 1500;
constexpr int FORWARD_US = 2000;
constexpr int REVERSE_US = 1000;
constexpr unsigned long ESC_ARM_MS = 1000;
constexpr unsigned long COMMAND_TIMEOUT_MS = 250;
constexpr int MAX_TIMED_COMMAND_MS = 10000;

Servo leftEsc;
Servo rightEsc;
bool armed = false;
bool timedMotion = false;
unsigned long lastCommandMs = 0;
unsigned long timedDurationMs = 0;

bool pinsConfigured() {
  return LEFT_ESC_PIN != UNCONFIGURED_PIN && RIGHT_ESC_PIN != UNCONFIGURED_PIN &&
         LEFT_ESC_PIN != RIGHT_ESC_PIN;
}

int pulseFor(float speed) {
  if (speed >= 0.0f) {
    return NEUTRAL_US + static_cast<int>(speed * (FORWARD_US - NEUTRAL_US));
  }
  return NEUTRAL_US + static_cast<int>(speed * (NEUTRAL_US - REVERSE_US));
}

void writeTracks(float left, float right) {
  leftEsc.writeMicroseconds(pulseFor(left));
  rightEsc.writeMicroseconds(pulseFor(right));
}

void safeStop() {
  if (leftEsc.attached() && rightEsc.attached()) {
    leftEsc.writeMicroseconds(NEUTRAL_US);
    rightEsc.writeMicroseconds(NEUTRAL_US);
  }
  armed = false;
  timedMotion = false;
}

bool armTank() {
  if (!pinsConfigured()) {
    return false;
  }
  if (!leftEsc.attached()) {
    leftEsc.attach(LEFT_ESC_PIN, REVERSE_US, FORWARD_US);
  }
  if (!rightEsc.attached()) {
    rightEsc.attach(RIGHT_ESC_PIN, REVERSE_US, FORWARD_US);
  }
  writeTracks(0.0f, 0.0f);
  delay(ESC_ARM_MS);
  armed = true;
  timedMotion = false;
  lastCommandMs = millis();
  return true;
}

bool stopTank() {
  safeStop();
  return true;
}

bool setTracks(float left, float right) {
  if (!armed || left < -1.0f || left > 1.0f || right < -1.0f || right > 1.0f) {
    return false;
  }
  writeTracks(left, right);
  timedMotion = false;
  lastCommandMs = millis();
  return true;
}

bool pivotTimed(float left, float right, int durationMs) {
  if (!armed || left < -1.0f || left > 1.0f || right < -1.0f || right > 1.0f ||
      durationMs <= 0 || durationMs > MAX_TIMED_COMMAND_MS) {
    return false;
  }
  writeTracks(left, right);
  timedMotion = true;
  timedDurationMs = static_cast<unsigned long>(durationMs);
  lastCommandMs = millis();
  return true;
}

void setup() {
  if (!Bridge.begin()) {
    return;
  }
  Bridge.provide_safe("tank.arm", armTank);
  Bridge.provide_safe("tank.stop", stopTank);
  Bridge.provide_safe("tank.set_tracks", setTracks);
  Bridge.provide_safe("tank.pivot_timed", pivotTimed);
}

void loop() {
  if (!armed) {
    delay(1);
    return;
  }

  const unsigned long elapsed = millis() - lastCommandMs;
  if ((timedMotion && elapsed >= timedDurationMs) ||
      (!timedMotion && elapsed >= COMMAND_TIMEOUT_MS)) {
    safeStop();
  }
  delay(1);
}
