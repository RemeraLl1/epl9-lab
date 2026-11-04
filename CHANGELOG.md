# Changelog

Record meaningful changes in English. Describe the result, why it changed, the checks actually performed and remaining limitations. Link detailed research reports rather than treating an offline test as a camera feature. Dates use `YYYY-MM-DD`; an Unreleased entry is not an installable firmware release.

## Unreleased

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
