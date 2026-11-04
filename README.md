# E-PL9 Lab

[Current status](docs/project-status.md) · [Documentation directory](docs/README.md) · [Risks and limitations](docs/risks-and-limitations.md) · [Continue or port the research](docs/porting-guide.md)

> **Experimental amateur research — use entirely at your own risk.** The owner is learning as they go, has no specialist camera-firmware expertise, and uses AI assistance. Code, analysis and documentation may be wrong, incomplete or misleading, even when tests pass. This is not an official Olympus/OM System project or a supported firmware product. There is no installable firmware modification, validated recovery procedure or guarantee of compatibility. Experimental camera changes can cause permanent damage, an unusable camera or lost files. See the [full limitations](docs/risks-and-limitations.md).

This public repository is intended to let anyone inspect, question, reproduce and continue the investigation, including for other cameras. The reusable starting point is the research method and evidence, not transferable E-PL9 patch addresses.

Tools and research notes for an Olympus PEN E-PL9 camera.

## Research goals

1. Investigate applying named film recipes, then replacing ART presets with in-camera film looks.
2. Document the camera's Wi-Fi API and USB interfaces.
3. Build an offline-capable browser interface for browsing and downloading original files, and measure transfer performance.
4. Investigate synchronized gyro logging for Gyroflow and full-field 1920×1440 video at 60 fps; these remain requested targets, not working modes.
5. Determine hardware and firmware limits before making claims about additional video modes, including 4K60.

These are research goals. A working E-PL9 firmware modification has not been produced by this project.

The first implementation baseline is [Watercolor I → Kodak Gold 200-inspired and Watercolor II → Kodak Portra 400-inspired](docs/watercolor-gold200.md), preserving unrelated modes. The wider 31-profile catalog and its icons are a design backlog, not 31 working camera slots.

**On hold:** Log, 10-bit and HEVC research, by owner decision on 2026-11-04. No practical quality/dynamic-range gain or genuine ten-bit recording is established. Preserve the [findings and resumption limits](docs/log-ten-bit-handoff.md); do not automatically restart this direction. Other project goals remain separate.

## Current evidence, 2026-11-04

**Real desktop color, white-balance and tonal draft images now exist. The modified camera pipeline still has no complete pixel cycle or installable package.** See the [status report](docs/project-status.md) for exact evidence provenance and newer work reported by other chats.

| Area | What is established | What remains open |
| --- | --- | --- |
| Native pipeline | [Connected construction, table attachment and completion contracts](docs/epl9-integrated-prototype.md), plus corrected [destination descriptors/status handling](docs/epl9-hardware-completion.md) | Actual ISP/DMA execution, coherent pixels and successful complete jobs |
| Real RAW input | [Eight actual-mosaic configuration cases](docs/epl9-real-raw-boundary.md) reach a peripheral boundary; the CPU prefix makes no source-pixel reads | Actual camera crop/CFA/packing and a usable native pixel executor |
| Desktop recipes | [Workspace controls](docs/epl9-workspace-cmio-bridge.md), [v0 color trials](docs/epl9-film-draft-trials.md) and [v2 tone/WB trials](docs/epl9-tonal-neutral-trials.md) have actual full-size TIFF exports | Calibration across scenes/illuminants, native hook and on-camera preview/capture behavior |
| UI resources | [G200/P400 draft icons](docs/epl9-watercolor-icons.md#standalone-replacement-artwork-2026-11-02) fit ten allocations; [photo references](docs/epl9-art-example-pictures.md) have provenance | Runtime screen/palette/photo bindings and final distributable artwork |
| Other research | Newer Wi-Fi, video/gyro, deep-color and E-PL9 recovery results are summarized as [reported work](docs/project-status.md#newer-reported-work-awaiting-publication-or-independent-reproduction) | Corresponding public source, reproducible evidence and physical-camera validation |

The current public definitions are [v2 color/tone/WB drafts](recipes/epl9-film-drafts-v2.json), retaining the original [v0 color base](recipes/epl9-film-drafts-v0.json). The [v1 gamma proposal](recipes/epl9-film-drafts-v1.json) is retained as a negative experiment: its isolated RGB-curve change produced no pixel difference, while v2's joint contrast/H/S/M change did. Gold v2 is still too warm in the test scene; these are not calibrated film matches. Desktop TIFFs do not execute the modified native worklist. Firmware, original media and generated TIFFs remain local.

## Planned changes and future installation

The [illustrated change plan](docs/planned-changes.md) shows the two-slot processing, name, icon and menu-example changes, with conceptual selection cards and a status map for parallel investigations. The [future installation and recovery guide](docs/firmware-installation-plan.md) explains the official stock USB route, candidate custom SD route, preparation and unresolved restore limits. It is a planning document, not an instruction to flash now.

![Planned mapping of two Watercolor slots to separate film recipes, with linked processing and UI changes](assets/docs/recipe-change-map.svg)

Follow [CHANGELOG.md](CHANGELOG.md) for meaningful updates, validation and limitations.

## Local workspace

The initial Windows checkout is `D:\EPL9Lab`. Public source and documentation are separated from ignored local data:

| Folder | Contents | Published |
| --- | --- | --- |
| `scripts/` | Diagnostics and offline inspection tools | Yes |
| `docs/` | Scope, sources and verified findings | Yes |
| `recipes/` | Versioned original draft parameters, not installed firmware | Yes |
| `assets/` | Original artwork, diagrams and source metadata | Yes |
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

Start with the [documentation directory](docs/README.md) and [clean-checkout prerequisites](docs/windows-setup.md#clean-checkout-and-cloud-reproduction-2026-11-04). The original first-session checklist is historical: owner media, desktop exports and initial USB observations now exist. Live camera behavior remains limited to specifically recorded observations; USB enumeration is not full firmware-dump or update readiness. The [offline browser-client note](docs/offline-browser-client.md) separates a cached interface from camera-network access.

## Continue the project

Start with the [handoff and porting guide](docs/porting-guide.md) for the reading order, current blockers and a new-model checklist. [CONTRIBUTING.md](CONTRIBUTING.md) defines how to report evidence, corrections and reproduction steps. An unsupported instruction or missing dependency is an unresolved result, not a successful camera feature.

## License and reuse

Original project material is available under the [MIT License](LICENSE), except the MN103 reader's C/header files, which retain **GPL-3.0-or-later**. See [licensing and third-party notices](docs/licensing.md) and the [GPL text](LICENSES/GPL-3.0-or-later.txt). Firmware, manufacturer assets and independent upstream projects are not relicensed by this repository. Forks and ports are welcome; preserve applicable notices and describe what was actually verified.
