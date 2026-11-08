# Changelog

Record meaningful changes in English. Describe the result, why it changed, the checks actually performed and remaining limitations. Link detailed research reports rather than treating an offline test as a camera feature. Dates use `YYYY-MM-DD`; an Unreleased entry is not an installable firmware release.

## Unreleased

### Explicit native v3 input path, 2026-11-08

- Close a real native-builder gap: late modules previously always loaded v0 HSL and v2 tone even when external RGB/matrix/WB controls were supplied. Add a complete exact-byte-hash-pinned two-slot input route with no historical numerical fallback or diagnostic mixing. Do not supply or reconstruct the missing final v3 recipes.
- Feed explicit HSL/RGB data into native module tables and contrast/H/S/M/WB/matrix/six-axis into existing native hooks. Generate separate native midtone biases when the two recipes differ; preserve the old generated source, module bytes and patches for the same historical numbers. Keep ART identities, request restoration, exact `0x1000` gates and assembly templates unchanged.
- Record exact input and emitted table hashes; refuse partial use of the bundle through the early builder. Add both emitter and exact-image-probe CLI plumbing and a [continuation report](docs/epl9-native-v3-input-binding.md) with the schema, inaccessible source locations, exact stock/reader identities and remaining gates. No flashable container or camera operation is added.
- Fifteen new synthetic tests pass, including actual native control execution and emitted table-offset checks. With the separate ART gate tests, **164 available tests pass**. Full discovery fails at the missing pinned OSD decoder's setup; its five tests are not run. Exact firmware/reader probes, real frozen-v3 binding, full-size package validation, GUI and physical-camera checks remain unperformed.

### Input-free ART guard regressions, 2026-11-08

- Add seven [synthetic late-hook gate tests](docs/epl9-art-hook-gate-regressions.md) for both recipe keys, exact request kinds including `0x1000`, rejected neighboring kinds, color/gamma caller and control-record guards, and WB arithmetic/state preservation. Three in-memory removal mutations are detected for both slots.
- Leave production code and all numerical recipes unchanged. The available subset passes **149 tests**; full discovery is blocked by the missing pinned external OSD decoder, so its five tests are not counted as passed. No firmware-dependent, package, GUI or camera check was performed.

### Integration readiness refresh, 2026-11-07

- Synchronize published research through `1f4dc523fc8db1a61863da66a09413627d5eb8e8`: emitted native hooks, late owner-preserving integration, gain/matrix/placement/load checks, the exact ART request-kind 0x1000 correction and row-bounded icon/OM-Emu validation. Preserve implementation source unchanged.
- Add a first-integration readiness review: offline native integration exists, partial native GUI checks pass, and exact install/stock-return container work is active. Separate those milestones from physical ISP output, runtime qualification and recovery coverage; give no invented percentage, ETA or safety probability.
- Carry forward the owner's v3 recipe freeze, first two-slot priority and current main-plus-OSD package intent. Keep existing large ART example photographs and current stock text labels; the earlier photo-replacement plan is historical.
- Record the separate 29-recipe review and possible later hybrid built-in/SD slots without claiming implemented menu capacity or E-PL9 file-loader support. Keep Log/10-bit/HEVC paused.
- Update README, directory index, scope, handoff, installation guidance, diagrams and agent guidance. The public checkout passes **147 unit tests**; exact-image native probes, private recipe exports, full-size package checks, OM-Emu UI sessions and physical-camera tests are not rerun by this documentation work.
- Review **40 Markdown files and 307 local links/anchors**, complete directory coverage, five parsed/rendered diagrams and JavaScript syntax. Qualify two links to originating-workspace reports that are not supplied by the public checkout. Implementation source and numeric recipe data remain unchanged from published main.

### Direction paused, 2026-11-04

- Record the owner's decision to pause Log, 10-bit and HEVC work. A useful quality/dynamic-range gain has not been demonstrated, and ten-bit feasibility remains unresolved rather than proven impossible.
- Preserve an English summary of the uploaded handoff and its source-availability limits; do not delete the originating uncommitted work, fabricate its missing files, or automatically restart the investigation.
- Keep film/ART, Wi-Fi, full-field 4:3 video and gyro logging as separate directions. Update the README, scope, agent guidance, status, illustrated-plan table and directory index to carry the pause forward.

### Research refresh, 2026-11-04

- Synchronize the entire checkout with published main through `a399202a0d7ded05eedc4120b5e4676fcf059a70`, preserving the public-research documentation branch. Import the existing completion/hardware/real-RAW audits, Workspace bridge, v0/v1/v2 recipes and tonal tools/tests without modifying their implementations.
- Replace obsolete current-blocker summaries with the native peripheral/ISP boundary. Preserve earlier absent-callee, schedule, descriptor and failure observations as dated history.
- Document actual desktop CMIO controls and full-size Gold/Portra color/tone/WB TIFFs separately from modified-camera output. The v1/v2 source was published during the refresh and is now integrated: retain the negative gamma result, effective v2 joint tone route and remaining calibration limits. Update only v2's descriptive validation metadata, preserving every numeric parameter and the historical v1 definition.
- Add a complete documentation directory and source-qualified project-status handoff. Record newer deep-color, Wi-Fi rd/ISC, video timing/gyro and E-PL9 validator findings without inventing unavailable public scripts or importing private media.
- Update installation planning with reported same-build acceptance, checksum-before-write checks, duplicate-component and hidden-write-error limits, and restoration of every modified component. Early E-PL9 entry and physical recovery remain unresolved.
- Carry forward the requested 1920×1440 full-field/60 fps target and broader 31-profile/icon design backlog without presenting either as working firmware.
- Refresh diagrams, setup instructions, source navigation, agent guidance and the continuation workflow to match these evidence boundaries.

### Validation for the 2026-11-04 refresh

- The available public checkout passes **99 unit tests**, including ten newly published tone/WB tests, after restoring the exact pinned external OSD decoder in ignored `references/`. The earlier pre-tonal run passed 89. Its stored hash uses CRLF; the independently identified LF/CRLF identities and setup are documented. No image/decoder hash checks were disabled.
- The first clean-checkout run exposed the missing decoder; an LF source copy then correctly failed the recorded CRLF identity check. After verifying both forms of the pinned source and restoring the expected bytes, the complete suite passed. Historical Windows totals include independent unpublished work and are not reused as this run's count.
- Documentation links/anchors, directory coverage, SVG parsing/rendering, English text and whitespace are reviewed for the refresh. Exact-image firmware audits, private ORF/TIFF trials, Windows DLL execution and physical-camera tests were not rerun in the cloud.

### Documentation

- Explain the project's amateur, AI-assisted and at-your-own-risk status, evidence limits, reuse licenses and continuation/porting workflow. Preserve GPL-3.0-or-later for the MN103 adapter.
- Add a future installation/recovery plan distinguishing official stock USB updates from the unvalidated custom E-PL9 SD route. Document package identity, offline validation, preparation, acceptance checks and recovery limits.
- Add original illustrated processing/resource maps and conceptual recipe cards; distinguish draft G200/P400 artwork from installed changes and third-party photo references from distributable assets.
- Reconcile the documentation handoff with the latest published connected-job and icon research, and identify parallel Wi-Fi/video/gyro/color investigations as separate work awaiting reviewed evidence.

### Validation and limits

- Documentation links, SVG structure/rendering, English-only text and whitespace are checked for this change. Existing research-test counts belong to their linked reports; they were not rerun as part of this documentation update.
- No modified firmware package was produced, installed or tested on a camera. SD entry/completion, stock restoration and a full pixel-processing cycle remain unverified here.

## Future entry format

```text
Date and source revision:
Changed behavior or finding:
Reason:
Model/build and exact input identity (or link):
Checks actually run and evidence category:
Known limitations / failures / compatibility and restore impact:
Detailed report and next unresolved question:
```
