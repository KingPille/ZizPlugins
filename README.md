<!-- ziz-plugins-distribution -->
# ZizPlugins

Installable plugin packages and updates for Dalamud/ZizLoader.

## Install in three steps

1. Open **Settings → Experimental → Custom Plugin Repositories** in your loader.
2. Add and enable this URL:

   ```text
   https://raw.githubusercontent.com/KingPille/ZizPlugins/main/pluginmaster.json
   ```

3. Reload the plugin installer, search for the plugin you want and select **Install**.

**That's it.** Future updates appear in the same plugin installer. No Git commands or manual DLL copying are needed.

If you previously loaded a manual development copy, disable that entry before installing another copy.
Keep your existing configuration and personal data.

## Available plugins

| Plugin | What it does | Source code |
| --- | --- | --- |
| **ZizDailyRoutines** | Configurable helpers for everyday FFXIV tasks. | [Browse](https://github.com/KingPille/ZizDailyRoutines) · [Download ZIP](https://github.com/KingPille/ZizPlugins/releases/download/DailyRoutines-v1.0.0.0/ZizDailyRoutines-1.0.0-Source.zip) |
| **ZizBestiarium** | Beastmaster bestiary, collection tracking and a capture autopilot preview. Open with `/zizbest`. | Included with its separate development package. |

### ZizDailyRoutines

**[Download plugin ZIP](https://github.com/KingPille/ZizPlugins/releases/download/DailyRoutines-v1.0.0.0/ZizDailyRoutines-1.0.0.zip)** · **[Download source code](https://github.com/KingPille/ZizPlugins/releases/download/DailyRoutines-v1.0.0.0/ZizDailyRoutines-1.0.0-Source.zip)** · **[Browse source](https://github.com/KingPille/ZizDailyRoutines)**

Use the repository URL above for the easiest installation. Manual users should extract the complete plugin ZIP
and keep its companion DLLs, assets and runtime folders together. The source download contains eight C# projects;
a complete clean build of that source snapshot has not been validated.

### ZizBestiarium

Tracks captured beasts separately for each character and plans missing creatures, including duty encounters.
The autopilot requires **ZizNav or vnavmesh**. Duties additionally require **ZizDuty**, Beastmaster level 50,
appropriate equipment and the necessary unlocks or premade party. These dependencies are installed separately.

Open `/zizbest` and use the first tab to start, pause or stop the autopilot.
Special boss mechanics may require intervention. The reported capture issue still needs runtime investigation.

## Compatibility and status

These packages target **Windows x64, .NET 10 and Dalamud/ZizLoader API 15**.
A different loader API level cannot load this build; adding the repository URL does not change that requirement.

Both packages are preview releases. Archive integrity and manifest consistency have been checked;
their runtime behavior in FFXIV has not been validated. See each release for its requirements.
Report issues with the plugin version, loader API level and exact status or error message.
Never include passwords or access tokens.

## Publishing updates

This repository hosts the package index, icons and versioned release downloads. Personal configuration and progress
files are not included. ZizDailyRoutines source is hosted in its [source repository](https://github.com/KingPille/ZizDailyRoutines).

For ZizBestiarium, increase the project and manifest versions together, build and check the project,
run its `Package.ps1`, then use `python publish.py --plugin-dir PATH_TO_PLUGIN --publish`.

For other configured packages, supply `--package`, `--manifest` and optionally `--source-zip`, `--source-repo`
and `--release-notes`. Omit `--publish` to prepare and inspect the files locally first.

The publishing script uses the existing GitHub login from Git Credential Manager. Credentials are never printed
or written to repository files. Existing release assets with different contents are not overwritten;
publish a new version instead. Public package downloads are verified against SHA-256 checksums before the feed is updated.

Repository format: [Dalamud: Custom Repositories](https://dalamud.dev/plugin-publishing/custom-repositories/).
