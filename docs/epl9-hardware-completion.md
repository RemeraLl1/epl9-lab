# E-PL9: hardware-status completion and corrected destination descriptors

## Result, 2026-11-04

The exact native hardware-status handler now executes through the existing request callback, signal, wait and cleanup under explicit register stimuli. Both accepted recipe identities and both selectors are covered. More importantly, a real fixture error was found and fixed: destination descriptor +16/+18 are offsets, whereas the source descriptor uses those locations for area dimensions. Filling both structures identically programmed a destination address exactly past the buffer in the tested short cases.

This closes an address-construction error and exercises the status-to-cleanup contract. **It does not execute the ISP or produce a completed image.** Pixel buffers remain poisoned and unchanged; `full_pixel_cycle_passed` remains false. The native offset bug was in the host prototype, not evidence of a defect in stock camera firmware.

## Exact firmware

Olympus E-PL9, displayed body version **1.1** reported by the owner, downloaded main build **1101**. Stock input `OLY_E_133_1101_0000_0000.BIN`: **104552480 bytes**, SHA-256 `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`. Decoded main: **26214336 bytes**, SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`, base `0x60400020`. These are downloaded stock bytes, not a dump of the installed body.

The hash-pinned reader and byte-checked native decode are inherited from the [completion audit](epl9-completion-contracts.md). No firmware/container edits, camera commands or peripheral writes on the physical camera were performed.

## Corrected SRC/DST field contracts

The native diagnostic printers provide explicit names rather than an interpretation based on arithmetic alone:

| Offset | Source printer `0x6176a567` | Destination printer `0x6176a650` |
| --- | --- | --- |
| +0 / +4 | `pAddress` / `pAddressC` | `pAddress` / `pAddressC` |
| +8 | `usDataFormat` | `usDataFormat` |
| +10 | `usMemHw` | `usMemHw` |
| +12 / +14 | `usUseHw` / `usUseVw` | `usHw` / `usVw` |
| +16 / +18 | **`usAreaHw` / `usAreaVw`** | **`usOffsetH` / `usOffsetV`** |
| +20 / +22 | `usOffsetH` / `usOffsetV` | Format-specific data begins at +20 |

The former fixture wrote `(width,height)` into +16/+18 in both cases. For a 640×480 format-`0x302` destination, native address setup at `0x6073db42…0x6073e02b` then stored **OUTPUT+614400** in workspace+9068+208. That equals the first address after the 614400-byte backing. Two negative controls retain the old fields and reproduce this exact result for both identities. This initially appeared to be a possible extra plane; the explicit destination names and a controlled field change resolve it as an unintended output offset in this fixture.

The corrected fixture preserves source area dimensions and writes destination offsets `(0,0)`. The primary native address is now **OUTPUT**, and additional output-address slots match their own descriptors. All 32 normal hardware-boundary cases in the existing grid check these base addresses: eight baseline long cases, eight attached-table cases, eight independent short inputs and eight padded-input-stride cases. Slot allocation/borrowing and guard checks remain active. The base-address check is not a complete proof of DMA access extent, tiling, byte/channel order, alignment on every real caller, or completed output data.

`epl9_job_probe.py` reports named destination fields, the active native descriptor views, output configuration words and the exact native write site. Source and destination structures must no longer be populated through a shared assumption about +16/+18. Historical reports before this fix describe the old fixture and cannot establish a valid output address or a pixel cycle.

## Submission and status handling

`0x607419ea` calls the native slot lookup at `0x6074001a`, selected through ROM table `0x608be540`. Task-0 record base is **`0x62636adc`**, with 48-byte entries. It copies the request ID, callback and context into the record, copies processing flags, and wakes service ID 148 through `0x60449079`. One native submission component case confirms ID `0x8000`, callback `0x607504f6`, pending context and the expected record flag. The wakeup leaf is modeled; the RTOS scheduler does not run in this test.

The native status handler is **`0x607491e9`**. Its address is installed by code beginning `0x607497b8`, through service ID 148 and the registration front `0x60449065`. This establishes a firmware status-callback binding, not a measured physical interrupt-vector mapping or interrupt latency.

The handler reads and masks `0x9f000068/078` and `0x9f000070/07c`. For the tested bit `0x2000`, it also checks `0x9f009c24 & 0x9f009c20`. It emits acknowledgement/enable write intents and selects callback behavior:

| Register/record stimulus | Native observation |
| --- | --- |
| Status bit `0x2000`, enabled mask, detail bit 0 | Event 10 with status zero |
| Same status/mask, detail bit 1 | Event 10 with the halfword from record+44; tested value `0x9e01` is preserved |
| Status present but masked | No request callback or completion signal |
| No relevant status | No request callback or completion signal |
| Record flag bit `0x20` set, detail bit 0 | Re-enable write and return without final notification |
| Record flag bit `0x40`, secondary enabled status path | Event 10 through the secondary branch |

The status-branch labels above are descriptions of executed conditions, not a complete hardware register manual. The handler has other progress/error branches not covered by this matrix. Its acknowledgement writes are recorded; their exact physical read/write-to-clear semantics remain unmeasured.

Twenty-four runs cover six scenarios × two identity labels × selectors 0/2. The ISR/status code itself does not use the film identity or selector to render pixels. These labels check the same service contract for the target matrix, not that either film look was processed. The record is synthetic and the integrated job's peripheral boundary is not bypassed.

For final-notification scenarios the handler calls **native `0x6073eab3 → 0x607504f6`**, which delivers the existing owner notifications and signals the pending token. Native pending cleanup then returns the supplied hardware status, clears the event/token and all 56 pending bytes, with balanced stack. The isolated record has no live consumer ID; consumer/workspace teardown remains separately covered by the failed-job tests. Nonfinal scenarios retain the pending record and allocated token. The output payload and its guards stay unchanged in every replay.

## Finite register replay and remaining pixel boundary

`RegisterReplay` supplies an exact sequence of reads at individually declared addresses. Each read is consumed once; an extra/unknown/unaligned read fails. Writes are logged only for declared registers and do not create readiness or change later reads. No zero-filled peripheral pages, successful ISP implementation, autonomous interrupt generation or write-to-clear behavior are supplied. These are synthetic register stimuli, not captured measurements from the camera.

Further inspection also corrects a possible naming ambiguity: `0x607a478d` programs the `0x9990…` block and tables and returns; it is not itself the proven final wait. `0x6073f845` selects additional hardware programming paths at `0x60740255`/`0x6074044f`. Other code contains a polling loop at `0x6074015c…0x60740166` for masked status bits in `0x9f000070`. These parts must be connected to actual peripheral and cache/DMA behavior before treating a status notification as proof of usable image data.

A full result still needs the actual input-buffer producer, TruePic transformation, coherent output storage, real status progression and validation of captured pixels. A stock ORF/JPEG pair from this body can provide a photographic baseline; it cannot alone validate an in-memory YCC dump or the uncalibrated Gold/Portra replacements.

## Owner-provided RAW/JPEG reference

After the owner pointed to the project directory, a supplied pair in its root was decoded and inspected. Its JPEG identifies the E-PL9 and decodes at **4608×3456**. LibRaw reports a **4640×3472** decoded mosaic, `uint16` backing, white level **4095**, and color pattern indices `[[0,1],[3,2]]` with description `RGBG`. These are measurements from the decoder, not proof of native firmware packing or sensor ADC precision. No automatic central crop or firmware data-format mapping is inferred from the dimension difference.

The camera JPEG and host development show the same scene; filenames were supplied as a pair, but matching EXIF timestamps were not independently checked. The JPEG has strong stylization. The host reference uses camera white balance, disabled automatic brightness and 8-bit RGB output; it is visibly distinct from the camera rendering. No film recipe has been applied to the reference.

`scripts/epl9_raw_reference.py` reproduces the decode into a new ignored `local/` directory, preserving both originals. Optional dependencies are pinned in `requirements-raw.txt` (RawPy 0.28.0, NumPy 2.5.4 plus the existing Pillow requirement). The script saves the decoded mosaic, full-resolution LibRaw PNG, two previews and private input hashes/decoder metadata. Actual artifacts are in `local/owner-reference-20261104-final/`. Originals, generated images and metadata remain ignored and are not included in the public commit.

This supplies a real scene/mosaic baseline for the present checks, **not** a completed modified-firmware image. The earlier Wi-Fi research directory also contains independently captured original files; they are not republished or assumed to be the current pair.

## Validation and reproduction

```powershell
.\.venv\Scripts\python.exe scripts/epl9_hardware_audit.py --out local/new-hardware-audit
.\.venv\Scripts\python.exe scripts/epl9_job_probe.py --out local/new-job-output-audit
```

Reports require a new ignored directory and assertions enabled. Final retained outputs are `local/hardware-audit-20261104-output-fixed/results.json` and `local/job-output-offsets-20261104-final/results.json`.

The hardware audit passes the 24 finite status replays, native submission and descriptor-label anchors. The full job probe passes its previous route/COLOR/input/error/destructor/stride checks plus two old-offset negative controls and 32 normal output-base comparisons. The base check uses the actual native destination descriptor: long paths can use an owner-allocated intermediate buffer instead of the final output. An initial over-specific assertion assumed the final-output address and was corrected before the passing final run. All **125 workspace unit tests** pass, including four new tests rejecting exhausted/undeclared register access, confirming that writes do not manufacture ready bits, retaining ordinary memory bounds and bounding task wakeups. Independent Wi-Fi/video tests contribute to that total.

No correct output image has yet been obtained from modified ART processing. The deployable Gold 200 / Portra 400 replacements and their physical-camera validation remain unfinished.
