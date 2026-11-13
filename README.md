# HB-RF-ETH Home Assistant Integration

Custom integration for the [HB-RF-ETH-ng](https://github.com/Xerolux/HB-RF-ETH-ng)
HomeMatic/HmIP Ethernet gateway. Adds the gateway as a device with
connectivity, load, firmware and update entities — including one-click update
entities for firmware **and** WebUI that trigger the device's own online
installation — plus device services for the operations MQTT cannot transport
(full backup/restore, log download).

Works standalone or alongside the firmware's native MQTT/HA auto-discovery
(see the [WIKI MQTT-API-Referenz](https://github.com/Xerolux/HB-RF-ETH-ng/blob/main/docs/WIKI.md)):
MQTT gives you the live control surface, this integration adds config flow,
reauth, diagnostics and the file-based services.

## Entities

| Platform | Entity | Source |
|---|---|---|
| binary_sensor | Ethernet | `ethernetConnected` |
| binary_sensor | CCU Relay | raw-uart session |
| sensor | CPU / Memory usage | `sysinfo.json` |
| sensor | Uptime | `sysinfo.json` |
| sensor | Firmware / Latest version | `sysinfo.json` + `/api/update/status` |
| update | Firmware (install + progress) | `/api/update/status` + `POST /api/update/install` |
| update | WebUI (install + progress) | `/api/update/status` + `POST /api/update/install` |

Firmware **2.4.0 or newer** is required (update status with
`runningFirmware`/`runningWebui` and the install endpoint).

## Services

| Service | Description |
|---|---|
| `hb_rf_eth.backup` | Downloads the full settings backup (incl. credentials/certificates) into `<config>/hb_rf_eth_backups/<serial>-<timestamp>.json` (mode 0600) |
| `hb_rf_eth.restore` | Restores a backup file from that folder (`filename` parameter) |
| `hb_rf_eth.download_log` | Saves the complete captured system log as a text file |
| `hb_rf_eth.restart` | Restarts the gateway |
| `hb_rf_eth.update_check` | Starts a manual update search (optional `channel: stable\|beta`) |

All services target the gateway via the usual device/entity selectors.
Backups contain secrets — treat the backup folder accordingly.

## Setup

Settings → Devices & Services → Add Integration → **HB-RF-ETH**

Enter host (or `hb-rf-eth-xxxxxx.local` via mDNS), username and password of
the device WebUI. A changed device password triggers a reauth prompt
automatically. The device page offers a diagnostics download for issue
reports (no credentials included).

## Installation (HACS)

1. HACS → ⋮ → **Custom repositories**
2. Repository: `Xerolux/hb-rf-eth-hass`, Category: **Integration**
3. Install **HB-RF-ETH**, restart Home Assistant

## Development

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python -m pytest -q tests   # 31 tests against HA 2026.10.4
.venv/bin/ruff check custom_components tests
```

## Status

**Beta.** Unit-tested against Home Assistant 2026.10.4 (pytest-homeassistant-
custom-component) and validated live on HA 2026.11.0 against gateway firmware
2.4.0 (config flow, entities, backup and update-check services). Feedback and
logs welcome in the issues.

## License

MIT — see [LICENSE](LICENSE). The gateway firmware itself is licensed
CC BY-NC-SA 4.0 (see the [firmware repository](https://github.com/Xerolux/HB-RF-ETH-ng)).
