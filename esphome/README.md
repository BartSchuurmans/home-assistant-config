# ESPHome devices

| File | Device | Board |
| --- | --- | --- |
| [projector.yaml](projector.yaml) | Sony VPL-HW10 projector, RS-232 | ESP32-C3 RS232 Adapter |

## Secrets

Copy `secrets.yaml.example` to `secrets.yaml` (git-ignored) and fill it in.
If you use the ESPHome add-on in Home Assistant, put the same keys in its
`secrets.yaml` instead.

## Projector (Sony VPL-HW10)

The adapter plugs straight into the projector's RS-232 port (female DB9) and
is powered over USB-C. UART is TX `GPIO10`, RX `GPIO4`, 38400 baud 8E1.

Entities:

- **Power** switch: sends the Sony power on/off commands. It reads on while
  the projector is starting or running and off in standby or cooling.
- **Power status** text sensor: `standby`, `starting`, `on`, `cooling` (or
  `unknown` until the projector answers). Use this for screen automations.
- **Power status code** (diagnostic): the raw Sony status, 0 to 8.
- **Connected** (diagnostic): on when a valid frame arrived in the last 15 s.

### Flash

1. First flash over USB: connect the adapter to your computer with USB-C and run
   `esphome run projector.yaml` (or use the ESPHome add-on / web.esphome.io).
   If it isn't detected, hold BOOT while plugging it in.
2. Later updates go over the air: `esphome run projector.yaml --device projector.local`.
3. Home Assistant discovers the device; add it with the API key from `secrets.yaml`.

### Test

1. Plug the adapter into the projector, power it from a USB charger, and open the
   logs (`esphome logs projector.yaml`). The UART debug lines show every byte
   sent (`>>>`) and received (`<<<`).
2. Every 5 s the device sends the status query `A9 01 02 01 00 00 03 9A`. A
   working link answers with something like `A9 01 02 02 00 00 03 9A`
   (standby) and **Connected** turns on.
3. No answer at all: swap `tx_pin` and `rx_pin` in the substitutions, reflash.
   Also check the projector's menu: if there's a low-power standby mode,
   RS-232 may be off in standby, so set it to standard.
4. Toggle **Power** in HA and watch **Power status** go
   `standby → starting → on`, then `cooling → standby` after switching off.

The command bytes follow Sony's protocol for the VPL-VW/HW range of that era
and have not yet been confirmed on this projector. Check the logs for `NAK` or
`Unhandled frame` lines if something doesn't react.
