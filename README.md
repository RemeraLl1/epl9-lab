# E-PL9 Lab

**Film looks and firmware research for the Olympus PEN E-PL9.**

## Start here

- **[Build the experimental Gold/Portra files →](docs/START-HERE.md)** — download the correct source branch, check your original firmware, and build locally. No GitHub experience required.
- **[Current progress and next steps →](docs/PROJECT-STATUS.md)** — what works in software, what remains untested, and where each workstream lives.
- **[Help develop or test →](CONTRIBUTING.md)** — choose a task and report reproducible results.
- **[Updates →](CHANGELOG.md)** · **[Credits and upstream projects →](docs/CREDITS.md)**

> **Research build, not a camera-tested release.** We can reproduce the experimental update file and run parts of the updater and menu in emulation. This does not establish safe installation, real image processing, or recovery on a physical E-PL9. There is no qualified E-PL9 flashing guide or public ready-to-install release yet. Do not use E-P7/PEN-F firmware or assume their instructions apply unchanged.

## Where this project comes from

This is an E-PL9 adaptation effort in the same Olympus firmware-modding community as **[Caduceus for E-P7](https://github.com/cakelesscoder/caduceus-ep7)** by **[cakelesscoder](https://github.com/cakelesscoder)** and contributors. Caduceus provides important ideas, tools and research references for bringing film looks to these cameras. We credit that foundation explicitly; we are not claiming to have invented the whole approach.

E-PL9 uses a different integration route: our first target replaces **Watercolor I/II in ART**, rather than assuming the E-P7's Colour Profile system exists here. Not every E-PL9 patch is a direct port, and Caduceus's camera-tested features are not evidence that our changes work. We also build on research from **[fishcu/oly_fw_analysis](https://github.com/fishcu/oly_fw_analysis)** and UI emulation from **[flatpanda/om-emu](https://github.com/flatpanda/om-emu)**. See [credits, licence boundaries and reuse rules](docs/CREDITS.md).

## What is available now?

| Work | Current result | Not established |
| --- | --- | --- |
| Gold 200 / Portra 400-inspired ART looks | Frozen experimental candidate; reproducible local builder; G200/P400 menu badges in emulation | Physical installation, calibrated camera JPEGs, video support |
| Local builder | Public source + exact original E-PL9 BIN recreate the same candidate and stock-return files | An automatic stock downloader or verified Windows run |
| Updater + UI emulator | Real instruction subsets → persistent logical flash → reread components → separate OM-Emu UI launch | Hardware reset, real NAND/controller behaviour, sensor/ISP/codec |
| Recovery | Software tests of stock main/OSD return after explicit entry into updater | Independent rescue if early main cannot start |
| 31 recipes, SD banks, Delete switch | Separate host-side reference model and recipe catalogue work | 31 working native ART recipes or on-camera SD/Delete integration |
| OpenGate | Parameter/buffer experiments on native code fragments | A recorded 4:3 movie, real frame rate, or hardware feasibility |
| Gyro / Wi-Fi / other functions | Research in progress | A usable time-synchronised gyro logger or universal camera control |

The first candidate remains frozen while awaiting hardware evaluation. Future recipes, SD switching, Delete-button changes, OpenGate and gyro work stay separate. The current menu text still says Watercolor I/II; badges alone do not prove image processing.

## Download the right code

The latest builder is currently in **[the volunteer-builder branch](https://github.com/RemeraLl1/epl9-lab/tree/develop/volunteer-builder-20261112)**, reviewed through [draft PR #8](https://github.com/RemeraLl1/epl9-lab/pull/8).

**The ordinary `Code → Download ZIP` on this main page does not include that builder yet.** Follow [Start here](docs/START-HERE.md), which takes you to the right branch. A draft PR is proposed work, not an installed feature or a released firmware image.

Olympus firmware, private camera media and credentials are not distributed here. You supply the exact original firmware locally. A successful build never installs anything on your camera.

## Find your area

- **First-time builders:** [Start here](docs/START-HERE.md).
- **Firmware and emulator developers:** [status and branch map](docs/PROJECT-STATUS.md), [contribution guide](CONTRIBUTING.md), then the workstream's own instructions.
- **Interested camera owners:** [how to volunteer](CONTRIBUTING.md#camera-owners), without treating this as a flashing invitation.
- **Historical research:** [scope](docs/research-scope.md), [initial firmware findings](docs/epl9-1.1-initial-findings.md), [sources](docs/sources.md). These dated notes are preserved as history; the status page explains later progress.

Not affiliated with or endorsed by OM Digital Solutions, Olympus, Kodak, Fujifilm, or the upstream authors. Film names describe inspired looks, not official film emulations. Project-wide reuse licensing still needs an explicit maintainer decision; upstream licences remain applicable to their own material.
