#pragma once

#include <Arduino.h>

// Small, dependency-free NMEA 0183 parser for the RMC and GGA sentences
// emitted by common UART GPS receivers.  It validates the NMEA checksum and
// keeps only the newest navigation fix.
class NmeaGps {
 public:
  void poll(Stream& serial) {
    while (serial.available()) {
      const char character = static_cast<char>(serial.read());
      if (character == '\r') {
        continue;
      }
      if (character == '\n') {
        sentence_[length_] = '\0';
        processSentence();
        length_ = 0;
        continue;
      }
      if (length_ < sizeof(sentence_) - 1) {
        sentence_[length_++] = character;
      } else {
        // Reject an overlong sentence instead of using partial coordinates.
        length_ = 0;
      }
    }
  }

  String snapshot() const {
    const unsigned long ageMs = millis() - lastFixMs_;
    const bool fresh = valid_ && ageMs <= 2000;
    String output = fresh ? "1" : "0";
    output += "|";
    output += String(latitude_, 7);
    output += "|";
    output += String(longitude_, 7);
    output += "|";
    output += String(speedKph_, 3);
    output += "|";
    output += String(courseDegrees_, 2);
    output += "|";
    output += String(satellites_);
    output += "|";
    output += String(hdop_, 2);
    output += "|";
    output += String(altitudeMeters_, 2);
    output += "|";
    output += String(ageMs);
    return output;
  }

 private:
  char sentence_[128] = {};
  size_t length_ = 0;
  bool valid_ = false;
  double latitude_ = 0.0;
  double longitude_ = 0.0;
  double speedKph_ = 0.0;
  double courseDegrees_ = 0.0;
  int satellites_ = 0;
  double hdop_ = 0.0;
  double altitudeMeters_ = 0.0;
  unsigned long lastFixMs_ = 0;

  static uint8_t hexValue(char character) {
    if (character >= '0' && character <= '9') return character - '0';
    if (character >= 'A' && character <= 'F') return character - 'A' + 10;
    if (character >= 'a' && character <= 'f') return character - 'a' + 10;
    return 0xFF;
  }

  static bool validChecksum(char* sentence) {
    if (sentence[0] != '$') return false;
    char* asterisk = strchr(sentence, '*');
    if (asterisk == nullptr || asterisk[1] == '\0' || asterisk[2] == '\0') return false;
    uint8_t checksum = 0;
    for (char* cursor = sentence + 1; cursor < asterisk; ++cursor) checksum ^= *cursor;
    const uint8_t high = hexValue(asterisk[1]);
    const uint8_t low = hexValue(asterisk[2]);
    if (high == 0xFF || low == 0xFF || checksum != static_cast<uint8_t>((high << 4) | low)) {
      return false;
    }
    *asterisk = '\0';
    return true;
  }

  static int split(char* text, char* fields[], int maximumFields) {
    int count = 0;
    fields[count++] = text;
    for (char* cursor = text; *cursor != '\0' && count < maximumFields; ++cursor) {
      if (*cursor == ',') {
        *cursor = '\0';
        fields[count++] = cursor + 1;
      }
    }
    return count;
  }

  static bool coordinate(const char* value, const char* hemisphere, double& destination) {
    if (value == nullptr || hemisphere == nullptr || value[0] == '\0' || hemisphere[0] == '\0') {
      return false;
    }
    const double raw = atof(value);
    const int degrees = static_cast<int>(raw / 100.0);
    const double decimal = degrees + (raw - degrees * 100.0) / 60.0;
    if ((hemisphere[0] != 'N' && hemisphere[0] != 'S' && hemisphere[0] != 'E' && hemisphere[0] != 'W') ||
        decimal < 0.0) {
      return false;
    }
    destination = (hemisphere[0] == 'S' || hemisphere[0] == 'W') ? -decimal : decimal;
    return true;
  }

  void processRmc(char* fields[], int count) {
    // $GxRMC,time,status,lat,N,lon,E,speed_knots,course,date,...
    if (count < 9) return;
    if (fields[2][0] != 'A') {
      valid_ = false;
      return;
    }
    double latitude;
    double longitude;
    if (!coordinate(fields[3], fields[4], latitude) || !coordinate(fields[5], fields[6], longitude)) {
      valid_ = false;
      return;
    }
    latitude_ = latitude;
    longitude_ = longitude;
    speedKph_ = atof(fields[7]) * 1.852;
    courseDegrees_ = atof(fields[8]);
    valid_ = true;
    lastFixMs_ = millis();
  }

  void processGga(char* fields[], int count) {
    // $GxGGA,time,lat,N,lon,E,quality,satellites,hdop,altitude,M,...
    if (count < 10 || atoi(fields[6]) <= 0) return;
    double latitude;
    double longitude;
    if (!coordinate(fields[2], fields[3], latitude) || !coordinate(fields[4], fields[5], longitude)) return;
    latitude_ = latitude;
    longitude_ = longitude;
    satellites_ = atoi(fields[7]);
    hdop_ = atof(fields[8]);
    altitudeMeters_ = atof(fields[9]);
    valid_ = true;
    lastFixMs_ = millis();
  }

  void processSentence() {
    if (length_ == 0 || !validChecksum(sentence_)) return;
    char* fields[16] = {};
    const int count = split(sentence_ + 1, fields, 16);
    if (count == 0 || strlen(fields[0]) < 3) return;
    const char* type = fields[0] + strlen(fields[0]) - 3;
    if (strcmp(type, "RMC") == 0) processRmc(fields, count);
    if (strcmp(type, "GGA") == 0) processGga(fields, count);
  }
};
