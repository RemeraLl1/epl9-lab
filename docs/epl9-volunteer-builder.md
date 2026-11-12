# E-PL9 local research builder / локальный сборщик

## What this does

The public source tree plus your **exact original Olympus E-PL9 build 1101**
file now reproduce the frozen `native-source-v1` Gold/Portra research pair.
There are no private module, RGB, OSD or reconstruction-manifest prerequisites.
The builder does not download firmware, run external programs, communicate with
a camera, copy to an SD card or install anything.

**This is a reproducible file builder, not an installation-qualified release.**
Physical installation, early-boot recovery and actual TruePic output have not
been established. A matching checksum is not proof that flashing is safe.

The existing Gold/Portra candidate is unchanged. This is not the older package
named `frozen-v3` or `private-color-v3`. It does not add SD recipes, Delete-button
remapping, OpenGate or gyro logging. The text labels still say Watercolor I/II.

## Requirements

- Python 3.10 or newer; Python 3.12.14/Linux was used for the full-size reproduction.
- Pillow 13.0.0, the pinned existing `requirements.txt` dependency.
- An original `OLY_E_133_1101_0000_0000.BIN` acquired lawfully from Olympus/OM
  or your own previously downloaded copy. Do not download a random patched BIN.
- Several hundred MB of free RAM and at least 110 MB free output space.

Only this exact original is accepted:

- 104552480 bytes
- SHA-256 `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`
- E-PL9 / IM008, downloaded build 1101 (body version 1.1 reported by the owner).

The repository does **not** redistribute Olympus firmware. There is deliberately
no automatic download URL guessed from an E-P7/PEN-F updater catalogue. If the
original cannot be obtained, do not use another model/build or disable its hash
check. See the [official OM support site](https://support.jp.omsystem.com/en/).

## Build

Download/clone this branch and open a terminal in the checkout root. Replace the
input path with your own path; do not put the original in the public Git tree.

```sh
python -m pip install -r requirements.txt
python epl9.py check-stock --stock "/path/to/OLY_E_133_1101_0000_0000.BIN"
python epl9.py build --stock "/path/to/OLY_E_133_1101_0000_0000.BIN"
```

On Windows, `py -3` may be used instead of `python`, for example:

```powershell
py -3 epl9.py build --stock "C:\Camera\OLY_E_133_1101_0000_0000.BIN"
```

The cross-platform Python implementation has no shell/toolchain dependency.
Windows execution has not been physically exercised in this pass.

By default outputs go to `local/volunteer-native-source-v1/`, ignored by Git.
Existing output directories are never overwritten. For a second build:

```sh
python epl9.py build --stock "/path/to/OLY_E_133_1101_0000_0000.BIN" --out local/volunteer-repeat
```

The two files, each 52428800 bytes, must be:

| File | SHA-256 |
| --- | --- |
| `Gold-Portra-v3-native-source-candidate.bin` | `10ac83e9beb9dd1bfd12aa6a021135706875d6ea245e58e20ec07fb917229421` |
| `Stock-1101-main-osd-restore.bin` | `10a7b949d1509ce627cb3c098c0a01a8ae5758fb2ce84b6c887e34b46e349387` |

`SHA256SUMS`, `READ-ME-FIRST.txt` and `manifest.json` accompany them. The manifest
is written last after reading back both output files. A folder without it is an
incomplete build and must not be used. If output fails, choose a new directory
for a retry; the builder does not remove or overwrite partial files.

**Do not rename these files to an assumed camera-card filename or flash them on
the strength of this guide.** Delivery filename, entry sequence, completion
indication and recovery on E-PL9 remain separately unqualified. Do not copy the
E-P7 `E142…` or PEN-F `E122…` procedure to E-PL9. The stock-return contains main
and OSD only, not calibration, settings or an independent bootloader rescue.

## How reproduction works

1. Verify complete stock size/SHA and the five-component inventory.
2. Decode main/OSD from the user's original and verify both exact hashes.
3. Derive the exact v3 RGB tables using the public v1 tone knots and the stock
   normal gamma table. The derived JSON matches the historical private input
   `915f5cfd…c6a1cb`; those private intermediary files are no longer needed.
4. Assemble the existing authored MN103 glue from the published assembly
   templates, HSL/tone definitions and WB recipe. Verify the exact frozen module
   and main, guard patch sites, and require audited updater/startup spans stock.
5. Draw the existing original G200/P400 badges and encode their RLE streams.
   Numeric layout facts and before/after digests identify ten bounded resources;
   no manufacturer icon bytes are distributed in the layout JSON.
6. Rebuild main/OSD containers using the original headers/trailers and new checksums.
   Reparse and compare the entire candidate and return files to the frozen hashes.
7. Write only to a new ignored directory, read both files back and issue a manifest.

The GUI screenshots and virtual-updater tests belong to the previous exact
candidate qualification; this builder does not rerun them or claim a camera test.
See [native-source report](epl9-native-source-v1-package.md) for those boundaries.

## Checks

```sh
python -m unittest discover -s scripts -p 'test_epl9_volunteer_builder.py' -v
```

The small suite runs without firmware. For the opt-in, full-size build test:

```sh
EPL9_STOCK_BIN=/path/to/OLY_E_133_1101_0000_0000.BIN python -m unittest discover -s scripts -p 'test_epl9_volunteer_builder.py' -v
```

A successful build establishes reproducibility of the file, not safety or video
support. The builder has no `--force`, hash bypass or different-model option.

## Reference work and attribution

[Caduceus E-P7](https://github.com/cakelesscoder/caduceus-ep7) inspired the local
stock-plus-authored-changes workflow. Its [firmware atlas](https://github.com/cakelesscoder/caduceus-ep7/blob/main/docs/ATLAS.md)
is a useful map, but E-P7 addresses, code-space ownership, hardware test evidence
and update instructions do not transfer to E-PL9. Its current code is Apache-2.0;
no Caduceus implementation is bundled or executed by this new builder.
The ten E-PL9 icon layout facts were cross-checked with the pinned Caduceus
`tools/osd_extract.py` at `7d42c1f258737b7196c6b17cec5d643b5080ece6`, already used
by the project's OSD research. End users do not need that external decoder.

This build does not copy an E-P7 release `edits.json`. It regenerates our existing
E-PL9 authored modifications from source and derives required stock tables from
the user's verified original. Both existing patchers keep firmware private;
this does not imply their hardware maturity is equal.

## Кратко по-русски

Оригинальный BIN остаётся у вас. Из него и опубликованного кода собираются ровно
те же экспериментальные Gold/Portra и штатный main/OSD для возврата. Приватные
промежуточные таблицы больше не нужны. Камера не подключается и не прошивается.

Сначала установите Python и зависимость, затем выполните команду `build` выше.
Готовые файлы будут в `local/volunteer-native-source-v1`. Это готовые **файлы для
исследования**, но подтверждённой инструкции физической установки на E-PL9 пока
нет. Не переносите имена файлов, сигналы и кнопочную процедуру с другой камеры.

## Verification on 2026-11-12

- Clean source-only clone + exact stock: candidate and stock-return both match
  the frozen full-file SHA-256 values above; no private intermediates present.
- Independent rebuild/review: same outputs, negative input/output controls pass.
- New focused suite: 12 tests passed with the exact-stock integration enabled.
- Legacy `test_epl9_*` discovery in the clean clone: 391 tests, two errors from
  missing unrelated research prerequisites (external OSD decoder and historical
  private-color-v3 fixture), 16 skips. This is **not** a full-suite pass.
- No physical camera, SD installation, Windows execution or video test performed.
