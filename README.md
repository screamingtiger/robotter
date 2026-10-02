# robotter

Python command handling for a two-track tank driven by two bidirectional ESCs on Arduino UNO Q.

## Architecture and safety

The Linux MPU only sends high-level intent over Arduino Router Bridge. The STM32U585 real-time MCU owns the two PWM signals, ESC arming, timed pivots, and a 250 ms command watchdog. If Linux, the Python process, or its heartbeat stops, the RT firmware drives both channels to neutral and disarms.

`firmware/tank_rt/tank_rt.ino` intentionally has no default PWM pins. It will compile, but `ARM` is rejected until both `LEFT_ESC_PIN` and `RIGHT_ESC_PIN` are explicitly provided at compile time. The code is not flashed as part of this project setup.

`STOP`, a failed command timeout, and Ctrl+C always request neutral PWM. A 90-degree turn is timing-based and must be calibrated on the finished chassis; it cannot be exact without feedback such as encoders or an IMU.

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
STOP
```

`FWD`, `REV`, `LEFT`, and `RIGHT` take a speed from `0` through `1`. `L90` and `R90` delegate a timed full-speed pivot to the RT MCU.

## RT runtime setup

On Ardy, install the missing virtual-environment support once (interactive sudo required), then install the project’s RT dependency in the project environment:

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

Before any upload, specify verified 3.3 V PWM-capable Arduino pin numbers, confirm left/right direction, calibrate `1000/1500/2000` microseconds against the ESC documentation, test with tracks lifted, and retain a physical emergency stop.
