# E-PL9 Lab

Tools and research notes for an Olympus PEN E-PL9 camera.

## Research goals

1. Document the camera's Wi-Fi API and USB interfaces.
2. Build a browser interface for browsing and downloading original files, and measure transfer performance.
3. Investigate applying named film recipes, then replacing ART presets with in-camera film looks.
4. Investigate gyro logging for Gyroflow and full-field 4:3 video at reduced resolution.
5. Determine hardware and firmware limits before making claims about additional video modes, including 4K60.

These are research goals. A working E-PL9 firmware modification has not been produced by this project.

## Local workspace

The initial Windows checkout is `D:\EPL9Lab`. Public source and documentation are separated from ignored local data:

| Folder | Contents | Published |
| --- | --- | --- |
| `scripts/` | Diagnostics and offline inspection tools | Yes |
| `docs/` | Scope, sources and verified findings | Yes |
| `tools/`, `downloads/` | Installed tools and their installers | No |
| `references/` | Independent upstream Git checkouts | No |
| `local/` | Machine configuration, installation records and private reports | No |
| `firmware/`, `captures/`, `samples/` | Firmware files, packet captures and camera media | No |

## Start

Run the workstation check from PowerShell:

```powershell
.\scripts\doctor.ps1
```

For an offline file identity report, use Python 3.12 or newer:

```powershell
.\.venv\Scripts\python.exe .\scripts\firmware_info.py .\firmware\camera-update.BIN --output .\local\firmware-info.json
```

The inspector reads a local file and reports its size, SHA-256 and initial bytes. It does not decode, modify or flash firmware.

The first camera session will record firmware versions, USB Storage/MTP descriptors, official-client recognition, Wi-Fi capabilities and transfer measurements. USB connection alone does not establish full firmware-dump access.

See [research scope](docs/research-scope.md) and [sources](docs/sources.md).
