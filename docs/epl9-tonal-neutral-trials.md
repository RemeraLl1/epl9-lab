# E-PL9: neutral balance and tonal drafts v1/v2

## Outcome, 2026-11-04

**The owner-rendered v2 TIFFs confirm a working desktop path for changing tone as well as color.** Gold is warmer with denser shadows; Portra has milder warmth, much lighter shadows and lower contrast in the supplied indoor scene. These remain film-inspired engineering drafts. Gold is currently quite orange in this frame; neither recipe is a calibrated match to Kodak film or the chosen digital references.

The earlier v1 RGB-gamma experiment did **not** produce a pixel change in its isolated Portra control. V2 therefore retains the original RGB gamma and uses existing contrast and highlight/shadow/midtone metadata. The same settings also produce valid curves when supplied explicitly to the downloaded E-PL9 native configuration code. Neither result establishes execution of the final ART replacement on the camera.

This extends [the first color trials](epl9-film-draft-trials.md) and [CMIO bridge](epl9-workspace-cmio-bridge.md). Definitions are in [v1](../recipes/epl9-film-drafts-v1.json) and [v2](../recipes/epl9-film-drafts-v2.json); the reproducible copy-only tool is [epl9_tonal_drafts.py](../scripts/epl9_tonal_drafts.py).

The [native film-parameter handoff follow-up](epl9-film-native-handoff.md) now runs the complete color-configuration builder with the existing HSL/tone and three diagnostic gamma pointers together. It also checks tone composition and records a separate active-control interpreter boundary. It adds no new rendered photograph or on-camera claim.

## Inputs and preservation

The camera is an Olympus E-PL9, owner-reported displayed body version **1.1**. Analysis uses downloaded build **1101**, not a dump of the installed body:

| Firmware input | Bytes | SHA-256 |
| --- | ---: | --- |
| `OLY_E_133_1101_0000_0000.BIN` | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Decoded main, base `0x60400020` | 26214336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |

All drafts derive from the same owner ORF. RAW strips, decoded mosaic, original file, file length, embedded preview and metadata pointers are preserved. Only qualified HSL, WB and version-specific tone spans are allowed to change. Private source/output hashes and full comparisons are retained under ignored `local/`; photographs, firmware and proprietary DLL data are not published.

The installed OM Workspace 2.5W `OlyLaurel.dll` is SHA-256 `ebe999733cabd44fcff2d292574d1d732d5d70719e1f5db8a830541949dfa5cc`. Independent guarded execution of its previously inspected decoder leaf at RVA `0x1bb80` agrees with Python for **all 136064 bytes** of each v1/v2 T block. Guards remain unchanged. This checks CMIO encoding, not tone consumption.

The owner manually exported full-size Exif-TIFF without manual correction or resizing. Resulting images are **4608×3456 RGB8**, tagged `OM Workspace 2.5W`, with identical embedded sRGB profiles. Export UI state was not independently captured. Python measures and arranges the actual TIFF pixels; it does not synthesize the film effects.

## Neutral balance and the rejected gamma attachment

Both versions retain the v0 HSL coefficients. The measured ImageProcessing entries `0x0100` and `0x0101` each contain four unsigned halfwords, in observed **R, B, G0, G1** order. Both original vectors are `(496,496,256,256)`. Only their first two values change:

| Draft | Relative R / B proposal | Stored R, B, G0, G1 | LibRaw R/G, B/G |
| --- | --- | --- | --- |
| Gold v1/v2 | 1.080 / 0.880 | 536, 436, 256, 256 | 2.093750, 1.703125 |
| Portra v1/v2 | 1.035 / 0.940 | 513, 466, 256, 256 | 2.003906, 1.820313 |

LibRaw confirms the gain interpretation and identical decoded mosaics. The adjustment is relative to this capture's WB, not a fixed Kelvin setting or a neutral calibration for every illuminant.

V1 additionally composed a monotone output remap with the exact 256-entry shared RGB gamma at ROM `0x608c37e4`, CMIO T offset `0xbe6`. Native selector `0x6079d328` accepted the explicit table for all three channels under variant 0, retained the stock table under variant 1, and setter `0x6079d7a0` passed a whole-5200-byte configuration check. **These configuration checks did not prove that Workspace consumed the edited CMIO curve.**

An isolated Portra control restored that gamma to stock while retaining v1 WB, HSL and all other source bytes. Its exported TIFF is **pixel-identical to Portra v1: zero differing pixels**. Thus the selected gamma edit had no observed effect in this tested Workspace path. The result does not negate other native RGB-curve mechanisms or prove that all CMIO curves are unused. V1 is retained as a reproducible negative experiment; its JSON status describes the proposal at generation time.

## V2: existing contrast and H/S/M fields

The field names/layout follow the primary [ExifTool Olympus source](https://raw.githubusercontent.com/exiftool/exiftool/master/lib/Image/ExifTool/Olympus.pm), inspected 2026-11-04. Types, bounds, axis identifiers and source values were also checked directly in this owner's ORF before writing copies.

CameraSettings `0x0523` contains three signed halfwords `(value,min,max)`, originally `(0,-2,2)`. The first value is at file offset **9056**. `0x052e` contains 28 signed halfwords, beginning with H/S/M groups `(identifier,value,min,max)`: identifiers `-31999`, `-31998`, `-31997`, initial value 0, bounds -7..7. Their value offsets are **9074, 9082, 9090**. Identifiers, bounds and remaining entries stay unchanged. The tool requires the measured Natural PictureMode metadata `(2,2)` and rejects incompatible layouts.

| V2 draft | Contrast | Highlights | Shadows | Midtones |
| --- | ---: | ---: | ---: | ---: |
| Gold | +1 | -2 | -1 | +1 |
| Portra | -1 | -1 | +3 | +1 |

**Causal input control:** Portra v2 and the exported Portra v1-with-stock-gamma control differ in just **six file bytes**, all within those four signed values. Their CMIO P, CMIO T, WB and RAW are identical. The output changes therefore validate the **joint contrast/H/S/M adjustment**, subject to consistent manual export settings. Individual field effects and the exact Workspace curve shape have not been isolated separately.

For native correspondence, the same numeric H/M/S values are supplied explicitly to the five-short tone block at request `+1512`, with contrast at `+1795`. Native scaler `0x6074a061` and builder `0x6079f309` return with balanced stacks. For both Natural key 2 and COLOR key 11, each recipe selects its owned 256-halfword curve at configuration `+2612` through pointer `+2608`. Curves are monotone with endpoints 0 and 1023; **Natural/COLOR curves are byte-identical for each tested recipe**.

| Curve sample index | 0 | 16 | 32 | 64 | 128 | 192 | 224 | 255 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Gold | 0 | 51 | 106 | 246 | 547 | 778 | 913 | 1023 |
| Portra | 0 | 109 | 208 | 346 | 537 | 752 | 881 | 1023 |

Gold executes 37124 instructions for key 2 and 37142 for key 11; Portra executes 37085 and 37103. These are synthetic request/configuration checks using the exact native code, not a trace of ORF metadata being converted into a camera request or hardware pixel execution. The existing HSL packer checks still pass for both unchanged v0 coefficient sets. No untracked audit script is required by the new tool.

## Actual TIFF comparisons

Baseline is the previously exported `epl9-cmio-neutral.tif` control. Differences are computed on decoded RGB pixels, excluding file metadata.

| Comparison | Differing pixels | Mean absolute RGB difference (/255) | Maximum |
| --- | ---: | ---: | ---: |
| Neutral → Gold v1 | 98.2026% | 7.0744 | 25 |
| Neutral → Portra v1 | 97.4445% | 2.9556 | 17 |
| Neutral → Gold v2 | 99.6871% | 8.6685 | 29 |
| Neutral → Portra v2 | 100% | 14.0331 | 35 |
| Gold v1 → v2 | 97.7927% | 4.5836 | 14 |
| Portra v1 → v2 | 98.7010% | 13.2856 | 28 |

The negative gamma control explains why v1's changed pixels cannot be taken as evidence for the proposed RGB tone remap. V2 establishes a separate, effective tonal route. Portra's substantially brighter shadows are visible in the comparison. Gold remains too warm to accept as final on this scene alone.

Gold v2 has 0.042285% of channels at zero; Portra v2 has none. No baseline/v1/v2 channel reaches 255. This scene does not qualify highlight roll-off, clipping resistance or universal neutral balance. Multiple illuminants, neutral targets and highlight-rich scenes are still needed; the RGB differences are not film-fidelity scores.

Retained ignored artifacts:

- `local/epl9-film-drafts-v1-20261104/`: v1 ORFs/TIFFs and generation/decoder checks.
- `local/epl9-tone-isolation-20261104/`: restored-gamma Portra control, TIFF and zero-difference report.
- `local/epl9-film-drafts-v2-20261104/`: final current ORFs/TIFFs, generation manifest and independent decoder checks.
- `local/epl9-film-draft-pixels-v2-20261104/`: comparison image, TIFF metrics, v1/v2 pixel comparisons and six-byte input isolation.
- `local/epl9-tonal-native-validation-20261104/`: all four Natural/COLOR tone cases and curve comparison.

## Reproduction and limits

```powershell
.\.venv\Scripts\python.exe scripts/epl9_tonal_drafts.py --raw <owner.orf> --native-config --out local/new-tonal-drafts
# Default: v2. For the historical gamma experiment add:
# --recipes recipes/epl9-film-drafts-v1.json
# Export both generated ORFs in Workspace to full-size Exif-TIFF, then:
.\.venv\Scripts\python.exe scripts/epl9_workspace_pixels.py --reference <cmio-neutral.tif> --images <gold-v2.tif> <portra-v2.tif> --out local/new-tonal-pixels
```

The tool requires a new output directory under ignored `local/`, the qualified main and DLL, and bounded source layouts. It verifies declared byte spans, RAW-strip identity, decoded mosaic and WB interpretation. Generation manifests describe checks at generation time; later manual-export measurements are separate reports. No original, camera or installed application is written.

The final CLI run in a fresh output directory reproduces both owner-rendered v2 ORFs byte-for-byte and passes all four native tone cases. The workspace suite passes **167 tests**, including ten new tonal/WB contract tests. Native configuration and actual export comparisons are separate evidence. No unknown CMIO P array is relabeled or edited as a tone curve; historical job probes and diagnostic markers remain unchanged.

The desktop RAW-to-TIFF trial now works with these color and tone settings. The camera implementation still requires a qualified ART hook, caller/format handling, persistent parameter/table ownership and cache invalidation, actual ISP completion/output, and preview/capture/save/unrelated-mode checks. The boundary in [the real-RAW report](epl9-real-raw-boundary.md) remains open. Nothing here is an installable firmware image or proof of camera/software pixel equivalence.
