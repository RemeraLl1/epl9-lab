# Project updates

This is a research progress log, **not a firmware release history**. Dates describe publication/checkpoints. A draft PR or software test does not mean a camera feature is available.

## 2026-11-12

- Added a current English homepage, newcomer build walkthrough, contributor guide, branch map and explicit upstream attribution.
- [PR #8](https://github.com/RemeraLl1/epl9-lab/pull/8): public-source local builder now reproduces frozen Gold/Portra and stock main/OSD return from the exact original E-PL9 BIN. Private intermediate inputs are no longer required. Linux full-size reproduction verified; Windows not run. No automatic stock downloader or flashing operation.
- [PR #5](https://github.com/RemeraLl1/epl9-lab/pull/5): connected native updater fragments to persistent logical flash/readback, then a separate OM-Emu UI launch from those components. 13 modeled fault/install/return scenarios; 164 UI frames; 41 restored frames matched stock. No hardware reset, physical flash, sensor or ISP claim.
- [PR #4](https://github.com/RemeraLl1/epl9-lab/pull/4): host-side future bank up to 31 recipes and Delete built-in/SD switching contract. Native integration and the full recipe parameter set remain unfinished.
- [PR #6](https://github.com/RemeraLl1/epl9-lab/pull/6): documented how the Caduceus atlas can guide E-PL9 research without copying model-specific addresses.
- [PR #7](https://github.com/RemeraLl1/epl9-lab/pull/7): 30 OpenGate parameter experiments. Config values and buffers were modeled; zero real video frames were produced.
- ART-video investigation found conditional request paths that bypass the recipe type gates. Their relationship to ordinary recording is not yet established, so neither complete video support nor complete failure is claimed.
- All listed code PRs remained open drafts at this checkpoint. See [status](docs/PROJECT-STATUS.md) for dependencies, validation limitations and next steps.

## 2026-11-11

- Published the [`native-source-v1` candidate source and report](https://github.com/RemeraLl1/epl9-lab/tree/feat/native-source-v1-package) for the two ART looks and badges.
- Reproducibility and software-level qualification established an exact candidate/stock-return pair. Full image processing, physical installation and recovery remained unverified.
- Kept the first candidate separate from SD recipes, Delete, grain, OpenGate and other future features.

## Earlier research

Earlier dated documents remain available under `docs/`: initial firmware identification, ART dispatch, colour tables, icon resources, prototype processing, Wi-Fi and USB observations. Their original conclusions should be read in their historical context, not as current installation instructions. Start with [the current status](docs/PROJECT-STATUS.md) before continuing an older thread of work.
