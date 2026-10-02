#include <cassert>
#include <cmath>
#include <cstring>
#include <string>

#include "../nmea_gps.h"

namespace {

unsigned long fakeMillis = 0;

class FakeStream final : public Stream {
 public:
  explicit FakeStream(std::string data) : data_(std::move(data)) {}

  int available() override { return static_cast<int>(data_.size() - offset_); }
  int read() override { return data_[offset_++]; }

 private:
  std::string data_;
  std::size_t offset_ = 0;
};

struct Snapshot {
  bool valid;
  double latitude;
  double longitude;
  double speedKph;
  double courseDegrees;
  int satellites;
  double hdop;
  double altitudeMeters;
  unsigned long ageMs;
};

Snapshot decode(const String& value) {
  char buffer[160] = {};
  std::strncpy(buffer, value.c_str(), sizeof(buffer) - 1);
  char* fields[9] = {};
  int count = 0;
  fields[count++] = buffer;
  for (char* cursor = buffer; *cursor != '\0' && count < 9; ++cursor) {
    if (*cursor == '|') {
      *cursor = '\0';
      fields[count++] = cursor + 1;
    }
  }
  assert(count == 9);
  return {
      fields[0][0] == '1', atof(fields[1]), atof(fields[2]), atof(fields[3]), atof(fields[4]),
      atoi(fields[5]),      atof(fields[6]), atof(fields[7]), static_cast<unsigned long>(atol(fields[8])),
  };
}

void near(double actual, double expected, double tolerance = 0.0001) {
  assert(std::fabs(actual - expected) <= tolerance);
}

}  // namespace

unsigned long millis() { return fakeMillis; }

int main() {
  NmeaGps gps;

  // A corrupt checksum must not create a navigation fix.
  FakeStream corrupt("$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*00\r\n");
  gps.poll(corrupt);
  assert(!decode(gps.snapshot()).valid);

  // Standard checksum-valid RMC test sentence: position, speed, and course.
  FakeStream rmc("$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A\r\n");
  gps.poll(rmc);
  Snapshot fix = decode(gps.snapshot());
  assert(fix.valid);
  near(fix.latitude, 48.1173);
  near(fix.longitude, 11.5166667);
  near(fix.speedKph, 41.4848, 0.001);
  near(fix.courseDegrees, 84.4);

  // Standard checksum-valid GGA test sentence: fix quality metadata.
  FakeStream gga("$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\r\n");
  gps.poll(gga);
  fix = decode(gps.snapshot());
  assert(fix.valid);
  assert(fix.satellites == 8);
  near(fix.hdop, 0.9);
  near(fix.altitudeMeters, 545.4);

  // A last fix more than two seconds old is marked invalid for consumers.
  fakeMillis = 2501;
  assert(!decode(gps.snapshot()).valid);
  return 0;
}
