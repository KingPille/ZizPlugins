<!-- ziz-plugins-distribution -->
# ZizPlugins

Plugin-Quelle für die Ziz-Plugins von TheLegendaryZiz / zizi45official.
Hier liegen die Installationsliste und die fertigen Pakete unter Releases.

## Installation

Diese URL im Loader unter **Einstellungen → Experimentell → Eigene Plugin-Quellen** hinzufügen und aktivieren:

```text
https://raw.githubusercontent.com/KingPille/ZizPlugins/main/pluginmaster.json
```

Danach den Plugin-Installer neu laden, **ZizBestiarium** suchen und installieren.
Weitere Versionen erscheinen über die normale Aktualisierung im Plugin-Installer.
In das Quellenfeld gehört die obige JSON-Adresse.

Falls zuvor eine DLL manuell als Dev-Plugin geladen wurde: diesen Dev-Eintrag deaktivieren,
bevor dasselbe Plugin über den Installer geladen wird. Die Sammlung liegt separat im
Konfigurationsordner; die eigenen Fortschrittsdateien nicht löschen.

## ZizBestiarium

Beastmaster-Bestiarium und Autopilot. Öffnen mit `/zizbest`.
Unter **Autopilot → Alle abklappern & fangen** starten.

- Liest vorhandene Pakte aus dem Spiel und plant fehlende Bestien ein.
- Reist zu freigeschalteten Fundgebieten, sucht Fundpunkte und verwendet Fangen mit eigener Rotation.
- Plant Instanz-Bestien über ZizDuty ein.
- Fortschritt, Favoriten und Notizen getrennt pro Charakter; Pause und Stopp im Fenster.

**Kompatibilität:** Windows x64, .NET 10 und Dalamud/ZizLoader **API 15**.
Ein Loader mit einer anderen API-Version kann dieses Paket nicht laden.
ZizNav oder vnavmesh muss zusätzlich installiert und bereit sein. Für Instanzen werden ZizDuty,
Beastmaster Stufe 50, passende Ausrüstung und die notwendigen Freischaltungen bzw. Gruppen benötigt.
Diese Abhängigkeiten werden durch diese Quelle nicht automatisch mitinstalliert.

**Testversion:** Der Autopilot wurde noch nicht im laufenden Spiel validiert.
Besondere Boss-Mechaniken können Eingreifen erfordern. Die Verteilung über GitHub bestätigt
keinen vollständigen automatischen Fangdurchlauf. Fehler bitte mit Plugin-Version und dem
genauen Status im Autopilot-Fenster melden. Keine Passwörter oder Zugangsdaten mitsenden.

## Neue Version veröffentlichen

Die Pakete werden lokal mit den passenden Dalamud-Bibliotheken gebaut. Dieses Repository
enthält Paketindex, Icon und Veröffentlichungsskript. Die Releases enthalten DLL und
die benötigten eigenen Daten, keine persönlichen Fortschrittsdateien.

1. Projekt- und Manifestversion gemeinsam erhöhen, bauen und prüfen.
2. Im Plugin-Projekt `Package.ps1` ausführen.
3. Hier `python publish.py --plugin-dir PFAD_ZUM_PLUGIN` ausführen und das Ergebnis prüfen.
4. Mit `python publish.py --plugin-dir PFAD_ZUM_PLUGIN --publish` Paket und Quellenliste veröffentlichen.

Das Skript verwendet die bestehende GitHub-Anmeldung aus Git Credential Manager.
Zugangsdaten werden weder in Dateien gespeichert noch ausgegeben. Bestehende Release-Dateien
mit abweichendem Inhalt werden nicht überschrieben; dafür ist eine neue Versionsnummer nötig.
Vor dem Aktualisieren des Index werden öffentliche Paketdownloads auf ihren SHA-256-Hash geprüft.

Formatbeschreibung: [Dalamud: Custom Repositories](https://dalamud.dev/plugin-publishing/custom-repositories/).
