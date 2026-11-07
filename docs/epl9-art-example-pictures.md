# E-PL9 ART example photographs

## Accepted scope and current evidence

**Current first-integration scope: keep the existing large ART example photographs unchanged.** This later owner instruction supersedes the original request to replace them. Only the two film replacements and small icons are being prepared for the first package; see [readiness](first-integration-readiness.md). The extraction, binding caveats and external-photo shortlist below preserve the earlier research and are not a current picture-component patch plan.

For the earlier replacement proposal, the artwork choice remained open: film cards/icons, owner photographs rendered with the completed recipes, or representative existing photographs. Owner images rendered by our actual recipes would demonstrate their result most directly. No final assets have been selected or generated. Existing firmware examples are research inputs, not newly rendered Gold/Portra output.

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

## Digital-recipe photo shortlist, 2026-11-02

The owner explicitly selected digital recipe examples. Both first choices below were visually inspected in the browser. The author identifies them as camera-made JPEGs using the named recipe; neither is an E-PL9 image or a prediction of our final rendering. Camera-specific settings should not be copied numerically into Olympus tables.

| Slot | First choice and author source | Why this frame |
| --- | --- | --- |
| Gold 200 | Ritchie Roesch, **Boy in Spring**, Fujifilm X-T30, [Kodak Gold 200 recipe](https://fujixweekly.com/2020/04/16/my-fujifilm-x-t30-kodak-gold-200-film-simulation-recipe/) | Daylight portrait with blossoms, blue sky, red scooter grips and green grass. Broad color range; central subject remains legible at menu size. |
| Portra 400 | Ritchie Roesch, **Julien Jarry with RED Camera**, Fujifilm X100V, [Kodak Portra 400 v2 recipe](https://fujixweekly.com/2020/12/30/fujifilm-x100v-film-simulation-recipe-kodak-portra-400-v2/) | Adult environmental portrait with muted sky, beige vegetation and skin tones. Prefer this over a sunset for a portrait-oriented recipe. |

**Sage Sunset**, from the same Portra article, was also inspected: striking orange clouds and dark vegetation, but the light dominates its appearance and gives little information about skin or neutral colors. Keep it as an alternative, not the primary comparison.

The first choices are approximately 3:2; the existing candidate resources are 4:3. A future 4:3 crop should retain the central subject in Gold and shift slightly right in Portra to retain both the person and camera. This is a visual proposal, not an exported or validated crop. Recompress and check the actual 256×192 result against the verified target allocation only after resolving the runtime photo binding.

Direct media links, provenance and review status are recorded in [the source manifest](../assets/film-menu/photo-sources.json). Only links and metadata are stored. No open redistribution permission was identified on these author pages; embedding the photos in a public asset package still needs an appropriate permission or replacement source. No request has been sent to the author.
