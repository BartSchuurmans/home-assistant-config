# DucoBox Silent 4215 (RF)

[`ducobox.yaml`](ducobox.yaml) turns a Wemos D1 Mini with a CC1101 868 MHz
radio into a wireless Duco controller. It joins the DucoBox as a CO2 sensor,
shows the current ventilation mode in Home Assistant and changes it, all
locally over the ESPHome API. The Duco protocol comes from
[Henkeh/DucoBox-ESPHome](https://github.com/Henkeh/DucoBox-ESPHome), a port
of arnemauer's ESPEasy Ducobox plugin that was tested on a DucoBox Silent.

## Wiring

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

## Secrets

Add these to the ESPHome secrets (**Secrets** in the ESPHome add-on, or
`secrets.yaml` next to the config with the CLI). Wi-Fi is shared with the
other devices.

```yaml
wifi_ssid: "your-wifi"
wifi_password: "your-wifi-password"
ducobox__fallback_ap_password: "change-me-12345"
ducobox__ota_password: "some-long-password"
# Generate with: python3 -c "import secrets,base64;print(base64.b64encode(secrets.token_bytes(32)).decode())"
ducobox__api_key: "PASTE_GENERATED_KEY_HERE"
```

## Flash

1. In the ESPHome add-on, create a device called `ducobox`, open **Edit**,
   replace its contents with `ducobox.yaml` and save.
2. First flash over USB: **Install** → **Manual download** → **Factory
   format**, then flash that file from [web.esphome.io](https://web.esphome.io)
   in Chrome or Edge with the D1 Mini plugged in. With the CLI:
   `esphome run ducobox.yaml`.
3. Later updates go over Wi-Fi: **Install** → **Wirelessly**.
4. Home Assistant discovers the device; add it with `ducobox__api_key`.

The first build downloads the Duco component from GitHub, pinned to a known
commit in the config.

## Pair with the DucoBox

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

## Entities

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
