# E-PL9 SD recipe implementation study

The [native processing consumer](epl9-sd-processing-prototype.md) now reads
all supported record controls, prepares persistent descriptors and connects
T1/T2 to scoped native image-configuration and connected-job checks.

The latest [owned-state/two-slot prototype](epl9-sd-state-slots.md) adds a
manager-tail allocation and independent T1/T2 file bindings, with embedded
fallback. Native menu allocation and a film-processing consumer remain open.

The [native loader follow-up](epl9-sd-loader-prototype.md) now identifies an HLS_EVENT call point and adds an executable standalone loader, native CRC/range checking and an event adapter. This document retains the preceding format/descriptor experiment; it is not the latest loader implementation status.

## First results on November 7 2026

The practical design is **an embedded default for every reserved SD slot, with one optional file overriding that slot**. A missing or rejected file leaves its default active. A valid file in another slot still loads. The built-in majority always uses its embedded recipes. This behavior is implemented in a host prototype; the exact defaults and number of reserved camera slots remain to be selected with the owner.

Two experimental 660-byte recipe files reproduce the frozen Gold 200 v3 and Portra 400 v3 HSL/gamma data. The exact E-PL9 HSL builder and gamma setter execute successfully with the restored data at host-declared RAM addresses. Each configuration matches its embedded counterpart after accounting for the expected pointer differences. The stock read backend also returns each file's exact bytes and then EOF, using explicit host models for file metadata and storage requests.

This first pass establishes a data transport and selected native configuration path. The subsequent [standalone loader](epl9-sd-loader-prototype.md) extends it with native loading and a candidate trigger; actual SD I/O, dynamic menu labels and full-frame processing remain unverified. WB and H/S/M values survive the format unchanged, but new film-processing instructions reading those controls from RAM have not been implemented. The [Watercolor v3 candidate](epl9-v3-integration-status.md) remains the separate camera-test candidate.

## Files and slot behavior

Use one fixed file per reserved slot instead of a single library pack requiring edits whenever a recipe is changed. Proposed card layout, with DOS-style short names:

```text
EPL9MOD/
    SLOT01.RCP
    SLOT02.RCP
    SLOT03.RCP
    SLOT04.RCP
```

Four entries illustrate a possible initial allocation, not an accepted slot count. The host resolver supports logical file indices; it does not create or assign native ART entries. The file contains the recipe, while its filename selects the reserved slot. Moving a recipe from slot 1 to slot 2 requires renaming it, not recompiling its contents. The camera only needs to open its fixed paths; directory enumeration and a separate mapping file are unnecessary for this version.

| Card condition at the qualified load point | Reserved slot result |
| --- | --- |
| No card or no recipe directory | Its embedded default recipe. |
| File for this slot missing | Its embedded default recipe; other slots resolve independently. |
| Valid compatible file | That file's complete recipe, retained in RAM. |
| Bad checksum, wrong version/model, short or oversized file | Its embedded default, with no partially applied settings. |
| One bad file next to a valid file | Only the bad file's slot falls back. |
| File changes after a successful load | Current session retains its immutable recipe; the proposed first version reloads on the next power-on. |

Keep the slot's selected built-in film recipe as its default, rather than making it unusable when the card has no file. The defaults can come from the recipe shortlist after review. The study uses Gold/Portra as controlled examples, including duplicate defaults, not as a decision to consume additional camera slots with those two looks.

For consistent processing, the default and override should use the same supported film-processing route. Falling back to the old spatial ART effect would require a separate routing policy and could produce a surprising change of behavior merely because a file was absent. No additional stock modes are selected for replacement in this study.

## Adding a recipe conveniently

The intended user workflow is to choose or edit a look on a computer, select a destination slot, export the correctly named file, and copy that file to the recipe directory. Existing files in other slots need no edits. Card replacement and file preparation happen with the camera powered off for the first implementation.

The implemented developer workflow already separates editable definitions from the binary file. [The author example](../recipes/epl9-sd-example-v0.json) contains a name, ID, twelve native HSL triplets, contrast, H/M/S, two WB multipliers and a small list of gamma-curve knots. [The exporter](../scripts/epl9_sd_recipes.py) composes those knots with the exact native base curve on the computer. The camera would receive final curve values, avoiding curve fitting and division in the loader. The example's zero adjustments are a COLOR-template starting point, not a claim of equivalence to the Natural picture mode.

```powershell
.\.venv\Scripts\python.exe scripts/epl9_sd_recipes.py export recipes/epl9-sd-example-v0.json --out local/new-sd-example/SLOT01.RCP
.\.venv\Scripts\python.exe scripts/epl9_sd_recipes.py inspect local/new-sd-example/SLOT01.RCP
```

These commands only create experimental local files. They deliberately reject output outside a new path under ignored `local/`; physical card preparation is outside this phase. Generated curves and firmware-derived native data stay local. A later editor can call the same exporter and provide the destination filename without exposing native coefficients to normal users; that editor has not been built.

Recommended camera labeling is a stable custom-slot badge such as `C1` plus the name of the recipe actually selected, including its default name after fallback. Reserve embedded numbered badges for these mutable slots; preserve recipe-specific Gold/Portra icons on the fixed slots. Recipe artwork loaded from SD is unnecessary for the first version. Dynamic names still require an E-PL9 label-getter hook and width/font checks; the prototype's 31-byte ASCII storage limit is not a verified camera label width. Existing large ART example photographs stay stock.

## Experimental file format

The implemented format is **v0, 660 bytes, one recipe per file**. It is not compatible with E-P7 files or with an already-installed E-PL9 loader.

| Area | Contents |
| --- | --- |
| 64-byte header | Magic `E9R0`, format/header sizes, model 1330, downloaded main build 1101, total length, CRC-32, recipe ID, processing ABI, zero flags and a NUL-padded 32-byte name field. |
| 72 bytes | Twelve signed HSL triplets in native physical-record order. |
| 8 bytes | Signed contrast, highlights, midtones and shadows. |
| 4 bytes | Two native-order Q10 WB gains. |
| 512 bytes | One shared 256-entry native variant-zero gamma curve. |

CRC covers the complete record with its CRC field zeroed. The decoder checks exact size, every header field, name termination, supported ranges and monotone 12-bit curve values. The file carries no absolute camera pointers, native ART key or executable code. The firmware's own slot-binding table determines which reserved slot may use it; no card record can retarget a fixed slot.

One shared curve matches the current v3 design and avoids assuming physical RGB channel order. Independent channel curves, matrix/six-axis overrides and new spatial effects are outside this format. Broader recipes in the 29-profile desktop library need conversion and native qualification before export; the prototype does not turn arbitrary desktop effects into camera recipes.

## Native integration findings

The [read-only audit](../scripts/epl9_sd_recipe_audit.py) verifies 27 instruction anchors against the exact stock main and decodes the corresponding OSD names. E-P7 reference patterns remain pinned as described in [the hybrid design](epl9-hybrid-recipe-slots.md#e-p7-reference).

| E-PL9 entry | Static finding |
| --- | --- |
| `0x609ce1c8` | Open wrapper, path in A0 and mode in A1; routes through `0x609cf2ed`. |
| `0x609ce1d1` | Close wrapper. |
| `0x609ce357` | Public read wrapper; backend is `0x609ddff6`. The tested backend uses destination A0, file A1, item size D0 and count D1. |
| `0x609ce3e5` | Position wrapper; native implementation reads descriptor +308. |
| `0x609ce44f` | Seek wrapper; native implementation `0x609de2e4` uses origin **0=current, 1=end, 2=absolute**. Do not import the usual C enum values. |
| `0x609dba49` | Context classifier reads CPU state and task identity, compares the file-service task field and consults a registered-task lookup. |
| `0x60434a21` | Synchronous service RPC. Ordinary task routing publishes a request and waits for the reply with argument -1. |
| `0x60402373` / `0x604023b2` | Ordinary allocator/free pair; the observed size classes are 128, 2048 and 16384 bytes. |

The stock image includes 42 `C:\...` path literals, including DCIM paths, so the proposed camera-side prefix `C:\EPL9MOD\...` follows an existing naming convention. Mount readiness and which volume to use at the chosen trigger still require runtime qualification.

The fixed-size first format can request **661 bytes with item size 1**, accept exactly 660 and reject trailing data. This avoids seek/tell calls entirely. Keep ordinary buffered `r` initially. The existing `rd` route brings alignment/cache qualifications that are unnecessary to introduce merely for these small files. Full public open/read/close and a suitable caller task remain a separate test from the already-exercised read backend.

Loading must happen in a qualified ordinary task after storage is ready, outside frame configuration and IRQ callbacks. A first-half-press trigger works in the E-P7 reference, but its E-PL9 counterpart is not yet identified. Do not mark a load attempt complete merely because storage is not initialized yet. Once a file is accepted or rejected after readiness, freeze that slot for the session. The live view/capture path reads persistent descriptors, not files.

The current native film hook compares two hard-coded recipe keys, uses fixed table addresses to recognize prior film output, and emits contrast/H/S/M/WB arithmetic as instructions. The generalized implementation therefore needs both a firmware-owned slot lookup and parameter loads from a common descriptor. Copying bytes over the loaded module is unnecessary. Use allocated retained storage and qualified publication; do not borrow another model's writable state address or overwrite native parameter-object +20 with a new token. Preserve request restoration, cache rebuild behavior, owner callbacks and table lifetime while pending requests exist.

## Slot mapping and memory

The audit samples 65 and 39 contiguous static label records containing variant aliases and base names. For example, Watercolor I/II appear as UI values `0x1301/0x1302` in one representation and `0x10013/0x20013` in another. These are not processing keys `0x01010078/0x01020078`. Counts of label records are not counts of free menu slots. Native bindings and all label/settings consumers must be inventoried before assigning further recipes.

A compact file does not imply an equally small native table. Materialization currently copies the stock 3028-byte COLOR template and changes only its 72 authored coefficient bytes. A shared 512-byte curve can serve all three selected gamma pointers, as checked in the native setter experiment.

For an initial design with four reserved slots, allowing 128 bytes of descriptor metadata per slot and 64-byte record alignment gives **3712 bytes per slot**, 14848 bytes for four. A 704-byte staging area, including the extra length-check byte, and a proposed 128-byte registry total **15680 bytes**, within one 16384-byte ordinary-pool payload. The metadata allowances are design estimates, not measured camera allocation contracts. Allocation availability, suitable CPU/ISP aliases, alignment and the registry's root/lifetime remain open.

The ordinary `r` read path also uses transient physical bounce/control allocations. In the local two-read sequence for each file, both bounce and control allocations are balanced; this extra working memory is not included in the proposed 15680-byte resident payload. No global allocator or Wi-Fi buffer size was changed.

## Verification and reproduction

- [Fourteen synthetic tests](../scripts/test_epl9_sd_recipes.py) pass, including all 660 single-byte corruptions, resealed invalid headers/values, independent fallback, I/O errors, bounded oversize reads, immutable sessions and moving a file between logical slots.
- [The study runner](../scripts/epl9_sd_recipe_study.py) compiles both accepted v3 definitions, verifies exact HSL and three embedded gamma contents, then runs the stock HSL builder and gamma setter for embedded and RAM sources: four cases, 1145 native instructions each. The full 5200-byte configuration is checked against the existing packing oracle and expected gamma setters. Comparisons normalize only ten HSL LUT pointers and three gamma pointers; gamma pointer contents are checked separately.
- The same runner executes the native buffered read backend for both 660-byte files and checks EOF. File metadata, open state, storage geometry and SD-sector service are declared host fixtures. No new native loader, mount event, RTOS scheduling or physical card is modeled by these results.
- Five host scenarios cover no card, no files, one override, a corrupt neighbor and changed contents in the next simulated power-on. These are resolver states, not camera power cycles.
- A separate exporter/inspector run successfully creates and validates the public author example. The frozen v3 candidate's SHA-256 is checked before and after the study.

Retained evidence: `local/epl9-sd-slot-audit-20261107-final/audit.json` and `local/epl9-sd-slot-prototype-20261107-final/study.json`. Preliminary runs remain separate. Native listings, example exports and simulated-card files are ignored local artifacts.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_epl9_sd_recipes.py -v
.\.venv\Scripts\python.exe scripts/epl9_sd_recipe_audit.py --out local/new-sd-audit
.\.venv\Scripts\python.exe scripts/epl9_sd_recipe_study.py --native-listings local/new-sd-audit --read-listings local/wifi-limits-20261102-v6 --out local/new-sd-study
```

The audit can reuse retained listings with `--listings local/epl9-sd-slot-study-20261107`; their instruction bytes are rechecked. The read-backend study reuses the byte-checked listings and explicit service models from the [existing file-read prototype](epl9-wifi-offline-prototype.md).

## Input identity and next native work

Olympus E-PL9, displayed body 1.1 reported by the owner, downloaded main build 1101; installed camera bytes have not been dumped.

| Read input | Bytes | SHA-256 |
| --- | ---: | --- |
| Stock package | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Stock main | 26214336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |
| Stock OSD | 26214336 | `ee9a9c3ad1974dd212483ca7d012e51ae23083ce0119589a3b42996aa13ccf1e` |
| Frozen v3 main | 26214336 | `501707d09a0eb648e46196752b7ece17cd5368f6d54dbabce7c73e9806f65686` |

GNU reader SHA-256: `e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae`. The audit pins the external OSD decoder through the existing adapter; all source and listing hashes are recorded in the retained reports.

The [follow-up](epl9-sd-loader-prototype.md) now traces a candidate task/event and SD status and exercises the public file wrappers with explicit service models. Remaining consumer work is a descriptor-reading version of the film controls and a label resolver for effective default/override names and fixed custom-slot badges. Broader routing and concrete reserved-slot selection follow that mapping. These investigations are authorized now; their eventual firmware changes remain separate from the frozen Watercolor test candidate. No camera write, SD preparation or firmware package was produced by this study.
