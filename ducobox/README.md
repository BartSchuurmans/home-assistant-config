# DucoBox Silent 4215 RF gateway

Local control of the DucoBox from Home Assistant: a Wemos D1 Mini with a
CC1101 868 MHz radio runs ESPEasy with
[arnemauer's Ducobox plugin](https://github.com/arnemauer/Ducobox-ESPEasy-Plugin)
(P150 "DUCO Ventilation remote"). The gateway joins the DucoBox as a wireless
CO2 sensor, reports the current ventilation mode and accepts mode commands,
all over MQTT. The Home Assistant side is in
[`packages/ducobox.yaml`](../packages/ducobox.yaml).

## 1. Wire the CC1101 to the D1 Mini

Make sure the radio is the **868 MHz** version (433 MHz modules look the same
and won't work). Power it from 3V3, never 5V.

| CC1101 pin | D1 Mini pin | GPIO   |
|------------|-------------|--------|
| VCC        | 3V3         |        |
| GND        | G           |        |
| MOSI       | D7          | GPIO13 |
| SCK        | D5          | GPIO14 |
| MISO/GDO1  | D6          | GPIO12 |
| GDO2       | D1          | GPIO5  |
| GDO0       | not used    |        |
| CSN        | D8          | GPIO15 |

GDO2 is the "packet received" interrupt; the plugin expects it on GPIO5 (D1).

Power the D1 Mini from a decent USB supply (2 A) with a short cable. Cheap
D1 Mini clones with a 150 mA regulator are known to reboot or corrupt flash
under RF load.

Keep the gateway **at least 60 cm (ideally 1 m) away from the DucoBox**.
Closer than that the two radios drown each other out and joining or mode
changes fail.

## 2. Flash ESPEasy with the Ducobox plugin

Use the prebuilt image from the plugin repo, it already has the plugin and
the right pin defaults (GPIO5 free of I2C):
[`20230518 Firmware ad1864a (ESPEasy mega-20230515).bin`](https://github.com/arnemauer/Ducobox-ESPEasy-Plugin/tree/master/Binaries/Binary%20based%20on%20ESPEasy-mega-20230515).

```sh
pip install esptool
esptool.py --chip esp8266 --port /dev/ttyUSB0 erase_flash
esptool.py --chip esp8266 --port /dev/ttyUSB0 write_flash 0x0 "20230518 Firmware ad1864a 18-05-2023 (ESPEasy mega-20230515).bin"
```

(On macOS the port is something like `/dev/cu.usbserial-*`. The "Flasher" zip
next to the .bin has a Windows GUI flasher if that's easier.)

After a reboot the D1 opens an access point `VENTILATION_GATEWAY_0`
(password `configesp`). Connect to it, open `http://192.168.4.1` if the portal
doesn't pop up, and join your Wi-Fi. Give it a DHCP reservation in the router.

Later updates go over the air: **Tools → Update Firmware**.

## 3. Configure ESPEasy

**Config tab**
- Unit Name: `ducobox` (this becomes `%sysname%` in the MQTT topics)
- Append Unit Number to hostname: off

**Hardware tab**: leave I2C SDA/SCL unset, GPIO5 must stay free.

**Controllers tab** → Add → *Home Assistant (openHAB) MQTT*
- Controller IP / Port: the Mosquitto broker, `1883`
- Use Extended Credentials: on, with an MQTT user for the gateway
- Controller Subscribe: `%sysname%/#`
- Controller Publish: `%sysname%/%tskname%/%valname%`
- Controller LWT Topic: `%sysname%/LWT`
- LWT Connect Message: `Connected`
- LWT Disconnect Message: `Connection Lost`
- Send LWT to broker: on
- MQTT Retain Msg: on (so HA gets the mode after a restart)
- Enabled: on

All HA entities use `ducobox/LWT` for availability, so they show as
unavailable until the LWT settings above are in place.

**Devices tab** → Edit an empty task → *DUCO Ventilation remote*
- Name: `duco`
- Enabled: on
- GPIO ← Interrupt pin (CC1101): GPIO-5 (D1)
- GPIO → Status LED: none (or a spare pin if you add an LED)
- Network ID / Device Address: **leave empty**, they are filled in by the join
- Log serial messages to syslog: on for now, it helps during pairing
- Send to Controller: tick the MQTT controller
- Interval: `60`
- Value `Ventilationmode`: decimals `0`
- Submit

## 4. Pair with the DucoBox

1. Open **Tools → Log** in a second browser window to watch the join.
2. Put the DucoBox in installer mode: take off the white cover and press the
   **INST** button until the LED blinks green. (Alternatively long-press two
   diagonal buttons on an already paired Duco wall switch.)
3. On the **Devices** tab press the blue **Join** button once. Joining takes
   about 20 seconds.
4. Edit the `duco` task and check that Network ID and Device Address are now
   filled in.
5. **Don't press Join again if it fails.** Each join adds a node to the
   DucoBox, which then keeps polling for it. Check the log and the distance to
   the box first. If you do need to start over, send `DISJOIN` first.
6. Turn "Log serial messages to syslog" off again and Submit.
7. Leave installer mode on the DucoBox (press INST again, or wait for it to
   time out).

Test from the Devices tab with the AUTO / LOW / MID / HIGH buttons; the
Ventilationmode value should follow within a few seconds.

## 5. Home Assistant

The entities are defined in [`packages/ducobox.yaml`](../packages/ducobox.yaml).
Load packages from `configuration.yaml` if that isn't set up yet:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Restart HA. You get a **DucoBox** device with:

| Entity                                   | What it does                                        |
|------------------------------------------|-----------------------------------------------------|
| `select.ducobox_ventilation_mode`        | Current mode; pick one to change it                 |
| `button.ducobox_boost_15_min` / `30` / `45` | High for 15, 30 or 45 min, then back to auto     |
| `button.ducobox_auto`                    | Back to auto right away                             |
| `binary_sensor.ducobox_rf_gateway_connection` | Whether the gateway is connected to MQTT         |

Low / Middle / High in the select are the timed (15 min) modes, the same as
one press on a Duco wall switch. Use the "Permanent" options for a mode that
stays until you change it.

You can also send any gateway command by hand:

```sh
mosquitto_pub -t ducobox/cmd -m 'VENTMODE,HIGH,0,2'
```

## Troubleshooting

- Mode commands do nothing: check the distance to the DucoBox and that Network
  ID / Device Address are filled in.
- Gateway keeps rebooting: power supply, cable or a weak D1 Mini regulator.
- More detail: set **Tools → Advanced → Web Log Level** to Debug and watch
  **Tools → Log**. The plugin's
  [wiki](https://github.com/arnemauer/Ducobox-ESPEasy-Plugin/wiki) (Dutch) has
  screenshots of every step.
