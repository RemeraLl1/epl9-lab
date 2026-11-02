# E-PL9 ART example photographs

## Accepted scope and current evidence

The owner includes the large example pictures in ART selection, in addition to the [small icons and inline symbols](epl9-watercolor-icons.md). Watercolor I's example must eventually represent Gold 200 and Watercolor II's Portra 400, preserving the existing menu and unrelated modes.

The artwork choice remains open: film cards/icons, owner photographs rendered with the completed recipes, or representative existing photographs. Owner images rendered by our actual recipes would demonstrate their result most directly. No final assets have been selected or generated. Existing firmware examples are research inputs, not newly rendered Gold/Portra output.

## Exact input and extraction

Olympus E-PL9, displayed body version reported as **1.1**, downloaded main build **1101**. Container `OLY_E_133_1101_0000_0000.BIN`: 104552480 bytes, SHA-256 `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`.

Picture component kind `0x102`, component-header version `0100`: decoded file `04_0102_468e0020.decoded.bin`, 13107136 bytes, SHA-256 `a0d6a08e79f8a1c731959695ada1f26d52ea1e1c0fc9f234618f795ced061c0f`. Component-header version is not the camera's displayed version. Directory addresses are interpreted relative to `0x468e0020`, not asserted as runtime RAM addresses.

The first payload pointer `0x468e3000` gives a 766-slot directory of 16-byte records, interpreted as pointer, allocated bytes, zero, zero. Zero-length placeholders may retain a pointer. Bounds and allocation overlap are checked. There are **221 nonempty resources: 220 JPEGs and one ICO**. All JPEGs fully decode with Pillow; the ICO's selected image also decodes. Resource 594 is the ICO, which is why neither a raw JPEG-signature count nor “every resource is a JPEG” is correct.

JPEG extraction walks marker lengths and entropy escapes to the outer EOI, ignoring embedded thumbnail EOIs inside metadata. Four synthetic parser tests cover embedded thumbnails, multiple scans, truncation and directory bounds/empty slots. Extracted photographs, contact sheets and payload hashes stay ignored under `local/art-samples-v3/`.

Two visually identified candidates show the same sunflowers in distinct watercolor-like treatments:

| Directory ID | Payload offset | Allocated bytes | JPEG bytes | Dimensions | JPEG SHA-256 |
| --- | --- | ---: | ---: | --- | --- |
| 360 (`0x168`) | `0x20a1e0` | 52736 | 52463 | 256×192 | `17a0e6a0650a0abf022cd90743fee5b76898d6a208bfb231257ed3bd7e58920b` |
| 361 (`0x169`) | `0x216fe0` | 39424 | 39363 | 256×192 | `96d49d5ad1f3505f09868a1b368f33e607f3d442aada424853dbedb1dd0db513` |

These are **visual candidates**, not proven Watercolor I/II runtime bindings. The local files are `p360.jpg` and `p361.jpg`; their order must not yet be treated as a patch contract.

## Binding caveat discovered during the search

Main-image identity: 26214336 bytes, SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`, candidate base `0x60400020`.

A nearby sample-image UI table begins at `0x615e716c`. In it, Watercolor-associated UI values `0x1301` and `0x1302` occur at `0x615e726c` and `0x615e7274`, but their paired values are **399 and 400**, not 360 and 361. Those directory slots currently have zero allocation. The function fragment at `0x61213379..0x612133a6` indexes eight-byte rows, compares the key and copies the paired 16-bit value; full caller/resource resolution is not traced.

Other table entries align with visible ART example images, but that is not enough to infer a fallback, remapping, or the active screen variant. Do not patch empty slots 399/400 or overwrite sunflower candidates merely from visual similarity. Trace the actual ART-selection screen's resource resolution and compare the screen on the camera before choosing the final replacement IDs. The small icon bindings from the earlier audit do not automatically establish these photo bindings.

## Replacement plan and reproduction

Keep the examples as ordinary image resources in the existing layout. A film card can be encoded in the same image format; changing the resource's content need not imply redesigning the menu. Once recipes render correctly, examples can instead be generated from owner images. An existing photograph would need an appropriate reuse source and must not be represented as an output of the uncalibrated recipe.

The replacement writer is not implemented: allocation size, encoding, pointer adjustment if needed, component/container integrity and actual screen selection still require validation. Current extraction never rewrites firmware.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_epl9_picture_audit.py -v
.\.venv\Scripts\python.exe scripts/epl9_picture_audit.py --out local/new-art-picture-audit
```

The runner verifies the exact picture component before extraction and requires a new ignored output directory. Firmware and extracted vendor photographs are not published in the repository.
