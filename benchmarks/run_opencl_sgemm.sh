#!/bin/sh
set -eu

benchmark_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
build_dir=$(mktemp -d)
trap 'rm -rf "$build_dir"' EXIT

g++ -O3 -std=c++17 -Wall -Wextra -Werror \
  "$benchmark_dir/opencl_sgemm.cpp" \
  -lOpenCL \
  -o "$build_dir/opencl_sgemm"
"$build_dir/opencl_sgemm"
