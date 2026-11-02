# E-PL9 Lab

[Русское введение](README.ru.md) · [Risks and limitations](docs/risks-and-limitations.md) · [Continue or port the research](docs/porting-guide.md)

> **Experimental amateur research — use entirely at your own risk.** The owner is learning as they go, has no specialist camera-firmware expertise, and uses AI assistance. Code, analysis and documentation may be wrong, incomplete or misleading, even when tests pass. This is not an official Olympus/OM System project or a supported firmware product. There is no installable firmware modification, validated recovery procedure or guarantee of compatibility. Experimental camera changes can cause permanent damage, an unusable camera or lost files. See the [full limitations](docs/risks-and-limitations.md).

This public repository is intended to let anyone inspect, question, reproduce and continue the investigation, including for other cameras. The reusable starting point is the research method and evidence, not transferable E-PL9 patch addresses.

Tools and research notes for an Olympus PEN E-PL9 camera.

## Research goals

1. Investigate applying named film recipes, then replacing ART presets with in-camera film looks.
2. Document the camera's Wi-Fi API and USB interfaces.
3. Build an offline-capable browser interface for browsing and downloading original files, and measure transfer performance.
4. Investigate gyro logging for Gyroflow and full-field 4:3 video at reduced resolution.
5. Determine hardware and firmware limits before making claims about additional video modes, including 4K60.

These are research goals. A working E-PL9 firmware modification has not been produced by this project.

The selected targets are [Watercolor I → Kodak Gold 200 and Watercolor II → Kodak Portra 400](docs/watercolor-gold200.md). Replace both slots' processing while retaining other modes. [E-PL9 routing findings](docs/epl9-art-routing.md) identify their shared worklist and candidate native color paths; no installable patch or calibrated recipe exists yet.

[Service dependencies](docs/epl9-service-dependencies.md) specify completion, callbacks, buffer handling and reference counts to preserve. The [icon-resource audit](docs/epl9-watercolor-icons.md) locates separate I/II badges and their UI-label associations in the exact E-PL9 image.

The [revised offline prototype](docs/epl9-integrated-prototype.md) preserves tested short/early schedules and executes native COLOR selection/build/return chains for both slots. Full pixel processing remains unverified, with explicit software boundaries recorded. The [ART example-picture audit](docs/epl9-art-example-pictures.md) separately inventories 220 JPEGs and one ICO and retains the owner's requirement to replace large menu examples.

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

The [first E-PL9 1.1 findings](docs/epl9-1.1-initial-findings.md) identify an exact shared COLOR table in the stock firmware. The [offline browser-client note](docs/offline-browser-client.md) separates cached interface behavior from camera transport requirements.

## Continue the project

Start with the [handoff and porting guide](docs/porting-guide.md) for the reading order, current blockers and a new-model checklist. [CONTRIBUTING.md](CONTRIBUTING.md) defines how to report evidence, corrections and reproduction steps. An unsupported instruction or missing dependency is an unresolved result, not a successful camera feature.

## License and reuse

Original project material is available under the [MIT License](LICENSE), except the MN103 reader's C/header files, which retain **GPL-3.0-or-later**. See [licensing and third-party notices](docs/licensing.md) and the [GPL text](LICENSES/GPL-3.0-or-later.txt). Firmware, manufacturer assets and independent upstream projects are not relicensed by this repository. Forks and ports are welcome; preserve applicable notices and describe what was actually verified.
