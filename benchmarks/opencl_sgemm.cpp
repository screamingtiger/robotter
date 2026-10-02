// Minimal FP32 OpenCL matrix-multiply benchmark for the Linux MPU GPU path.
// It is a compute proxy for dense/convolutional neural-network layers, not a
// claim of end-to-end model inference speed.

#define CL_TARGET_OPENCL_VERSION 120
#include <CL/cl.h>

#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr int kMatrixSize = 512;
constexpr int kRuns = 12;

const char* kKernel = R"CLC(
#define TILE 8
__kernel void sgemm(const int n,
                    __global const float* a,
                    __global const float* b,
                    __global float* c) {
  const int localColumn = get_local_id(0);
  const int localRow = get_local_id(1);
  const int column = get_global_id(0);
  const int row = get_global_id(1);
  __local float tileA[TILE][TILE];
  __local float tileB[TILE][TILE];
  float sum = 0.0f;

  for (int tile = 0; tile < n; tile += TILE) {
    const int aColumn = tile + localColumn;
    const int bRow = tile + localRow;
    tileA[localRow][localColumn] = (row < n && aColumn < n) ? a[row * n + aColumn] : 0.0f;
    tileB[localRow][localColumn] = (bRow < n && column < n) ? b[bRow * n + column] : 0.0f;
    barrier(CLK_LOCAL_MEM_FENCE);
    for (int index = 0; index < TILE; ++index) {
      sum += tileA[localRow][index] * tileB[index][localColumn];
    }
    barrier(CLK_LOCAL_MEM_FENCE);
  }
  if (row < n && column < n) c[row * n + column] = sum;
}
)CLC";

void check(cl_int result, const char* operation) {
  if (result != CL_SUCCESS) {
    throw std::runtime_error(std::string(operation) + " failed with OpenCL error " + std::to_string(result));
  }
}

cl_device_id findGpu() {
  cl_uint platformCount = 0;
  check(clGetPlatformIDs(0, nullptr, &platformCount), "clGetPlatformIDs(count)");
  std::vector<cl_platform_id> platforms(platformCount);
  check(clGetPlatformIDs(platformCount, platforms.data(), nullptr), "clGetPlatformIDs(list)");
  for (cl_platform_id platform : platforms) {
    cl_uint deviceCount = 0;
    cl_int result = clGetDeviceIDs(platform, CL_DEVICE_TYPE_GPU, 0, nullptr, &deviceCount);
    if (result != CL_SUCCESS || deviceCount == 0) continue;
    std::vector<cl_device_id> devices(deviceCount);
    check(clGetDeviceIDs(platform, CL_DEVICE_TYPE_GPU, deviceCount, devices.data(), nullptr), "clGetDeviceIDs");
    return devices.front();
  }
  throw std::runtime_error("no OpenCL GPU device found");
}

std::string deviceName(cl_device_id device) {
  size_t bytes = 0;
  check(clGetDeviceInfo(device, CL_DEVICE_NAME, 0, nullptr, &bytes), "clGetDeviceInfo(size)");
  std::vector<char> value(bytes);
  check(clGetDeviceInfo(device, CL_DEVICE_NAME, bytes, value.data(), nullptr), "clGetDeviceInfo(name)");
  return value.data();
}

}  // namespace

int main() {
  try {
    const cl_device_id device = findGpu();
    cl_int result = CL_SUCCESS;
    const cl_context context = clCreateContext(nullptr, 1, &device, nullptr, nullptr, &result);
    check(result, "clCreateContext");
    const cl_command_queue queue = clCreateCommandQueue(context, device, CL_QUEUE_PROFILING_ENABLE, &result);
    check(result, "clCreateCommandQueue");

    const size_t elementCount = static_cast<size_t>(kMatrixSize) * kMatrixSize;
    const size_t bytes = elementCount * sizeof(float);
    std::vector<float> inputA(elementCount, 1.0f);
    std::vector<float> inputB(elementCount, 1.0f);
    std::vector<float> output(elementCount, 0.0f);

    const cl_mem a = clCreateBuffer(context, CL_MEM_READ_ONLY | CL_MEM_COPY_HOST_PTR, bytes, inputA.data(), &result);
    check(result, "clCreateBuffer(A)");
    const cl_mem b = clCreateBuffer(context, CL_MEM_READ_ONLY | CL_MEM_COPY_HOST_PTR, bytes, inputB.data(), &result);
    check(result, "clCreateBuffer(B)");
    const cl_mem c = clCreateBuffer(context, CL_MEM_WRITE_ONLY, bytes, nullptr, &result);
    check(result, "clCreateBuffer(C)");

    const char* source = kKernel;
    const size_t sourceLength = std::char_traits<char>::length(source);
    const cl_program program = clCreateProgramWithSource(context, 1, &source, &sourceLength, &result);
    check(result, "clCreateProgramWithSource");
    result = clBuildProgram(program, 1, &device, "", nullptr, nullptr);
    if (result != CL_SUCCESS) {
      size_t logLength = 0;
      clGetProgramBuildInfo(program, device, CL_PROGRAM_BUILD_LOG, 0, nullptr, &logLength);
      std::vector<char> log(logLength);
      clGetProgramBuildInfo(program, device, CL_PROGRAM_BUILD_LOG, logLength, log.data(), nullptr);
      throw std::runtime_error(std::string("clBuildProgram failed: ") + log.data());
    }
    const cl_kernel kernel = clCreateKernel(program, "sgemm", &result);
    check(result, "clCreateKernel");

    check(clSetKernelArg(kernel, 0, sizeof(kMatrixSize), &kMatrixSize), "clSetKernelArg(n)");
    check(clSetKernelArg(kernel, 1, sizeof(a), &a), "clSetKernelArg(A)");
    check(clSetKernelArg(kernel, 2, sizeof(b), &b), "clSetKernelArg(B)");
    check(clSetKernelArg(kernel, 3, sizeof(c), &c), "clSetKernelArg(C)");
    const size_t global[] = {kMatrixSize, kMatrixSize};
    const size_t local[] = {8, 8};

    // Warm the driver and shader compiler before timing.
    check(clEnqueueNDRangeKernel(queue, kernel, 2, nullptr, global, local, 0, nullptr, nullptr), "warmup enqueue");
    check(clFinish(queue), "warmup finish");

    std::vector<double> milliseconds;
    for (int run = 0; run < kRuns; ++run) {
      cl_event event = nullptr;
      check(clEnqueueNDRangeKernel(queue, kernel, 2, nullptr, global, local, 0, nullptr, &event), "timed enqueue");
      check(clWaitForEvents(1, &event), "clWaitForEvents");
      cl_ulong started = 0;
      cl_ulong finished = 0;
      check(clGetEventProfilingInfo(event, CL_PROFILING_COMMAND_START, sizeof(started), &started, nullptr), "profile start");
      check(clGetEventProfilingInfo(event, CL_PROFILING_COMMAND_END, sizeof(finished), &finished, nullptr), "profile end");
      milliseconds.push_back(static_cast<double>(finished - started) / 1'000'000.0);
      clReleaseEvent(event);
    }
    check(clEnqueueReadBuffer(queue, c, CL_TRUE, 0, bytes, output.data(), 0, nullptr, nullptr), "clEnqueueReadBuffer");
    if (output.front() != static_cast<float>(kMatrixSize) || output.back() != static_cast<float>(kMatrixSize)) {
      throw std::runtime_error("result validation failed");
    }

    const double averageMs = std::accumulate(milliseconds.begin(), milliseconds.end(), 0.0) / milliseconds.size();
    const double operations = 2.0 * kMatrixSize * kMatrixSize * kMatrixSize;
    const double gflops = operations / (averageMs / 1000.0) / 1e9;
    std::cout << "device=" << deviceName(device) << '\n';
    std::cout << "matrix=" << kMatrixSize << "x" << kMatrixSize << " fp32 runs=" << kRuns << '\n';
    std::cout << std::fixed << std::setprecision(3);
    std::cout << "average_kernel_ms=" << averageMs << '\n';
    std::cout << "effective_gflops=" << gflops << '\n';

    clReleaseKernel(kernel);
    clReleaseProgram(program);
    clReleaseMemObject(c);
    clReleaseMemObject(b);
    clReleaseMemObject(a);
    clReleaseCommandQueue(queue);
    clReleaseContext(context);
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "benchmark error: " << error.what() << '\n';
    return 1;
  }
}
