# HB-RF-ETH in Home Assistant

[English](guide.md) · [Projekt-README](../README.md) · [Projekt unterstützen](../README.md#support-the-project)

## Installieren und verbinden

Voraussetzungen sind Home Assistant ab 2026.10.0 und Gateway-Firmware ab
2.4.0. Installiere **HB-RF-ETH** in HACS als benutzerdefiniertes Repository
der Kategorie **Integration**. Bei manueller Installation entpacke das
Release-ZIP so, dass `manifest.json` direkt in
`<config>/custom_components/hb_rf_eth/` liegt. Starte Home Assistant neu.

Öffne **Einstellungen → Geräte & Dienste** und bestätige das gefundene
Gateway. Falls es dort nicht erscheint, wähle **Integration hinzufügen →
HB-RF-ETH** und gib die IP-Adresse oder den mDNS-Namen ein. Verwende die
Zugangsdaten der Gateway-Weboberfläche.

## Adresse oder Passwort ändern

Öffne **Neu konfigurieren** am Integrationseintrag und gib die aktuelle
IP-Adresse oder den Hostnamen ein. Lasse das Passwortfeld leer, um das
gespeicherte Passwort zu verwenden. Wenn das Gateway das gespeicherte
Passwort ablehnt, fordert Home Assistant zur erneuten Anmeldung auf. Beim
Adresswechsel behält die Integration die bestehenden Entitäts-IDs bei.

## Entitäten über REST oder MQTT

- **REST-Entitäten:** Die Integration zeigt Ethernet- und CCU-Verbindung,
  CPU- und Speicherauslastung, Laufzeit sowie Firmware- und WebUI-Updates.
  Das Abfrageintervall liegt bei 10–300 Sekunden und standardmäßig bei 30 Sekunden.
- **Nur Dienste:** Aktiviere diese Option, wenn das Gateway bereits
  Entitäten über MQTT-Discovery bereitstellt. Diese findest du unter der
  MQTT-Integration. Backup, Wiederherstellung, Log-Download, Neustart und
  Update-Suche bleiben über HB-RF-ETH verfügbar.

## Aktionen und Fehlersuche

- **Backup und Wiederherstellung:** Backups liegen in
  `<config>/hb_rf_eth_backups/` und enthalten Zugangsdaten und Zertifikate.
  Gib zum Wiederherstellen den Namen der JSON-Datei aus diesem Ordner ein.
- **Aktionsziel:** Wähle das Gateway-Gerät oder eine seiner Entitäten.
  Bei genau einem geladenen HB-RF-ETH-Gateway ist das Ziel optional.
- **Systemlog:** Aktiviere zuerst die Log-Aufzeichnung in der WebUI.
- **Unbekannte Update-Version:** Führe **Nach Updates suchen** aus. Wenn
  die Suche übersprungen wurde oder fehlgeschlagen ist, prüfe die Attribute
  `update_check_status` und `update_check_reason`. Firmware und WebUI
  aktualisierst du über ihre jeweilige Update-Entität.
