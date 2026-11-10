# E-PL9 hybrid recipe library study

Latest offline implementation: [owned loader state and two test slots](epl9-sd-state-slots.md).
T1/T2 are independent file aliases with embedded fallback, not final ART/menu assignments.

## Owner decision and current priority

On 2026-11-07 the owner chose to keep most recipes built into firmware and reserve a few slots for recipes supplied on the SD card. Less useful recipes in the planned 29-recipe library may be omitted to make room for these slots. The exact split, recipe selection and slot assignments remain open.

The immediate priority is the first functionality test of **Watercolor I → Gold 200 v3** and **Watercolor II → Portra 400 v3**. Keep the accepted looks, their embedded icons and stock large ART example pictures. The [v3 integration status](epl9-v3-integration-status.md) owns the candidate identity, completed checks and packaging gate. This future extension does not change that candidate or add an SD-loading prerequisite to its test.

The owner subsequently clarified that active offline implementation research should begin now, including missing-file behavior and convenient recipe addition. The [first technical results](epl9-sd-slot-study.md) include a host codec/resolver, native file-read-backend runs with modeled storage and embedded-versus-RAM HSL/gamma helper comparisons. The later [standalone native loader](epl9-sd-loader-prototype.md) adds a candidate HLS_EVENT point, SD readiness gates and native record validation. No loader is installed in a camera firmware image, and the larger menu allocation remains open.

## Library entries and camera slots

A library entry describes a look. A camera slot binds one selectable camera entry to a look and to its display resources. The planned 29-recipe pool is not a verified count of independent native menu entries. The [active gamma report](epl9-workspace-active-gamma.md) also distinguishes the separate 29-profile desktop catalogs from the two native Gold/Portra recipes; do not silently merge their counts or treat desktop postprocessing as a native recipe implementation.

The accepted storage direction is:

| Slot group | Recipe source | Intended use |
| --- | --- | --- |
| Built-in majority | Firmware | The selected core library is available without recipe files on the card. |
| Reserved SD minority | Validated data loaded into RAM from SD | Replace these looks on a computer without rebuilding firmware, within the processing features that the installed loader supports. |

The split applies to the eventual library. It does not authorize replacing additional stock ART modes during the current two-slot integration. SD records should address only designated SD slots; they should not silently override the embedded majority.

## Evidence available for the study

| Source | Established information | Remaining work for this extension |
| --- | --- | --- |
| [Current v3 candidate](epl9-v3-integration-status.md), [module builder](../scripts/epl9_film_module.py) and [late builder](../scripts/epl9_film_late_module.py) | Two separate native recipe identities; HSL and curve tables are embedded in the module. The current candidate preserves stock matrix and six-axis data. | Define a common data descriptor for both embedded and SD recipes; qualify each added slot. |
| [Late native source](../firmware_src/epl9_films_late.s.in) and [WB generator](../scripts/epl9_wb_extension.py) | Table addresses, contrast and tone biases are emitted into native code; WB gains generate arithmetic instructions. | Move supported controls into data as well as redirecting table pointers. Merely reading a file is insufficient. |
| [Connected job and cache investigation](epl9-integrated-prototype.md), [late integration](epl9-late-film-integration.md) | Cache comparison includes parameter-object +20; changing the pointer at +16 alone does not dirty the tested bit. The current hook also recognizes embedded table addresses. | Preserve cache identity and revise fixed-address recognition when introducing RAM-backed recipes. |
| [E-PL9 file-read study](epl9-wifi-transfer-limits.md) and [offline read prototype](epl9-wifi-offline-prototype.md) | Stock file-open/read routes are identified; selected native read paths run with bounded host storage services. | Qualify full open/read/close, mount readiness, calling task, allocation and error handling for recipe loading. The existing prototype supplies an already-valid file object. |
| [Icon investigation](epl9-watercolor-icons.md) | The accepted Gold/Portra replacements use embedded UI resources. | Choose how reserved SD slots display their names and icons without changing unrelated navigation. |

Firmware observations above concern **Olympus E-PL9, displayed 1.1 reported by the owner, downloaded main build 1101**. Exact byte sizes and SHA-256 values are pinned in the linked integration status and file-read reports. They do not identify the installed camera bytes.

## E-P7 reference

Reference checkout: [cakelesscoder/caduceus-ep7](https://github.com/cakelesscoder/caduceus-ep7), commit **`7d42c1f258737b7196c6b17cec5d643b5080ece6`**, under ignored `references/caduceus-ep7/`.

- [Film menu loader design](https://github.com/cakelesscoder/caduceus-ep7/blob/7d42c1f258737b7196c6b17cec5d643b5080ece6/docs/FILM_MENU_V2.md), section 4.2: first-half-press loading, bounded allocation, file size/header/CRC/range validation and publication after validation.
- [SD loader v3](https://github.com/cakelesscoder/caduceus-ep7/blob/7d42c1f258737b7196c6b17cec5d643b5080ece6/patches/sd_bundles_v3/sd_bundles_v3.s.in): data retained in allocated memory, a single load attempt per power-on and fallback after errors. Its comments record an earlier failed design that wrote into loaded-image memory.

These provide useful design patterns. E-P7 addresses, allocation pools, trigger hooks and binary formats are not E-PL9 compatibility evidence. In particular, first half-press is a candidate trigger to investigate, not an established safe E-PL9 file-I/O context. Keep external source in the ignored reference checkout.

## Proposed first implementation

Study a common recipe descriptor whose contents can come from firmware or a validated SD file. It should carry supported HSL adjustments, curve data, contrast, H/S/M biases and native-order WB gains. Preserve stock calibration and omit matrix/six-axis overrides from the first loader. Additional processing features need their own native qualification. The first host experiment uses one shared gamma curve, matching the current v3 configuration, rather than independently assigning physical color channels.

Use a host-side exporter to turn editable recipe definitions into bounded binary data. The file should contain versioned fields and relative offsets, with no executable code or camera memory pointers. Include target/model and processing-format compatibility fields, slot identifiers, lengths, a checksum, range checks and bounded display names. The exact path, extension, layout and maximum record count remain to be chosen after memory and UI investigation.

The proposed initial lifecycle is one load attempt per power-on, after storage and the chosen task are ready. Read into private staging memory, validate the complete file, then publish a persistent descriptor only after all checks pass. Capture and live view use RAM; they do not open a recipe file for each frame. Avoid live reload in the first implementation so referenced tables remain stable through pending requests, cancellation and owner cleanup. Card-write support and an on-camera recipe editor are separate future work.

The first prototype gives each reserved SD slot an embedded fallback recipe. One valid file overrides that slot; missing or rejected files retain its fallback and do not affect neighboring slots or the built-in majority. This is the recommended design under study, not an owner-selected fallback list or a native camera result. Fixed filenames provide slot binding; unsupported fields and corrupt data reject that slot's complete file. See the [results](epl9-sd-slot-study.md) for the proposed card layout and tests.

An SD-backed recipe still uses processing code installed in firmware. Replacing its parameters should not require a firmware update; adding a new processing algorithm or unsupported field may require one. Names and icons need an explicit design alongside the data loader; changing the file alone cannot change the current embedded artwork.

## Remaining implementation study

1. **Select the library and map slots.** Review the candidate recipes, retain the useful built-ins and choose how many SD slots are needed. Inventory actual native entry identities and all UI/settings consumers before assigning new slots or reusing modes. Preserve unrelated modes unless the owner subsequently selects replacements.
2. **Trace file I/O in a suitable task.** Follow E-PL9 open/read/close and allocator contracts through mount readiness, short reads, errors and cleanup. Determine a trigger that does not perform file I/O in an interrupt or image-processing callback. Preserve updater/startup dependencies and the frozen v3 code placement while investigating a new placement separately.
3. **Design descriptors and lifetime.** Replace embedded-address tests and generated numeric immediates with qualified data access. Preserve owner callbacks, original mode identity and reference counts. Establish cache invalidation for changed contents in the same slot; do not invent a meaning for parameter-object +20 beyond the tested native contract. Budget the largest permitted file, staging memory, resident memory and stack use against the actual allocator.
4. **Specify the format and exporter.** Set explicit limits, field ranges, compatibility checks, fallback behavior, name encoding and UI resource bindings. Keep model-specific conversion separate from the reference E-P7 format. A future format must not accidentally import firmware-derived tables into public source or export bundles.
5. **Run offline comparisons, then a bounded camera test.** Reuse identical Gold/Portra data first so storage is the only intended difference. Expand the library only after matching the embedded baseline under the same processing path.

## Later validation matrix

| Case | Required observation |
| --- | --- |
| Identical recipe embedded versus SD-backed | Matching configured tables and controls; later, matching camera output under fixed conditions. |
| Missing card/file, bad checksum/version, truncated or oversized file, duplicate or forbidden slot | Defined fallback, unchanged built-ins and no partially published recipe. |
| Allocation failure or short/error read | File closed, staging memory released, persistent state remains valid. |
| Power cycle, card replaced while powered off, selection/settings restored | Predictable slot binding, name/icon display and fallback. |
| Same slot loaded with different contents on the next power-on | New contents reach native configuration; no stale cache reuse. |
| Live view, still JPEG, pending request, cancellation and owner teardown | Stable table lifetime and preserved completion/refcount behavior; actual image behavior measured on the camera. |
| Unrelated ART modes and embedded slots | Existing routing, UI and settings remain consistent. |

Offline tests establish software contracts. They must not fabricate TruePic pixels or normal hardware completion. The immediate camera-test preparation continues through the existing v3 packaging gate independently of this future loader study; firmware flashing and camera writes remain outside the current authorized phase.
