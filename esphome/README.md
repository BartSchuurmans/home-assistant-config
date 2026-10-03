# ESPHome devices

| File | Device | Board |
| --- | --- | --- |
| [projector.yaml](projector.yaml) | Sony VPL-HW10 projector, RS-232 | ESP32-C3 RS232 Adapter |
| [projector-screen.yaml](projector-screen.yaml) | Top-Vision projector screen, 433 MHz | Olimex ESP32-DevKit-LiPo + CC1101 |

## Secrets

The configs read passwords and keys from a separate `secrets.yaml`, so they
never end up in git. `secrets.yaml.example` lists the keys it needs. Wi-Fi
is shared; every other secret is prefixed with the device name
and two underscores (`projector__…`), the format the ESPHome app uses
for scoped secrets, so devices never share keys or passwords.

**ESPHome add-on in Home Assistant:** click **Secrets** (top right of the
ESPHome dashboard), add the lines from `secrets.yaml.example` with your own
values, and save. For `projector__api_key`, copy a fresh key from the
[ESPHome API docs](https://esphome.io/components/api/) (the page shows a
randomly generated one). Then create a new device called `projector`, open
**Edit**, replace its contents with `projector.yaml`, and save.

**ESPHome CLI:** copy `secrets.yaml.example` to `secrets.yaml` (git-ignored)
next to the config and fill it in.

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

1. First flash over USB. In the add-on: **Install** → **Manual download** →
   **Factory format**, then flash that file from [web.esphome.io](https://web.esphome.io)
   in Chrome or Edge with the adapter plugged into your computer. With the CLI:
   `esphome run projector.yaml`. If it isn't detected, hold BOOT while plugging it in.
2. Later updates go over Wi-Fi: **Install** → **Wirelessly** in the add-on, or
   `esphome run projector.yaml --device projector.local`.
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

## Projector screen (Top-Vision, 433 MHz)

An ESP32 with a CC1101 radio replays the screen remote's codes. The screen's
own receiver and wall controller still stop it at the end limits; Home
Assistant gets a time based cover (**closed** is down, **open** is up) that
tracks where it expects the screen to be.

### Wiring

CC1101 module to Olimex ESP32-DevKit-LiPo. Use 3.3 V, never 5 V:

| CC1101 | ESP32 |
| --- | --- |
| VCC | 3.3V |
| GND | GND |
| SCK | GPIO18 |
| MOSI | GPIO23 |
| MISO (SO) | GPIO19 |
| CSN | GPIO25 |
| GDO0 | GPIO26 |
| GDO2 | GPIO27 |

Make sure the module is the 433 MHz version (antenna and marking say 433)
and has its antenna attached.

### Flash

1. In the add-on's **Secrets**, add `projector-screen__api_key` (a fresh key
   from the [ESPHome API docs](https://esphome.io/components/api/), different
   from the projector's) and `projector-screen__fallback_ap_password`. The
   Wi-Fi lines are shared with the projector.
2. Create a new device called `projector-screen`, open **Edit**, replace its
   contents with `projector-screen.yaml`, and save.
3. First flash over USB: **Install** → **Manual download** → **Factory
   format**, then flash that file from [web.esphome.io](https://web.esphome.io)
   in Chrome or Edge with the board plugged into your computer. Later updates
   go over Wi-Fi: **Install** → **Wirelessly**.
4. Home Assistant discovers the device; add it with the API key from Secrets.
   Until the codes are filled in, the cover moves in HA but sends nothing and
   logs `code not captured yet`.

With the CLI instead: `esphome run projector-screen.yaml` and
`esphome logs projector-screen.yaml`.

### Capture the remote

1. Power the board near the screen and click **Logs** on the device in the
   add-on (choose **Wirelessly**).
2. Press **down**, **up** and **stop** on the remote a few times each, one
   button at a time, with the remote near the board. Each press should log a
   line like `Received Dooya: id=0x123456, channel=1, button=3, check=3` or
   `Received RCSwitch Raw: protocol=1 data='0010...'`. Note which line belongs
   to which button and that it is the same on every press.
3. Click **Edit** and paste the values into the `send_down`, `send_up` and
   `send_stop` scripts (the comment above them has an example per protocol),
   then **Install** → **Wirelessly**.
4. Time how long the screen takes to go fully down and fully up, set
   `down_duration` and `up_duration` at the top, and install again.

If nothing is logged, add `raw` to the `dump` list and install: you'll see the
bare pulse timings instead, which can be replayed with `transmit_raw`. If the
log shows **KeeLoq**, the remote uses rolling codes and cannot be replayed
this way.

### Test

1. Put the screen fully up with its own remote, then set the cover to open in
   HA if it isn't already.
2. Press close in HA: the screen should go down and HA should show it closed
   after `down_duration`. Then open, and stop halfway.
3. Out of range? Move the board closer to the screen or set `output_power` to
   the maximum of `11`.

### Automation

Import [blueprints/projector-screen.yaml](../blueprints/projector-screen.yaml)
and pick the projector's **Power status** sensor and the screen cover. The
screen goes down when the projector starts and up when it starts cooling.
