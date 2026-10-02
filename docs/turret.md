# Camera turret

The camera turret uses a normal positional PWM servo driven by the Arduino UNO Q RT MCU. Its calibrated centre is the tank's forward-facing direction.

## Pinout

| Servo lead | Connect to |
| --- | --- |
| Signal (usually yellow, white, or orange) | Arduino Q `D6` / PB1 / TIM3_CH4 |
| Ground (usually black or brown) | Arduino Q `GND` and the servo power-rail ground |
| Positive supply (usually red) | The separate servo power rail only |

`D6` is a 3.3 V PWM-capable GPIO. The servo signal input must accept a 3.3 V logic-high signal; otherwise use a 3.3 V-to-5 V buffer. Do not connect the separate servo rail's positive supply to the Arduino Q 3.3 V or 5 V pins. A common ground is required for the PWM signal to have a reference.

The pin is deliberately unconfigured in firmware. Build with `TURRET_SERVO_PIN=6` only after verifying wiring, power capacity, and the mechanical end stops. No turret PWM signal is generated before a `TCENTER` or `TURRET` command is accepted.

## Commands

```text
TCENTER       # 1,500 us: calibrated forward-facing camera direction
TURRET -30    # relative angle, degrees; allowed range is -60 through +60
TURRET 45
```

The default `1000 / 1500 / 2000` microsecond mapping and ±60° range are conservative starting values. Set the camera forward, issue `TCENTER`, then adjust the pulse and angle range only after testing slowly with the camera clear of its mechanical stops. Positive and negative physical direction must also be confirmed on the actual mount.
