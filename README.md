# HB-RF-ETH Home Assistant Integration

[English guide](docs/guide.md) · [Deutsche Anleitung](docs/guide.de.md)

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

Each service operates on one loaded gateway. Select a device or entity
when you have multiple gateways. With a single loaded gateway, the target
is optional.
Backups contain secrets — treat the backup folder accordingly.

## Setup

Settings → Devices & Services → Add Integration → **HB-RF-ETH**

Gateways with firmware **2.4.0 or newer** can be discovered via mDNS
(`_hb-rf-eth._tcp`). Confirm the discovery and enter the gateway's WebUI
credentials. For manual setup, use an IP address or hostname such as
`hb-rf-eth-xxxxxx.local`.

Use **Reconfigure** after an IP or hostname change. The integration keeps
the existing device and entity IDs. Leave the password field blank to
keep the saved password. If the gateway rejects the saved credentials,
Home Assistant prompts for reauthentication.

For remote gateways, see [Tailscale setup](docs/guide.md#connect-a-remote-gateway-over-tailscale).

### Options (Configure on the config entry)

| Option | Description |
|---|---|
| Services only | Registers **no entities** — for setups where the gateway already delivers its entities via the firmware's native MQTT/HA auto-discovery. The integration then only provides its services; duplicates are avoided, the device is not polled redundantly. |
| Poll interval | REST polling interval, 10–300 s (default 30 s, when REST entities are enabled). |

> **„I see no entities in this integration?"** — That is the intended
> behaviour of *Services only*: the config entry deliberately shows nothing
> but its services. Your gateway device with **all its entities** lives under
> **Settings → Devices & Services → MQTT → HB-RF-ETH-…** (search for the
> hostname). If you prefer the entities here instead, turn *Services only*
> off — but then they duplicate the MQTT ones.

### Coexistence with the native MQTT discovery

The firmware offers both paths; the recommended combination is:
**MQTT discovery for the live entity surface** (switches, numbers,
selects, events, update entities — token-gated) **plus this integration
in services-only mode** (backup/restore, log download, restart,
reauth, diagnostics). Device load stays modest: MQTT publishes its
status once per minute, the REST coordinator sends sysinfo and update-status GETs per
poll interval when REST entities are enabled.

## Installation

Requires Home Assistant **2026.10.0 or later** and gateway firmware **2.4.0 or later**.

The integration source lives in `custom_components/hb_rf_eth`.
The published `hb_rf_eth.zip` contains the files for that directory.

**Home Assistant Marketplace (if available):** Open **Settings > Marketplace** and use
**Custom repositories > Add via link** with
`https://github.com/Xerolux/hb-rf-eth-hass`. Open the integration's listing to
select and install a version. If your Marketplace does not offer prereleases,
use the manual ZIP installation below.

**HACS:** Add `Xerolux/hb-rf-eth-hass` as a custom repository in the
**Integration** category, install **HB-RF-ETH**, then restart Home Assistant.
Enable prerelease versions if you want to install a beta.

**Manual:** Extract the release ZIP into
`<config>/custom_components/hb_rf_eth` so `manifest.json` is directly inside
that directory, then restart Home Assistant. An existing config entry is
picked up by the new version after restart.

## Changelog

See the [versioned release notes](docs/release-notes) for upgrade information,
improvements, fixes and links to the full GitHub comparison. Add a curated
`docs/release-notes/<version>.md` before tagging a release.

## Development

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python -m pytest -q tests
.venv/bin/ruff check custom_components tests
```

## Status

**Stable release.** Version 0.3.0 reports unknown firmware and WebUI versions
until a successful update check. Skipped and failed checks expose their reason
as an update-entity attribute. Use the firmware MQTT discovery together with
**Services only** to avoid duplicate entities and periodic REST polling.

## Support the project

[GitHub Sponsors](https://github.com/sponsors/xerolux) ·
[Patreon](https://www.patreon.com/Xerolux) ·
[Ko-fi](https://ko-fi.com/xerolux) ·
[Buy Me a Coffee](https://buymeacoffee.com/xerolux) ·
[PayPal](https://paypal.me/xerolux) ·
[Tesla referral](https://ts.la/sebastian564489)

## License

MIT — see [LICENSE](LICENSE). The gateway firmware itself is licensed
CC BY-NC-SA 4.0 (see the [firmware repository](https://github.com/Xerolux/HB-RF-ETH-ng)).
