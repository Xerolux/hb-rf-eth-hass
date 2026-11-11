# HB-RF-ETH Home Assistant Integration

Custom integration for the [HB-RF-ETH-ng](https://github.com/Xerolux/HB-RF-ETH-ng)
HomeMatic/HmIP Ethernet gateway. Adds the gateway as a device with
connectivity, load and firmware entities — including a one-click update
entity that triggers the device's own online installation.

## Entities

| Platform | Entity | Source |
|---|---|---|
| binary_sensor | Ethernet | `ethernetConnected` |
| binary_sensor | CCU Relay | raw-uart session |
| sensor | CPU / Memory usage | `sysinfo.json` |
| sensor | Uptime | `sysinfo.json` |
| sensor | Firmware / Latest version | `sysinfo.json` + `/api/update/status` |
| update | Firmware | install via `POST /api/update/install` |

Firmware **2.4.0 or newer** is recommended (adds `/api/health` and richer
update status); older firmware works for the sensor set.

## Installation (HACS)

1. HACS → ⋮ → **Custom repositories**
2. Repository: `Xerolux/hb-rf-eth-hass`, Category: **Integration**
3. Install **HB-RF-ETH**, restart Home Assistant

## Setup

Settings → Devices & Services → Add Integration → **HB-RF-ETH**

Enter host (or `hb-rf-eth-xxxxxx.local` via mDNS), username and password of
the device WebUI.

## Status

**Beta.** Built against the documented REST contract and standard HA
integration patterns; not yet validated against a live Home Assistant
instance. Feedback and logs welcome in the issues.

## License

CC BY-NC-SA 4.0, following the firmware project.
