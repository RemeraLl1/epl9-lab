# E-PL9: CMIO bridge to an installed software RAW engine

## Outcome, 2026-11-04

The owner exported a full-size Natural reference from their ORF using OM Workspace. The TIFF is **4608×3456, RGB, 8 bits/channel, uncompressed, sRGB**, with software tag `OM Workspace 2.5W`. It is a real desktop application export, not output of the modified camera route. Its original export settings were observed through the GUI; the internal decoder/DLL execution sequence has not been traced. The TIFF and its preview remain private in ignored `local/workspace-raw-20261104/`.

The same E-PL9 ORF contains native CMIO processing data. Its encoded table block is byte-identical to a block in this exact E-PL9 firmware. Decoding recovers complete Natural and COLOR tables and a common RGB curve that independently match the firmware. This provides a concrete **candidate parameter-transport route into Workspace**, beyond a shared constant in an installed DLL.

Two copied ORF controls have been prepared, preserving every RAW strip and every byte outside explicitly listed CMIO spans. One carries neutral COLOR coefficients; the other carries a strong negative saturation control. **Their rendered images have not yet been exported or compared.** The intended effect, Workspace's consumption of the changed fields and equivalence to the camera ISP remain unverified. They are diagnostic controls, not Gold/Portra recipes or modified firmware.

## Exact inputs

- Olympus E-PL9, owner-reported body version **1.1**, downloaded main build **1101**; not a dump of the installed camera.
- Stock `OLY_E_133_1101_0000_0000.BIN`: **104552480 bytes**, SHA-256 `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`.
- Decoded main: **26214336 bytes**, SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`, analysis base `0x60400020`.
- Installed `OlyLaurel.dll`: SHA-256 `ebe999733cabd44fcff2d292574d1d732d5d70719e1f5db8a830541949dfa5cc`. The runner rejects another binary. It extracts constants locally and does not redistribute the DLL or its tables.
- Original ORF, TIFF, extracted CMIO data, disassembly, per-file hashes and generated copies remain ignored. The owner-supplied originals are unchanged.

The PEN-F CMIO work in the ignored upstream checkout at revision `539fcf1fa9eda5fdef8ede4deeab94a4691d94c3` suggested this experiment: [ORF metadata report](https://github.com/fishcu/oly_fw_analysis/blob/539fcf1fa9eda5fdef8ede4deeab94a4691d94c3/docs/color/pen-f/ORF_METADATA.md). Its offsets and formats are **not** used as E-PL9 compatibility evidence. This E-PL9 has different CMIO sizes, revision and table/parameter locations; all below were measured locally. Upstream source was not copied into this project.

## Measured E-PL9 layout

Olympus ImageProcessing IFD `0x2040` contains:

| Tag | Role | Bytes | Header |
| --- | --- | ---: | --- |
| `0x0635` | Parameters P | 8960 | `CMIO`, little-endian `0xdc130001` |
| `0x0636` | Encoded tables T | 136064 | same |

T matches decoded-main file span `0x54b9e0…0x56cd5f`, SHA-256 `d6b0b8afabeca79490eb7c8812e816441cb8d52131eeb29d668c80c31e9a4f57`. This identifies a static native table payload in the supplied ORF, not that its full processing state matches the synthetic native job.

After decoding:

| T offset | Exact firmware correspondence | P coefficient offset |
| --- | --- | --- |
| `0x6ebe` | Full 3028-byte Natural table at `0x608e499c` | `0x7b4` |
| `0x7a92` | Full 3028-byte Natural table at `0x608e5570` | `0x7fc` |
| `0xe506` | Full shared COLOR table at `0x608ee360` | no captured COLOR triplet bank identified here |
| `0x0be6` | Full 512-byte common RGB curve at `0x608c37e4` | not changed |

At each Natural P offset, all 72 bytes equal the corresponding ROM table's twelve signed H/S/L triplets (record offsets +12/+14/+16). This is an independently checked structure match, not a claim that Workspace always consumes these fields. The two banks correspond to the native selector's request+1799 alternatives; their UI/output-color-space bindings have not been measured on E-PL9 and are not assumed from PEN-F.

Native selector `0x6079e1f6` selects key 2 through `0x6079e405`. With other tested fields zero, request+1799 chooses parameter structure `0x608ff9a8` or `0x608ff9dc`, whose first pointers are the two tables above. Other request flags can select different structures. Static listings remain in ignored `local/art-routing/cmio-color-source-*.tsv`.

## Encoding and independent native check

Read-only inspection found the installed software's bounded decoder leaf at **OlyLaurel RVA `0x1bb80`**, length **120 bytes**, SHA-256 `c6b12e8f0ba5407f8bad25f2d4ae4fb45d671935e7bd82381cc76e7ddc404380`. Its Win64 argument registers are RCX unused, RDX block pointer, R8D byte length. It reads a 63-word constant bank at RVA `0xabfe0`, starts at block+8, and does not call external routines. An isolated Python process invoked this inspected leaf on guarded copies, using the unchanged installed DLL.

The Python decoder matches **all 136064 bytes** of native output for the original T and both modified controls. Guards before/after the buffers remain intact. This independently checks decoding, not pixel development. The library decoder's recurrence uses previous decoded byte/key state; for an interior plaintext edit, its encoded difference affects bytes p and p+1. Omitting the ending boundary propagates corruption into subsequent plaintext.

The script applies that delta only to the two measured Natural spans. A full post-edit decode must equal the original decode with exactly those spans replaced; no unexplained plaintext changes are accepted. Uninterpreted tails remain byte-identical in the encoded file. No claim is made about every CMIO revision, checksums or other manufacturers' formats.

## Controls and verification

`scripts/epl9_workspace_bridge.py` creates a new ignored directory and two exclusive-create files:

- `epl9-cmio-neutral.ORF`: both Natural T banks replaced by the exact COLOR template; both matching P banks contain twelve `(H=0,S=0,L=0)` triplets.
- `epl9-cmio-desat-control.ORF`: same T banks; both P banks contain twelve `(H=0,S=-240,L=0)` triplets. This is an explicit diagnostic stimulus, not a measured slider value or a photographic recipe.

Both copies have the same length as the original. Differences are restricted to the two 72-byte P spans and the two 3028-byte T spans plus their encoded ending-boundary bytes. No pointers, IFD counts, RAW data, embedded JPEG or unrelated metadata are changed. Source CMIO T must match the exact stock E-PL9 payload, and original Natural P/T correspondence must pass before any output is created. The helper rejects already modified/unqualified inputs and output overwrite.

Independent checks on both real controls confirm unchanged decoded **3472×4640** mosaics using RawPy/LibRaw, in addition to exact RAW-strip byte equality and the native decoder comparison. This confirms that copies still parse as RAW; it does not establish acceptance by Workspace or firmware. There were no camera accesses, application binary changes or firmware writes.

Eight new synthetic tests cover wrong-model/revision rejection, truncated spans, duplicate tags, RAW/metadata overlap, correct encoded boundaries, deliberate boundary corruption and change containment. **136 workspace unit tests pass**; this includes independent work and is not a pixel-validation count.

## Next manual render and limits

Open `local/workspace-cmio-controls-20261104/` in Workspace, select both ORFs and export full-size Exif-TIFF into the same directory, retaining their distinct names. Keep Adjust Color disabled so an explicit UI adjustment does not intentionally replace the embedded coefficients. Initial thumbnails can remain identical because their embedded JPEGs were preserved; compare exported pixels rather than those thumbnails. If export still ignores the embedded fields, investigate fresh-development/reset behavior separately without claiming success from file creation alone.

Compare the two exported TIFFs for changed chroma, geometry, embedded profile and preserved detail. A successful controlled difference would qualify a desktop parameter path and permit numerical recipe trials. It would **not** execute the modified native Watercolor worklist or validate ISP timing, full native-job completion, live view, saved settings or a deployable patch. The CPU probe still stops before actual ISP execution as documented in [the real-RAW boundary report](epl9-real-raw-boundary.md).

```powershell
.\.venv\Scripts\python.exe scripts/epl9_workspace_bridge.py --raw <owner.orf> --reference-tiff <workspace-natural.tif> --out local/new-workspace-cmio-controls
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_epl9_workspace_bridge.py -v
```

Retained private results: `local/workspace-cmio-controls-20261104/manifest.json`, `independent-validation.json`, and `local/workspace-raw-20261104/native-cmio-decoder-check.json`. No Gold 200 or Portra 400 result is claimed at this checkpoint.
