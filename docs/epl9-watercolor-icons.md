# E-PL9 Watercolor icon resources

## Result, 2026-11-02

The exact E-PL9 image contains **separate `ART 12 I` and `ART 12 II` bitmap resources**, in several sizes and color variants. They were decoded and visually inspected. Matched value/label tables associate the two variants with the English Watercolor I/II strings. Separate Gold 200 and Portra 400 artwork can therefore target existing distinct resource slots; a new menu layout is not needed for those slots.

This establishes existing resource separation, not a tested firmware modification. Some other UI contexts use a generic `ART 12` badge, and inline symbols are a separate resource class. All screens' draw paths and active palettes have not been traced.

## Inputs and provenance

Olympus E-PL9, owner-reported displayed version **1.1**, downloaded main build **1101**. Stock container `OLY_E_133_1101_0000_0000.BIN`: **104552480** bytes, SHA-256 `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`.

| Decoded component | Bytes | SHA-256 |
| --- | ---: | --- |
| Main `0x0100`, analysis base `0x60400020` | 26214336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |
| OSD `0x0101`, container payload address `0x421e0020`, component header version `0x0100` | 26214336 | `ee9a9c3ad1974dd212483ca7d012e51ae23083ce0119589a3b42996aa13ccf1e` |

Parsing reuses the pinned external [OSD decoder](https://github.com/cakelesscoder/caduceus-ep7/blob/7d42c1f258737b7196c6b17cec5d643b5080ece6/tools/osd_extract.py), SHA-256 `16e310d988012e56091ce883ab6ab95d5f1eaf3abb00a0aac733a54edb99a9b8`. Its [format research](https://github.com/cakelesscoder/caduceus-ep7/blob/7d42c1f258737b7196c6b17cec5d643b5080ece6/docs/OSD.md) supplies a hypothesis to validate against E-PL9. Our adapter pins the external file, sets the exact E-PL9 component addresses/hashes, retains hash checking, and validates the resulting descriptors and pixels. External source remains in ignored `references/`; it is not republished here.

## E-PL9 structure actually checked

- 70 populated resource records. Resource 0: decoded offset `0x7e0`, size `0x49ac00`; resource 69: decoded offset `0xcaf7e0`, size `0x7c6e00`.
- Structurally solved bank bases `0xa3091000` and `0xa3611000`. These coincidentally match the reference model; they were solved from E-PL9 pointers and dimensions, not assumed from that match.
- 7490 bitmap-table entries: **5417 decoded images, 2072 placeholders, one null**. No bitmap decode failures. All 240 inline symbols also decode.
- Image streams: 4876 mode-11 (8-bit palette indices), 541 mode-10 (4-bit palette indices). All target bitmaps below use mode 11.
- Mode 11 uses a 4-byte dimensions/mode header, then 12-bit run/index tokens in 64-bit groups, five tokens per group. The decoder verifies exact pixel count, dimensions and zero padding. This is not PNG/JPEG storage.
- English resource 8: 3506 strings, solved base `0xa407f540`.
- Preview palette candidate `0x6151b980` comes from this E-PL9 main. Its on-camera screen/layer selection is unverified; raw palette indices are retained in exported PNGs.

## Separate variant assets

Offsets below are relative to the **decoded OSD component**, not the complete update file or executable main. Encoded bytes are the current stream length, not guaranteed spare allocation capacity.

| I / II bitmap IDs | Dimensions | Visual appearance with candidate palette | I payload offset / bytes | II payload offset / bytes |
| --- | --- | --- | --- | --- |
| 4387 / 4388 | 50×38 | White `ART 12 I` / `II` | `0x158024` / 1118 | `0x15849c` / 1140 |
| 4420 / 4421 | 64×48 | Yellow-green variants | `0x105cdb8` / 1742 | `0x105d4a0` / 1748 |
| 4458 / 4459 | 50×38 | Another white set; pixel hashes differ from 4387/4388 | `0x15eb24` / 1118 | `0x15ef9c` / 1140 |
| 4556 / 4557 | 44×32 | Smaller pale/gray variants | `0x106d508` / 548 | `0x106d744` / 570 |

The audit records each descriptor offset, encoded/pixel SHA-256, format and bank. The four pairs were viewed in the extracted contact sheet, `local/osd-audit-20261102-v2/watercolor-icons.png`.

## Association with Watercolor selection

These paired main-image rows provide a concrete connection beyond visually reading ART numbers:

| Main row addresses | Value → label mapping |
| --- | --- |
| `0x6157192c` / `0x61571938` | `0x1301` / `0x1302`, kind 3, bitmap 4387 / 4388 |
| `0x61571f08` / `0x61571f14` | Same values, kind 3, bitmap 4420 / 4421 |
| `0x615725c8` / `0x615725d4` | Same values, kind 4, string 2694 / 2695 |
| `0x615731bc` / `0x615731c8` | `0x10013` / `0x20013`, kind 3, bitmap 4458 / 4459 |
| `0x61572eec` / `0x61572ef8` | Same values, kind 4, string 1800 (`Watercolor`) |
| `0x61583fe8` / `0x61583ff4` | `0x1301` / `0x1302`, kind 3, bitmap 4556 / 4557 |

English 2694 is `Watercolor@A054@`; 2695 is `Watercolor@A055@`. Decoded symbols A054/A055 show Roman I/II. The matched table records, label contents and rendered bitmap text support the mapping. This is not yet an executed E-PL9 label-renderer trace or a hardware measurement. UI values `0x1301/0x1302` are distinct from the processing keys `0x01010078/0x01020078`; their conversion has not yet been traced.

## Other artwork to account for

- Generic `ART 12` bitmaps: 688 (50×38), 689 (64×48), 1024 (50×38), 4573 (44×32). They do not distinguish recipes by themselves.
- Inline symbols: **A076/A077** are distinct 44×32 `ART 12 I/II` badges. They occur in English strings 2729/2730. Payload offsets are `0x48284c` (268 bytes) and `0x482964` (272 bytes); these symbol streams use the symbol decoder, not bitmap mode 11.
- **A062** is the generic inline `ART 12` badge. **A054/A055** are shared Roman numerals; replacing them globally would alter other modes, so leave these shared numeral resources alone.
- Numeric UI values are not globally unique. A naive search also matched bitmap 5127, which visually reads `Magyar` (language menu), and IDs 2685/2700 which are placeholders. These are explicitly excluded from the target icon set. A raw numeric hit is not sufficient evidence for a replacement.

## Replacement implications

Create project-authored Gold 200/Portra 400 artwork in the existing dimensions, including the applicable small and selected-state variants. Encode it with the correct stream format, preserve descriptor and table contracts, and check whether it fits each original allocation before considering resource relocation. Names and inline symbols also need deliberate coverage to avoid mixed old/new labels.

Preserve menu structure, navigation and unrelated ART assets. Generic badges require a screen-specific decision after tracing their users; the existence of variant-specific slots does not guarantee every screen already distinguishes variants.

The initial audit produced no replacement assets or firmware writes. Standalone candidate artwork was subsequently added below. All original artwork and extracted catalogs remain ignored local files.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_epl9_osd_audit.py -v
.\.venv\Scripts\python.exe scripts/epl9_osd_audit.py --out local/new-osd-audit
```

The **five synthetic tests** cover a known tiny stream, malformed/truncated/overrun/padded streams, mismatched dimensions, input/decoder identity rejection and invalid label input. The exact-image audit independently checks all bitmap/symbol decodes and 12 target label rows. Retained output: `local/osd-audit-20261102-v2/audit.json`. These checks establish extraction and associations, not patch bootability or rendering on the camera.

## Standalone replacement artwork, 2026-11-02

Two original pixel-grid cassette badges now distinguish **G200** and **P400**. Their geometry and tiny glyphs were authored for this project; no vendor artwork or third-party SVG was copied. Reviewable sources: [G200.svg](../assets/film-menu/G200.svg), [P400.svg](../assets/film-menu/P400.svg). These are draft icons, not installed changes or an owner-approved final design.

An external alternative is [Camera film roll by donchico](https://commons.wikimedia.org/wiki/File:Camera_film_roll.svg), listed as CC0 on Commons. The project badges were chosen for their simpler shape, distinct labels and fit in the existing 44×32 slots; the external file was not imported.

`scripts/epl9_film_icons.py` creates monochrome candidates in each native size, encodes the actual RLE formats, pads to the original allocation and decodes with the pinned independent decoder. All 10 outputs reconstruct exactly and fit without changing resource pointers:

| Resources | Size / mode | New bytes, G200 / P400 | Existing allocation |
| --- | --- | --- | --- |
| 4387 / 4388 | 50×38 / 11 | 484 / 481 | 1118 / 1140 |
| 4420 / 4421 | 64×48 / 11 | 634 / 634 | 1742 / 1748 |
| 4458 / 4459 | 50×38 / 11 | 484 / 481 | 1118 / 1140 |
| 4556 / 4557 | 44×32 / 11 | 377 / 377 | 548 / 570 |
| A076 / A077 | 44×32 / 1 | 230 / 231 | 268 / 272 |

The local preview uses candidate palette `0x6151b980`: index 4 for white, 22 for the small gray badges and 103 for selected yellow-green badges; inline symbols use level 3. Runtime palette selection is still unverified. The artwork was visually reviewed at native sizes. Shared Roman numerals A054/A055, generic ART12 resources, menu strings and the firmware remain untouched.

Reproduce with `python scripts/epl9_film_icons.py --out local/new-film-icons`. Retained report and preview: `local/film-icons-20261102-v1/results.json` and `film-icons.png`. Outputs are standalone RLE candidates; fit/round-trip success does not prove that the camera accepts a rebuilt component or container.
