"""Constants for the HB-RF-ETH integration."""

DOMAIN = "hb_rf_eth"

DEFAULT_USERNAME = "admin"
DEFAULT_POLL_INTERVAL_SECONDS = 30
MIN_POLL_INTERVAL_SECONDS = 10
MAX_POLL_INTERVAL_SECONDS = 300

# Options (stored in entry.options, editable via the Options flow).
# services_only is the coexistence mode for installations that already use
# the firmware's native MQTT/HA auto-discovery for entities: the integration
# then provides only its services (backup/restore/log/restart/update check)
# and registers no entities, avoiding duplicates.
CONF_SERVICES_ONLY = "services_only"
CONF_POLL_INTERVAL = "poll_interval"

DEFAULT_OPTIONS = {
    CONF_SERVICES_ONLY: False,
    CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL_SECONDS,
}

# mDNS service announced by the firmware (see main.cpp of HB-RF-ETH-ng).
# HA's manifest entry needs the fully qualified type including ".local.".
ZCONF_SERVICE_TYPE = "_hb-rf-eth._tcp.local."
