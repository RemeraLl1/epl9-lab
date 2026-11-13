# PEN-F and E-P7 lessons for the E-PL9 ART recipes

## Decision and scope

Source review completed on 2026-11-08, in this order: PEN-F HSL, then E-P7
Caduceus, then applicability to this project's ART integration.

Continue the E-PL9 implementation for exactly Watercolor I -> Kodak Gold
200-inspired and Watercolor II -> Kodak Portra 400-inspired. Preserve other
modes and the existing interface structure. The later
[ART integration scope](epl9-late-film-integration.md) retains the stock large
example photographs and replaces the two recipes' icons. This review does
not reopen that artwork decision. Open-gate/video work is deferred.
SD import is research only; do not implement it in this phase.

The useful transfers are design contracts: image-owned parameters, native
processing boundaries, validation of recipe data, and explicit separation of
configuration from pixel output. Neither an upstream firmware image nor a set
of upstream offsets is an E-PL9 patch.

This change contains documentation only. No firmware bytes were downloaded,
decoded, built or modified for this review; no camera, updater, SD card,
installed Workspace or owner media was accessed.

## Evidence levels and source pins

- **[S] Source inspection:** published code or documentation was read in this
  review. A source's assertions are not automatically independent verification.
- **[E] Reported offline result:** an upstream/project report describes execution
  or checks under its declared fixtures. Those runs were not reproduced here.
- **[C] Reported camera result:** the author reports physical testing on the
  named model. It is not a new test on the owner's E-PL9.
- **[I] Inference/proposal:** useful next work, not demonstrated compatibility.

| Source snapshot | Model/build covered | Pin |
| --- | --- | --- |
| fishcu/oly_fw_analysis | PEN-F public 3.1, internal 3101; HSL alpha-20261017 | [`9be1867ace6638d79e705048212dfddd3a1e794f`](https://github.com/fishcu/oly_fw_analysis/tree/9be1867ace6638d79e705048212dfddd3a1e794f) |
| cakelesscoder/caduceus-ep7 | E-P7 public 1.1, internal 1100; current v0.29a line | [`825f8e62a9650f7802dade669edce5eb882e112c`](https://github.com/cakelesscoder/caduceus-ep7/tree/825f8e62a9650f7802dade669edce5eb882e112c) |
| This project before this document | E-PL9 owner-reported 1.1; downloaded build 1101 | [`1f4dc523fc8db1a61863da66a09413627d5eb8e8`](https://github.com/RemeraLl1/epl9-lab/tree/1f4dc523fc8db1a61863da66a09413627d5eb8e8) |

For future reproduction, the E-PL9 stock input remains
`OLY_E_133_1101_0000_0000.BIN`, 104552480 bytes, SHA-256
`aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`.
Decoded main: 26214336 bytes, SHA-256
`8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`,
analysis base `0x60400020`. This identifies downloaded stock, not a dump of
the installed camera. See [initial findings](epl9-1.1-initial-findings.md).
Upstream input/output identities belong to their respective builders [P1, E7].

## 1. PEN-F: how the HSL modification is integrated

### Profiles, processing and persistence

[S] The published HSL patch extends stock COLOR1-3 with hue/lightness and
extends H/S/L editing to -7..+7. It is not a ready-made named Kodak film library.
Current profiles and C1-C4 registrations expose fifteen user-facing COLOR
recipes. Native paired settings records are not extra independent slots [P1, P3].

[S] The image hook runs the original COLOR builder and then replaces its H/L
output coefficients, retaining stock saturation and common LUTs. It checks the
callback, selected operation record and parent job before using extension data.
All sixteen valid operation records are supported; malformed values become
neutral before table lookup [P2].

[S] H/L live in validated alternate setting cells, carried by the stock
save/checksum/recall machinery. Publication follows the committed settings;
staged destination settings must not be exposed while other image settings
still describe the source bank. The reviewed cell ownership is specific to
PEN-F 3101, not proof of spare persistent cells on E-PL9 [P3].

[S/E] The transport follows committed settings -> capture/compact owner ->
processing job -> operation record -> COLOR configuration. Owners receive
value copies; a reused slot is overwritten completely. Separate preview and
recording converters must both carry H/L. Late reads of the current editor
would allow a later edit to change an earlier image [P4].

[C] The project reports physical live-view/JPEG, RAW-edit, profile, persistence,
custom-bank and reset tests within stated scopes. These do not establish every
RTOS schedule, DMA/cache interaction or exceptional completion path [P3, P4].

### RAW metadata and installation

[S/C] The patch also carries the captured rendering effect in native ORF CMIO
data. Workspace can render that effect, but this does not restore editable H/L
slider positions. Enabling its separate Adjust Color panel can replace the
embedded effect. This is a useful distinction for E-PL9 desktop trials [P5].

[S/E] The source builder checks stock ranges, placements, assembled hashes,
component metadata, checksum reconstruction and exact released output.
It produces main+OSD install and matching stock restore components [P1].

[C] Installation, stock restoration and reinstalling the published combined
PEN-F HSL release are author-reported physical results. [S] The SD updater's
validation/backend is mapped, but the complete physical OK+power entry and an
independent immutable rescue environment are not established. Successful recovery
from particular failures is not universal recovery proof [P6].
No PEN-F installation procedure is proposed for E-PL9.

## 2. E-P7: Caduceus profiles and SD storage

### The current implementation

[S/C] The current project uses stock COLOR1-4 as the host for film looks, with
Film, Saturation, Hue, Light and Extras pages. Its README/release reports physical
operation on E-P7. Some older design documents retain historical untested
status paragraphs; current source and later results must be checked together [E1].

[S] `LOOKS.BIN` is the selectable library; `BUNDLES.BIN` carries user slots,
names and edits. The loader runs after a gated first half-press rather than
reading files during early boot. Capture converters transport mode/profile
identity into the job extension; H/L readers validate the native job/record
relationship before looking up the bundle [E2].

[S] Live view has a separate H/L reader. It excludes capture jobs handled by
the capture transport and obtains the effective COLOR profile through a stock
getter. The capture-only reader was insufficient to provide the same preview.
This is not evidence of an immutable full-recipe snapshot on every E-P7 path [E3].

### Data validation and write context

[S] The reviewed `LOOKS.BIN` format has a 64-byte header and 64-byte records,
up to 32 looks. It carries version, E-P7 build 1100, stock SHA prefix, payload
length, CRC and layout identity. The consumer validates field ranges, class/slot
mask and bounded names. It contains parameter records, not an arbitrary 3D LUT [E4].

[S/E] SD-loader v3 retains a validated allocation and publishes its handle only
after checks. Accessors select that heap table or the baked fallback. Mutable
state is separate from the loaded firmware image [E5].

[C] Loader v2 restarted the E-P7 on its first half-press, even without a recipe
file. [I] Writes into loaded image sections were the leading suspected cause,
not a conclusively isolated cause. v3's design and read-only-image emulator
checks are useful lessons; they do not classify E-PL9 memory as writable [E5].

[S] Filesystem wrappers can message a worker and wait indefinitely. The loader
therefore checks its task context, loaded sections and mounted media. The
upstream analysis retains a possible queue-coupling deadlock and first-press
latency as residual risks. Copying an `fopen` address into an arbitrary E-PL9
UI callback would omit these dependencies [E6].

[S] Editor persistence sets a dirty flag, then saves from the half-press
context. The reviewed source writes/read-checks `BUNDLES.NEW`, copies the old
`BUNDLES.BIN` to `.BAK`, then writes/read-checks `.BIN`. Backup failure does
not stop the final save, and dirty is cleared before the attempt. This is not
an atomic rename transaction or proof against every media/power failure [E8].

[S/E] The packager rejects the wrong exact stock hash, unexpected bytes,
overlaps and metadata changes, and re-parses changed and restore packages.
Those are useful future build requirements; passing them does not establish
bootability [E7].

### Recipe controls and historical documentation

[S] From v0.24, choosing a tone-bearing library look also applies its stored
per-sector saturation through stock settings. Older statements that saturation
is only advice are historical. Contrast remains advice in the reviewed library
path; H/M/S are applied through stock profile settings, and Blacks/Whites use
additional slot fields [E4, E9].

[C] The library's WB tuning used E-P7 EXIF comparisons under one lamp: an A/B
step changed the relevant gains by about 4.4%, versus the original simulator's
1.5% assumption. [S] The source still calls H/L uncalibrated. This is evidence
against treating simulator slider scales as portable measurements [E10].

[S/C] CPU-side parameter success also did not guarantee visible colour grain:
the project records several stock-stage attempts without a visible result,
before later CPU-grain work. Grain and bloom should remain outside the minimum
Gold/Portra implementation [E11].

## 3. What carries over to E-PL9

| Mechanism | Useful lesson | E-PL9 boundary |
| --- | --- | --- |
| Native COLOR table/builder | Compare semantics and preserve native packing | The reported byte-identical 3028-byte table is a starting point, not an exposed COLOR editor or compatible patch [L1] |
| PEN-F image-owned values | Capture recipe identity/parameters with each image | Derive the E-PL9 owner and lifetime; do not copy pool addresses, offsets or spare-setting claims [P4] |
| Separate capture/preview consumers | Trace both callers explicitly | A correct saved-photo configuration does not certify live view [E2, E3] |
| E-P7 heap-backed SD library | Validate before publication; define fallback and lifetime | Future research only; no SD reader/writer is added here [E4-E6] |
| Reproducible edit lists | Exact inputs, expected bytes, metadata and independent reconstruction | A future E-PL9 packager needs E-PL9 identities and its own qualification [P1, E7] |
| Upstream camera tests | Evidence that the technique can work on that body | No transfer of recovery, memory/cache or pixel-output claims to E-PL9 [P6] |

[E] The current E-PL9 late integration already preserves the original ART
identity, uses the selected native owner, restores request state and supplies
persistent recipe tables. The subsequent native-producer work found a concrete
bug: producers emitted request kind `0x1000`, which the old recipe gates
excluded. The corrected gates accept that exact kind for the two selected ART
keys. This is more advanced than the early blanket key-rewrite proposal [L2, L3].

[E] The latest documented candidate runs at `0x604a1300` in an offline-modeled
early load. Its positive jobs stop at native `0x6073eafa`, the first unmapped
TruePic write to `0x9880014c`. They do not change output pixels or signal
successful completion. [E] Workspace exports separately demonstrate changed
E-PL9 color/tone through copied ORFs; those exports do not run the modified
camera job [L3-L5].

## 4. Gold and Portra: concrete comparison candidates

These numbers are alternative experiments, not replacement final recipes.
The E-PL9 native HSL draft uses signed coefficients in physical-record order;
Caduceus recipes use UI-sector arrays. Convert through a verified native builder
and explicit ordering, not by copying the integers [P2, E2, L6].

| Candidate | Contrast | Highlights / Midtones / Shadows | Balance / endpoints |
| --- | ---: | --- | --- |
| E-PL9 Gold v2 | +1 | -2 / +1 / -1 | Relative R/B 1.080/0.880 |
| E-P7 Gold library | 0, advice | -1 / +1 / 0 | WB A+2/G0; Blacks 0, Whites -1 |
| E-PL9 Portra v2 | -1 | -1 / +1 / +3 | Relative R/B 1.035/0.940 |
| E-P7 Portra library | -1, advice | -2 / +1 / +2 | WB A+1/G0; Blacks 0, Whites -2 |

[S] E-P7 H/L/saturation arrays and WB come from `lib2_gold` and
`lib2_portra`; endpoint additions come from `bundles/library_v3.json` [E12].
[E] The E-PL9 report confirms actual Workspace TIFF differences but describes
Gold as too orange in its tested indoor scene. Neither project establishes a
calibrated match to Kodak film or equal results across bodies [L5].
Film names do not require setting camera ISO to 200/400.

## 5. Next work, with acceptance boundaries

1. **Trace the actual E-PL9 producer and pixel-source provenance.**
   Follow the selected ART property through producer, native constructor and
   real source descriptors. Resolve crop, CFA, WB and sample packing. The
   `0x1000` correction is a demonstrated reason to extend from actual producers,
   not broaden format masks speculatively. Acceptance: declared source fields
   have native producers; request kind and pixel layout remain distinct [L3, L4].

2. **Finish ownership and reentry coverage.**
   Investigate remaining owner/resource callbacks, nonzero effect-object
   destruction and same-job access during the late hook's temporary request
   edits. Keep balanced acquire/release, pending completion and callback result
   handling. Acceptance: every new case either executes a specified path or
   stops at a named boundary; no modeled success hides a missing dependency.
   Existing whole-request/cache/non-target regressions remain required [L2, L3].

3. **Retain the current E-PL9 recipe drafts and compare alternatives separately.**
   When the existing workstation/media are available, use the qualified
   copy-only Workspace/CMIO path for controlled comparisons: current drafts,
   milder-WB variants and candidates inspired by E-P7. Isolate HSL, WB and tone
   changes; test neutrals, skin, foliage, sky and highlights under multiple
   illuminants. Acceptance: original RAW unchanged, measured output differences
   and an owner-selected direction. This is desktop fitting, not firmware
   qualification [L5, L6].

4. **Document an adapter before any future SD implementation.**
   Specify model/build, native units, sector order, schema version, limits,
   CRC, ownership, fallback and compatibility rejection. A Caduceus share-code
   or parameter format can be an interchange reference; an E-P7 card file is
   not directly accepted E-PL9 data. SD import remains unimplemented.

5. **Keep hardware milestones explicit.**
   Runtime code-slot/cache behavior, true source packing, TruePic output,
   completion, preview/capture consistency and photographic calibration remain
   open. Do not turn peripheral writes into synthetic pixels or describe more
   passing configuration probes as a completed camera image [L3, L4].

## 6. Reuse and limitations

[S] fishcu publishes no repository-wide license for all original tools and
writing; individual components have their own terms. Caduceus identifies its
authored code as Apache-2.0 and its external research submodule separately.
Keep upstreams as independent references, attribute ideas and check component
rights before copying code. This document republishes no upstream assembly,
firmware, tables, photographs or extracted resources [P7, E1].

This review checked published sources and their stated evidence. It did not
rerun firmware emulators, reproduce camera tests or independently audit every
upstream release edit. No installable E-PL9 update or recovery guarantee follows
from the comparison.

## Pinned primary sources

### PEN-F

- [P1: HSL source/build](https://github.com/fishcu/oly_fw_analysis/blob/9be1867ace6638d79e705048212dfddd3a1e794f/patches/hsl/pen-f/README.md)
- [P2: image-parameter assembly](https://github.com/fishcu/oly_fw_analysis/blob/9be1867ace6638d79e705048212dfddd3a1e794f/patches/hsl/pen-f/src/image_parameters/image_parameters.s)
- [P3: settings storage and commit lifecycle](https://github.com/fishcu/oly_fw_analysis/blob/9be1867ace6638d79e705048212dfddd3a1e794f/docs/color/pen-f/SETTINGS_STORAGE.md)
- [P4: image-owned parameters and asynchronous paths](https://github.com/fishcu/oly_fw_analysis/blob/9be1867ace6638d79e705048212dfddd3a1e794f/docs/color/pen-f/CAPTURE_PARAMETERS.md)
- [P5: ORF CMIO rendering versus sliders](https://github.com/fishcu/oly_fw_analysis/blob/9be1867ace6638d79e705048212dfddd3a1e794f/docs/color/pen-f/ORF_METADATA.md)
- [P6: update/recovery evidence and limits](https://github.com/fishcu/oly_fw_analysis/blob/9be1867ace6638d79e705048212dfddd3a1e794f/docs/boot/pen-f/RECOVERY.md)
- [P7: rights and provenance](https://github.com/fishcu/oly_fw_analysis/blob/9be1867ace6638d79e705048212dfddd3a1e794f/RIGHTS-AND-PROVENANCE.md)
- [Published alpha-20261017 release and physical-install report](https://github.com/fishcu/oly_fw_analysis/releases/tag/alpha-20261017)

### E-P7 Caduceus

- [E1: project status and supported body](https://github.com/cakelesscoder/caduceus-ep7/blob/825f8e62a9650f7802dade669edce5eb882e112c/README.md)
- [E2: capture bundle transport and H/L reader](https://github.com/cakelesscoder/caduceus-ep7/blob/825f8e62a9650f7802dade669edce5eb882e112c/patches/bundles/bundles.s.in)
- [E3: separate live-view H/L reader](https://github.com/cakelesscoder/caduceus-ep7/blob/825f8e62a9650f7802dade669edce5eb882e112c/patches/lv_bundles/lv_bundles.s.in)
- [E4: LOOKS.BIN compiler/validator](https://github.com/cakelesscoder/caduceus-ep7/blob/825f8e62a9650f7802dade669edce5eb882e112c/tools/ep7_looks_bin.py)
- [E5: SD-loader v3, v2 failure and unresolved cause](https://github.com/cakelesscoder/caduceus-ep7/blob/825f8e62a9650f7802dade669edce5eb882e112c/docs/SD_BUNDLES_V3.md)
- [E6: filesystem task context and queue risks](https://github.com/cakelesscoder/caduceus-ep7/blob/825f8e62a9650f7802dade669edce5eb882e112c/docs/SD_BUNDLES_V2.md)
- [E7: package/restore checks and E-P7 input hash](https://github.com/cakelesscoder/caduceus-ep7/blob/825f8e62a9650f7802dade669edce5eb882e112c/tools/build_package.py)
- [E8: actual save sequence](https://github.com/cakelesscoder/caduceus-ep7/blob/825f8e62a9650f7802dade669edce5eb882e112c/patches/look_editor/ed_ui.s.in)
- [E9: v0.24 saturation-setting code](https://github.com/cakelesscoder/caduceus-ep7/blob/825f8e62a9650f7802dade669edce5eb882e112c/patches/v024/sat.s.in)
- [E10: WB camera measurements and remaining calibration gaps](https://github.com/cakelesscoder/caduceus-ep7/blob/825f8e62a9650f7802dade669edce5eb882e112c/docs/LIBRARY_V1.md)
- [E11: grain experiments and camera results](https://github.com/cakelesscoder/caduceus-ep7/blob/825f8e62a9650f7802dade669edce5eb882e112c/docs/GRAIN_PORT.md)
- [E12: Gold/Portra arrays and WB](https://github.com/cakelesscoder/caduceus-ep7/blob/825f8e62a9650f7802dade669edce5eb882e112c/sim/recipes/library_v2.json); [tone endpoints](https://github.com/cakelesscoder/caduceus-ep7/blob/825f8e62a9650f7802dade669edce5eb882e112c/bundles/library_v3.json)
- [v0.29a release](https://github.com/cakelesscoder/caduceus-ep7/releases/tag/v0.29a)

### E-PL9 baseline used for this comparison

- [L1: exact stock identity and shared table](https://github.com/RemeraLl1/epl9-lab/blob/1f4dc523fc8db1a61863da66a09413627d5eb8e8/docs/epl9-1.1-initial-findings.md)
- [L2: late integration and preserved contracts](https://github.com/RemeraLl1/epl9-lab/blob/1f4dc523fc8db1a61863da66a09413627d5eb8e8/docs/epl9-late-film-integration.md)
- [L3: native owner binding, kind 0x1000 and current boundary](https://github.com/RemeraLl1/epl9-lab/blob/1f4dc523fc8db1a61863da66a09413627d5eb8e8/docs/epl9-native-owner-binding.md)
- [L4: real RAW input and missing TruePic executor](https://github.com/RemeraLl1/epl9-lab/blob/1f4dc523fc8db1a61863da66a09413627d5eb8e8/docs/epl9-real-raw-boundary.md)
- [L5: actual Workspace tone/WB trials](https://github.com/RemeraLl1/epl9-lab/blob/1f4dc523fc8db1a61863da66a09413627d5eb8e8/docs/epl9-tonal-neutral-trials.md)
- [L6: native HSL draft definitions](https://github.com/RemeraLl1/epl9-lab/blob/1f4dc523fc8db1a61863da66a09413627d5eb8e8/recipes/epl9-film-drafts-v0.json); [tone/WB definitions](https://github.com/RemeraLl1/epl9-lab/blob/1f4dc523fc8db1a61863da66a09413627d5eb8e8/recipes/epl9-film-drafts-v2.json)
