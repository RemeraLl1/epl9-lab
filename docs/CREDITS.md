# Credits, lineage and licence boundaries

E-PL9 Lab is an **E-PL9 adaptation effort in the Olympus firmware-modding community**, substantially informed by the projects below. We aim at the same broad goal of bringing custom film looks and useful controls to Olympus bodies while researching what the E-PL9 actually supports.

## Caduceus for E-P7

- Project: **[cakelesscoder/caduceus-ep7](https://github.com/cakelesscoder/caduceus-ep7)**.
- Author and contributors: **cakelesscoder and the Caduceus contributors**.
- [README](https://github.com/cakelesscoder/caduceus-ep7/blob/main/README.md), [firmware atlas](https://github.com/cakelesscoder/caduceus-ep7/blob/main/docs/ATLAS.md), [licence](https://github.com/cakelesscoder/caduceus-ep7/blob/main/LICENSE), [NOTICE](https://github.com/cakelesscoder/caduceus-ep7/blob/main/NOTICE).
- Upstream identifies its patch code, tools and docs as Apache-2.0, while its NOTICE identifies separately licensed components. Read the licence and notices of the exact files/revision being used.

Caduceus is a foundation/reference for our stock-plus-authored-changes builder workflow, firmware mapping, film-look investigation and model-specific adaptation work. Its OSD tooling has been used in the research. The E-PL9 builder regenerates our existing changes from public authored inputs plus the user's original firmware; it does not simply apply an E-P7 `edits.json` or invoke the Caduceus implementation.

Our current target is Watercolor I/II in **ART**. E-P7's Colour Profile implementation, addresses, features, update behaviour and camera validation cannot be assumed to transfer. This is not an official Caduceus release, endorsement or a claim that all of our code is a direct port.

Upstream explicitly asks ports/remixes to preserve its NOTICE, credit recipe authors and never redistribute OM firmware. When copying/adapting Caduceus material, include the applicable licence and NOTICE, preserve copyright/attribution, identify changed files, and respect separately licensed dependencies. A link here alone does not replace those obligations. This documentation update does not import or relicense upstream code.

## PEN-F research and emulation

- **[fishcu/oly_fw_analysis](https://github.com/fishcu/oly_fw_analysis)**: PEN-F firmware analysis, native-instruction research and emulator harness. Check the licence of the exact revision and files before reusing code. Its current main LICENSE identifies Apache-2.0, while Caduceus NOTICE describes its pinned external research dependency as GPL-3.0; do not treat these revisions as interchangeable. Its camera results belong to its tested models, not automatically to E-PL9.
- **[flatpanda/om-emu](https://github.com/flatpanda/om-emu)**: upstream UI emulation used for the E-PL9 menu experiments. Keep upstream separate, record the pinned commit and preserve its licensing. Our UI bridge is not a replacement claim for authorship of OM-Emu, and UI success is not hardware/ISP emulation.
- Other sources and earlier researchers are recorded in [sources](sources.md) and the relevant topic reports. Retain their provenance when extending that work.

## Recipe provenance

Credit each recipe's actual author, source and subsequent changes. A film name is not provenance and a renderer approximation is not a calibrated camera profile. Do not copy a catalogue or claim compatibility without its parameters, format and licence. The creative 31-entry catalogue and native ART integration are distinct stages.

## This repository's licence status

At the 12 November 2026 documentation update, no project-wide `LICENSE` was present in E-PL9 Lab. Public visibility alone is not a general permission to reuse the whole repository. This update adds attribution and contribution guidance, not a new licence grant. The maintainer must resolve the project's own licensing explicitly; upstream material retains its existing terms.

Olympus/OM firmware and extracted assets are not redistributed. Trademarks and film names belong to their respective owners. Neither E-PL9 Lab nor its contributors claim endorsement by Olympus/OM Digital Solutions, Kodak, Fujifilm, Caduceus, or other upstream authors.
