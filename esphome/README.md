# ESPHome devices

| File | Device | Board |
| --- | --- | --- |
| [projector.yaml](projector.yaml) | Sony VPL-HW10 projector, RS-232 | ESP32-C3 RS232 Adapter |
| [ducobox.yaml](ducobox.yaml) | DucoBox Silent 4215 ventilation, 868 MHz RF | Wemos D1 Mini + CC1101 |
| [projector-screen.yaml](projector-screen.yaml) | Top-Vision projector screen, 433 MHz | Olimex ESP32-DevKit-LiPo + CC1101 |

## Secrets

The configs read passwords and keys from a separate `secrets.yaml`, so they
never end up in git. `secrets.yaml.example` lists the keys it needs. Wi-Fi
is shared; every other secret is prefixed with the device name
and two underscores (`projector__…`), the format the ESPHome app uses
for scoped secrets, so devices never share keys or passwords.

**ESPHome add-on in Home Assistant:** click **Secrets** (top right of the
ESPHome dashboard), add the lines from `secrets.yaml.example` with your own
values, and save. For each `<device>__api_key`, copy a fresh key from the
[ESPHome API docs](https://esphome.io/components/api/) (the page shows a
randomly generated one). Then create a new device with the config's name
(e.g. `projector`), open **Edit**, replace its contents with the YAML file
(e.g. `projector.yaml`), and save.

**ESPHome CLI:** copy `secrets.yaml.example` to `secrets.yaml` (git-ignored)
next to the config and fill it in.

## Projector (Sony VPL-HW10)

The adapter is wired like a PC serial port (DB9 pin 3 TX, pin 2 RX) and so is
the projector, so Sony requires a cross cable between them. Put a DB9
**null-modem adapter** (female on one side, male on the other) between the
adapter and the projector's female RS-232 port. Power the adapter over USB-C.
UART is TX `GPIO10`, RX `GPIO4`, 38400 baud 8E1.

Entities:

- **Power** switch: sends the Sony power on/off commands. It reads on while
  the projector is starting or running and off in standby or cooling.
- **Power status** text sensor: `Standby`, `Starting`, `On`, `Cooling` (or
  `Unknown` until the projector answers). Use this for screen automations;
  the states are capitalized, so match them exactly.
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
3. No answer at all (only `>>>` lines): check the null-modem adapter is in
   place. Swapping `tx_pin` and `rx_pin` does not help on this board, because
   the line driver fixes which DB9 pins send and receive. Also check the
   projector's menu: if there's a low-power standby mode, RS-232 may be off
   in standby, so set it to standard, or test with the projector switched on.
4. Toggle **Power** in HA and watch **Power status** go
   `Standby → Starting → On`, then `Cooling → Standby` after switching off.

The command bytes follow Sony's protocol for the VPL-VW/HW range of that era
and have not yet been confirmed on this projector. Check the logs for `NAK` or
`Unhandled frame` lines if something doesn't react.

## DucoBox Silent 4215 (RF)

[`ducobox.yaml`](ducobox.yaml) turns a Wemos D1 Mini with a CC1101 868 MHz
radio into a wireless Duco controller. It joins the DucoBox as a CO2 sensor,
shows the current ventilation mode in Home Assistant and changes it, all
locally over the ESPHome API. The Duco protocol comes from
[Henkeh/DucoBox-ESPHome](https://github.com/Henkeh/DucoBox-ESPHome), a port
of arnemauer's ESPEasy Ducobox plugin that was tested on a DucoBox Silent.

### Wiring

Make sure the radio is the **868 MHz** version (433 MHz modules look the same
and won't reach the box). Power it from 3V3, never 5V.

| CC1101 | D1 Mini | GPIO   |
|--------|---------|--------|
| VCC    | 3V3     |        |
| GND    | G       |        |
| SCK    | D5      | GPIO14 |
| MISO   | D6      | GPIO12 |
| MOSI   | D7      | GPIO13 |
| CSN    | D8      | GPIO15 |
| GDO0   | D1      | GPIO5  |
| GDO2   | not used |       |

This differs from the ESPEasy wiring guides you may find: ESPHome reads
packets on **GDO0**, not GDO2. Upstream's ESP8266 example puts GDO0 on D4,
but D4 is a boot pin the radio drives while it powers up, so this config
uses D1.

Keep the gateway **at least 60 cm (ideally 1 m) from the DucoBox**. Closer
than that the two radios drown each other out and pairing or mode changes
fail. Use a decent USB supply and short cable; cheap D1 Mini clones with a
weak regulator tend to reboot under RF load.

### Flash

1. Add the `ducobox__` secrets from `secrets.yaml.example` (see Secrets
   above), create a device called `ducobox` in the add-on, open **Edit**,
   replace its contents with `ducobox.yaml` and save.
2. First flash over USB: **Install** → **Manual download** → **Factory
   format**, then flash that file from [web.esphome.io](https://web.esphome.io)
   in Chrome or Edge with the D1 Mini plugged in. With the CLI:
   `esphome run ducobox.yaml`.
3. Later updates go over Wi-Fi: **Install** → **Wirelessly**.
4. Home Assistant discovers the device; add it with the API key from `secrets.yaml`.

The first build downloads the Duco component from GitHub, pinned to a known
commit in the config.

### Pair with the DucoBox

1. Open the device logs in the ESPHome add-on to watch the join.
2. Put the DucoBox in installer mode: take off the white cover and press
   **INST** until the LED blinks green. (Or long-press two diagonal buttons
   on a paired Duco wall switch.)
3. In Home Assistant press **Pair** on the DucoBox device, once.
4. Check that **Network ID** and **Device address** (diagnostic) now have
   values. They are saved in flash, so pairing survives reboots and updates.
5. Press **Disable installer mode** to put the box back to normal.

Don't keep pressing Pair if it doesn't work: every join adds a node to the
DucoBox, which then keeps polling for it. Check the distance and logs first,
and press **Unpair** before trying again.

### Entities

| Entity | What it does |
|--------|--------------|
| **Ventilation** fan | Preset shows the current mode; pick one to change it. Off = away mode. |
| **Boost** button | High for 15 minutes, then the box goes back to auto |
| **Auto** button | Back to auto right away |
| Ventilation mode code (diagnostic) | Raw Duco mode: `AUTO`, `MAN1-3`, `CNT1-3`, `EMPT` |
| Network ID, Device address (diagnostic) | Set by pairing |
| Pair, Unpair, Enable/Disable installer mode, Restart (config) | Pairing and maintenance |

Low / Medium / High are the timed modes, like one press on a Duco wall
switch. The Permanent presets stay until you change them.

After a reboot the gateway requests auto, so both sides agree on the mode.
That also ends a boost that was running.

## Projector Screen (Top-Vision, 433 MHz)

An ESP32 with a CC1101 radio replays the screen remote's codes. The motor has
no limit switches; the wall controller stores the end limits and stops it
there, and the ESP32 only talks to that controller. Home Assistant gets a time
based cover (**closed** is down, **open** is up) that tracks where it expects
the screen to be.

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

1. Check the end limits first, with the original remote: press **down** once,
   don't touch anything, and see whether the screen stops by itself at the
   bottom. Do the same with **up**. Keep your hand on **stop** in case it
   doesn't. If it stops by itself both ways, `has_built_in_endstop: true` is
   right. If it overruns, the controller isn't enforcing limits: don't use the
   cover until they're reprogrammed with the remote.
2. Put the screen fully up with its own remote, then set the cover to open in
   HA if it isn't already.
3. Press close in HA: the screen should go down and HA should show it closed
   after `down_duration`. Then open, and stop halfway.
4. Out of range? Move the board closer to the screen or set `output_power` to
   the maximum of `11`.

### Automation

Import [blueprints/projector-screen.yaml](../blueprints/projector-screen.yaml)
and pick the projector's **Power status** sensor and the screen cover. The
screen goes down when the projector starts and up when it starts cooling.
