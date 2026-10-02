#!/bin/sh
set -eu

test_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
build_dir=$(mktemp -d)
trap 'rm -rf "$build_dir"' EXIT

g++ -std=c++17 -Wall -Wextra -Werror \
  -I"$test_dir/host" \
  "$test_dir/nmea_gps_test.cpp" \
  -o "$build_dir/nmea_gps_test"
"$build_dir/nmea_gps_test"
echo "NMEA parser tests: OK"
