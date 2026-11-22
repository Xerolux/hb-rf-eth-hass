# HB-RF-ETH in Home Assistant

[Deutsch](guide.de.md) · [Project README](../README.md) · [Support the project](../README.md#support-the-project)

## Install and connect

Use Home Assistant 2026.10.0 or newer and gateway firmware 2.4.0 or newer.
Install **HB-RF-ETH** through HACS as an Integration custom repository, or
extract the release ZIP so that `manifest.json` is in
`<config>/custom_components/hb_rf_eth/`. Restart Home Assistant.

Open **Settings → Devices & services** and confirm the discovered gateway.
If it is absent, choose **Add integration → HB-RF-ETH** and enter the gateway's
IP address or mDNS name. Use the username and password from the gateway WebUI.

## Change the address or password

Open **Reconfigure** on the integration entry. Enter the current IP address
or hostname. Leave the password field blank to use the saved password.
A rejected password triggers a reauthentication prompt. When changing
the address, the integration retains the existing entity IDs.

## Choose how entities are provided

- **REST entities:** The integration shows Ethernet and CCU connectivity,
  CPU and memory use, uptime, and firmware and WebUI updates. Set the polling
  interval to 10–300 seconds. The default is 30 seconds.
- **Services only:** Enable this if the gateway already provides entities
  via native MQTT discovery. Find those entities under the MQTT integration.
  HB-RF-ETH still provides backup, restore, log download, restart and update
  search.

## Actions and troubleshooting

- **Backup and restore:** Backups are saved in `<config>/hb_rf_eth_backups/`
  and contain credentials and certificates. For restore, enter the JSON
  filename from this folder.
- **Action target:** Select the gateway's device or an entity. You can omit
  the target when exactly one HB-RF-ETH gateway is loaded.
- **System log:** Enable log capture in the gateway WebUI before downloading
  the text file.
- **Unknown update version:** Run **Check for updates**. Check the update
  entity's `update_check_status` and `update_check_reason` attributes if the
  check was skipped or failed. Install firmware or WebUI updates from their
  respective update entities.
