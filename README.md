# robotter

Python command handling for a two-track tank driven by two bidirectional ESCs on Arduino UNO Q.

## Architecture and safety

The Linux MPU only sends high-level intent over Arduino Router Bridge. The STM32U585 real-time MCU owns the two PWM signals, ESC arming, timed pivots, a 250 ms command watchdog, an optional camera-turret servo, and NMEA GPS ingestion. If Linux, the Python process, or its heartbeat stops, the RT firmware drives both channels to neutral and disarms.

`firmware/tank_rt/tank_rt.ino` intentionally has no default PWM pins. It will compile, but `ARM` is rejected until both `LEFT_ESC_PIN` and `RIGHT_ESC_PIN` are explicitly provided at compile time. The code is not flashed as part of this project setup.

`STOP`, a failed command timeout, and Ctrl+C always request neutral PWM. A 90-degree turn is timing-based and must be calibrated for the finished chassis; it cannot be exact without an IMU or wheel encoders.

## ESC signal wiring

Use the STM32U585 PWM outputs on the UNO-style digital header:

| Connection | Arduino UNO Q pin |
| --- | --- |
| Left ESC signal | `D9` |
| Right ESC signal | `D10` |
| Both ESC signal grounds | Any Arduino Q `GND` pin |

`D9` and `D10` are 3.3 V PWM-capable GPIO pins. Their PWM signal levels are **3.3 V**, not 5 V. Confirm that the ESC control input accepts a 3.3 V logic-high signal before connecting it. If the ESC requires 5 V logic, use a dedicated 3.3 V-to-5 V buffer/level shifter on each signal; never feed 5 V into an Arduino Q GPIO.

The ESCs may use their own motor-power rails, but their signal grounds must share a common ground with the Arduino Q. Do not connect an ESC BEC's positive (typically red) lead to the Arduino Q 3.3 V or 5 V rails when the ESC is separately powered; insulate that unused lead. Keep motor current off the Arduino Q power rails.

Before compiling for physical hardware, set `LEFT_ESC_PIN=9` and `RIGHT_ESC_PIN=10`, verify both ESC pulse calibration values, test with tracks lifted, and retain a physical emergency stop.

## Camera turret

The camera uses a normal positional servo driven by `D6`, with a calibrated 1,500 µs centre representing forward. The servo positive supply stays on its own rail, while servo ground and Arduino Q ground must be common. The MCU signal is 3.3 V; use a level shifter if the servo does not accept 3.3 V logic.

`TCENTER` commands the forward-facing centre. `TURRET <degrees>` commands a relative angle; the software initially limits it to -60 through +60 degrees until the physical end stops and direction have been calibrated. See [the turret wiring and calibration guide](docs/turret.md).

## GPS receiver wiring and logging

The reusable GPS receiver interface expects standard **NMEA 0183** sentences at 9,600 baud on the RT MCU hardware UART (`Serial1`):

| Connection | Arduino UNO Q pin |
| --- | --- |
| GPS TX (data from receiver) | `D0` / `Serial1 RX` |
| GPS RX (optional receiver configuration input) | `D1` / `Serial1 TX` |
| GPS ground | Arduino Q `GND` |
| GPS power | Per the receiver's voltage specification |

The Arduino Q UART pins are 3.3 V logic. Use a GPS receiver with a 3.3 V TX output, or level-shift the GPS TX signal before `D0`; do not apply a 5 V UART signal directly. Many GPS breakouts accept 5 V or 3.3 V supply power but still require checking their specific voltage and logic-level documentation.

The RT firmware validates NMEA checksums and parses the common `RMC` and `GGA` sentences into position, ground speed, course, satellite count, HDOP, altitude, and fix age. Linux retrieves this through `gps.snapshot`; it does not open the Router's reserved serial link directly.

After flashing GPS-capable firmware, start a CSV logger at the default 0.5 second interval:

```sh
cd ~/robotter
.venv/bin/python -m robotter.gps_logger --csv logs/gps.csv --interval 0.5
```

Each row records a host timestamp, GPS data, validity, and a `moving` estimate based on GPS ground speed and distance from the previous fix. GPS can verify whether the tank is moving and its course over ground, but cannot establish whether the chassis is moving *forward* rather than backward without a body-heading reference such as an IMU/compass or wheel encoders.

## AI benchmarks

The repository includes a GPU OpenCL FP32 matrix-multiply benchmark and an ONNX Runtime CPU latency harness. Install the optional benchmark dependency, then run the appropriate script:

```sh
cd ~/robotter
.venv/bin/pip install -e '.[benchmark]'
sh benchmarks/run_opencl_sgemm.sh
.venv/bin/python benchmarks/onnx_cpu_benchmark.py /path/to/model.onnx --threads 4
```

The OpenCL result is a GPU-compute proxy, not object-detection FPS. The ONNX harness reports actual local model-inference latency. Store downloaded models outside the repository.

## Simulator

The default CLI uses `MemoryPwm`; it never drives physical GPIO.

```sh
cd ~/robotter
PYTHONPATH=. python3 -m robotter.cli
```

Commands are processor-friendly mnemonics:

```text
ARM
FWD 0.50
LEFT 0.40
L90
TCENTER
TURRET -30
STOP
```

`FWD`, `REV`, `LEFT`, and `RIGHT` take a speed from `0` through `1`. `L90` and `R90` delegate a timed full-speed pivot to the RT MCU.

## RT runtime setup

On Ardy, install virtual-environment support once, then install the project's RT dependency:

```sh
sudo apt-get install python3.13-venv
cd ~/robotter
python3 -m venv .venv
.venv/bin/pip install -e '.[rt]'
```

After the RT firmware is explicitly configured with real PWM pins, compiled, and flashed, use:

```sh
cd ~/robotter
.venv/bin/python -m robotter.rt_cli
```

## Compile the RT firmware (no upload)

The following verifies the firmware only; it does not alter the MCU:

```sh
base=~/.arduino15/internal
arduino-cli compile --fqbn arduino:zephyr:unoq \
  --libraries "$base/Arduino_RouterBridge_0.4.3_456a4ab6b378b066" \
  --libraries "$base/Arduino_RPClite_0.3.1_3aaf611bc915560f" \
  --libraries "$base/MsgPack_0.4.2_a0d4adc5044d022c" \
  --libraries "$base/ArxContainer_0.7.0_007f0bb2a1cdefe3" \
  --libraries "$base/ArxTypeTraits_0.3.2_d65e2aabfeed7838" \
  --libraries "$base/DebugLog_0.8.4_c199e2cf6415ecc8" \
  ~/robotter/firmware/tank_rt
```

Before any upload, verify GPS and turret wiring/logic levels and the ESC pulse calibration, test with tracks lifted, and retain a physical emergency stop.
