#pragma once

#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iomanip>
#include <sstream>
#include <string>

using uint8_t = std::uint8_t;

class String {
 public:
  String() = default;
  String(const char* value) : value_(value) {}
  String(int value) : value_(std::to_string(value)) {}
  String(unsigned long value) : value_(std::to_string(value)) {}
  String(double value, int decimals) {
    std::ostringstream output;
    output << std::fixed << std::setprecision(decimals) << value;
    value_ = output.str();
  }

  String& operator+=(const char* value) {
    value_ += value;
    return *this;
  }

  String& operator+=(const String& value) {
    value_ += value.value_;
    return *this;
  }

  const char* c_str() const { return value_.c_str(); }

 private:
  std::string value_;
};

class Stream {
 public:
  virtual ~Stream() = default;
  virtual int available() = 0;
  virtual int read() = 0;
};

unsigned long millis();
