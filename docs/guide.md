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

## Connect a remote gateway over Tailscale

Run a [Tailscale subnet router](https://tailscale.com/docs/features/subnet-routers)
at the gateway site. Advertise the gateway's LAN address as a host route or
advertise its subnet, approve the route in Tailscale, and allow the Home
Assistant host to reach the gateway's HTTP port. The Home Assistant process
must be able to use this route. Add each gateway manually using its LAN IP.

If a tailnet node forwards HTTP to the gateway, use that node's Tailscale IP
or MagicDNS name, with the forwarded port if it differs from 80. Enter the
address without an HTTP prefix. Use one address or port per gateway. The
integration uses this connection for REST status and actions. A CCU or
OpenCCU needs its own network path to the gateway's radio interface.

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
