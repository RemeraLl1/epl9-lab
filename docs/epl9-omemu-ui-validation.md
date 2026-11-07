# E-PL9 OM-Emu UI validation, 2026-11-07

## Result and scope

OM-Emu runs the exact E133/E-PL9 application and menu locally on Windows.
It exposed a real defect in our icon encoding: runs spanning rows passed the
external extraction decoder but were rejected by the emulated OSD engine.
The encoder now terminates each run at a scanline boundary. The drawing,
palette indices, descriptors, resource allocations and large ART example
pictures are unchanged.

The corrected G200/P400 icons are visible in the Picture Mode list, its
selected value in Shooting Menu 1, and the shooting-screen mode indicator.
These are screenshots of native E133 GUI execution with modeled devices,
not a host reconstruction of the menu. Watercolor I/II text labels remain
stock. No camera was accessed and no update container was created.

This closes part of the UI integration, not TruePic pixel processing or
installation readiness. The five film-processing hook sites were never
executed during this UI route; loading their bytes is not exercising them.
The [native owner report](epl9-native-owner-binding.md) still stops at
`6073eafa -> 9880014c` before hardware image output.

## Inputs and dependencies

Model: Olympus E-PL9; displayed body version **1.1** (owner report); main build
**1101**. Input identities:

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| Stock `OLY_E_133_1101_0000_0000.BIN` | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Stock main | 26214336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |
| Stock decoded OSD | 26214336 | `ee9a9c3ad1974dd212483ca7d012e51ae23083ce0119589a3b42996aa13ccf1e` |
| Existing kind-0x1000 main candidate | 26214336 | `29c6dceb4ecd14c0cf7ae5286aa595f48b9a548a2303986375d098fc34bb1585` |
| Corrected OSD candidate | 26214336 | `50141904c211fd16bc4c26b35cd52955f96a9e611ca062d84fe0169eeda21b3b` |

OM-Emu loads a **21456352-byte** OSD prefix: stock SHA-256
`d777456e3c2e41db6a55458cb8ec37d1a6589391f8103b3ec38be7cae59aaa43`,
corrected candidate `e492fa2ca4aa5143f7c207db22f1e417d4d2838f53daee5353b5a2a28ed144bc`.
All ten replacements lie inside this prefix.

- Upstream: [flatpanda/om-emu](https://github.com/flatpanda/om-emu/tree/147ca89c60b24774f3145c2813d79714e0f0b7b7),
  pinned commit `147ca89c60b24774f3145c2813d79714e0f0b7b7`, ignored checkout
  `references/om-emu`. Its tracked files are unchanged.
- Project-local Node **v26.13.0**, `local/omemu-node26/node.exe`.
  Official `win-x64/node.exe` SHA-256
  `14319838b3f355e0398c13569a90270bce4fc68f25189f58c59b03dadae0e6d5`,
  verified against the release's SHASUMS256.txt. The system Node was not replaced.
- `scripts/epl9_omemu_windows.mjs` replaces URL `.pathname` with
  `fileURLToPath` in pinned host modules in memory. It checks source hashes;
  it changes host path handling only, not CPU, devices or firmware. No
  external source is copied into this repository.
- `scripts/epl9_omemu_overlay.py` checks exact full component hashes,
  nonoverlapping declared regions and reconstruction of the complete
  candidate. It emits private memory overlays with original-byte guards:
  ten resource regions, six main regions, or all sixteen.

## Corrected encoding and screen mapping

The older candidate OSD SHA-256
`0f1605684aa282a59cf6de2840aeb7d8b8b493824fa7c324d1c9872e46971497`
is superseded. It is retained locally as a negative control.
The external decoder checked the total pixel extent but did not reject a run
crossing a row. OM-Emu's `emu/src/dev/engine.mjs` explicitly rejects
`column + run > width` with `BMP_TOKEN`. Merely extracting the intended
pixels was therefore insufficient.

| Resources | Corrected encoded bytes I / II | Existing allocation I / II | Native E133 screen observed |
| --- | --- | --- | --- |
| A076 / A077 | 231 / 232 | 268 / 272 | Picture Mode list; both selected and unselected |
| 4556 / 4557 | 418 / 418 | 548 / 570 | Shooting Menu 1, Picture Mode value |
| 4387 / 4388 | 527 / 524 | 1118 / 1140 | Shooting screen, upper right |
| 4420 / 4421 | 670 / 670 | 1742 / 1748 | Not reached in this run |
| 4458 / 4459 | 527 / 524 | 1118 / 1140 | Not reached in this run |

`epl9_icon_integration.py` again reparsed all **7490 bitmap descriptors and
240 inline symbols** using the pinned independent decoder. All non-target
pixels, descriptors and example pictures remain identical. Restoring the ten
original ranges reproduces the exact stock component. Two hand-derived test
vectors cover identical pixels on adjacent rows in modes 1 and 11.

The UI trace reads actual text draw arguments containing `@A076@` / `@A077@`
and native bitmap calls for 4556/4557 and 4387/4388. Selected menu icons
are black on the highlight and unselected/shooting icons are white. The
native calls include LUTs: one cannot infer the displayed colour from the
stored index alone. This is a scoped screen/colour observation, not a complete
mapping of every palette and UI state.

## Controls and limitations of the emulator

`epl9_omemu_ui.mjs` uses Player/PlaySession, deterministic button presses and
virtual waits. It records frame hashes, native GUI state names, target bitmap
draws, inline labels, engine diagnostics and passive hit counters for five
film hook sites **after bring-up**. It observes existing behavior without
replacing processing with successful-return stubs.

Important baseline findings:

- The generic `nav.mjs` harness fails its bring-up address checks on stock
  E133. Player's camera-application path is the working route used here.
- Turning the emulated mode dial to ART and waiting for its large example
  screen reaches `FMT_UNMODELLED` (value 1). The Picture Mode list works.
  No guessed compositor implementation or replacement photo was added.
- The generic palette dumper attempts an unmapped E133 read at
  `9c004400`; the runner records this diagnostic limitation. It does not
  substitute another model's palette banks.
- The engine emits a particular **stock BMP_LUT** error after S1 for a
  format-10 draw. The runner preserves this exact signature and refuses
  other errors. Comparison must also require the complete diagnostic
  history to match stock, including occurrence count.
- Checking only the current error counter is invalid: native menu drawing
  harvests and clears the diagnostic ring. The runner captures errors before
  every clear and at each frame boundary. Earlier exploratory runs which
  recorded only the current counter do not establish error-free drawing.
- `a15: on` is recorded per frame, including whether the compositor actually
  assumed a boundary. The kernel, camera devices and scene still have
  upstream model assumptions; this is not booting a physical camera from reset.

OM-Emu's [image-processing gap description](https://github.com/flatpanda/om-emu/blob/147ca89c60b24774f3145c2813d79714e0f0b7b7/docs/hle-gaps.md)
and `src/lab/scene.mjs` distinguish its synthetic scene/capture model from
the sensor/TruePic pixel pipeline. Neither a menu screenshot nor a synthetic
emulator JPEG calibrates Gold 200/Portra 400, exercises our native colour
hooks, or demonstrates a completed RAW conversion.

## Reproduction

All firmware bytes, overlays, screenshots and detailed logs remain in ignored
local directories. Stock firmware is provisioned from the already identified
local BIN, without contacting a camera:

```powershell
.\local\omemu-node26\node.exe --import ./scripts/epl9_omemu_windows.mjs references/om-emu/emu/bin/fetch-fw.mjs --model E133 --bin D:/EPL9Lab/firmware/OLY_E_133_1101_0000_0000.BIN
.\.venv\Scripts\python.exe scripts/epl9_icon_integration.py --out local/new-rowbounded-icons
```

The overlay packer currently pins the audited input paths
`local/epl9-embedded-icons-rowbounded-20261107` and
`local/epl9-kind1000-integration-final-20261105`; it will refuse a different
component hash. Reproduce its outputs in a new directory:

```powershell
.\.venv\Scripts\python.exe scripts/epl9_omemu_overlay.py --out local/new-omemu-overlays
$actions = @('s1','menu','right','down','ok') + (@('down') * 27) + @('ok','menu','menu','ok','down','ok','menu','menu')
.\local\omemu-node26\node.exe --max-old-space-size=6144 --import ./scripts/epl9_omemu_windows.mjs scripts/epl9_omemu_ui.mjs local/new-stock - @actions
.\local\omemu-node26\node.exe --max-old-space-size=6144 --import ./scripts/epl9_omemu_windows.mjs scripts/epl9_omemu_ui.mjs local/new-icons local/new-omemu-overlays/icons.json @actions
.\local\omemu-node26\node.exe --max-old-space-size=6144 --import ./scripts/epl9_omemu_windows.mjs scripts/epl9_omemu_ui.mjs local/new-combined local/new-omemu-overlays/combined.json @actions
.\.venv\Scripts\python.exe scripts/epl9_omemu_compare.py local/new-stock local/new-icons local/new-combined
```

The comparator requires **41 frames per run**, equal input actions and GUI
states, exact stock diagnostic histories, all six observed target resources,
pixel-identical icons-only/combined frames, and stock-to-candidate differences
confined to icon areas. These requirements deliberately do not claim execution
of the film processing hooks or output from TruePic.

## Retained validation results

The final controlled runs are `local/epl9-omemu-stock-final-20261107`,
`local/epl9-omemu-icons-final-20261107` and
`local/epl9-omemu-combined-final-20261107`. All three complete the same
41-frame route; the combined directory contains `comparison.json`.

- All 41 GUI states and button actions match stock.
- All 41 combined frames match the icons-only frames by raw hash and PNG pixels.
- Ten frames differ from stock, with every changed pixel inside the icon
  areas; the other 31 frames are identical.
- The complete engine diagnostic histories match stock exactly: three
  occurrences of the same pre-existing format-10 `BMP_LUT`, no added error.
- Both inline symbols and both pairs 4387/4388, 4556/4557 are observed.
- All five film-site counters remain zero. The observation begins after
  Player bring-up, and does not characterize unobserved startup execution.
- Twelve relevant Python unit tests pass (6 encoding, 2 resource replacement,
  4 overlay boundary tests); JavaScript syntax and Git whitespace checks pass.
- Negative control `local/epl9-omemu-old-icons-confirmed-20261107` refuses
  the older component at frame `031-down.png`: two `BMP_TOKEN` errors when
  A076/A077 first appear. The corrected component has neither error. This
  verifies that the diagnostic collection detects the original failure.

Reviewable private screenshots in the combined directory:
`032-down.png` (Gold selected with both recipe badges visible),
`037-down.png` (Portra selected), `033-ok.png` / `038-ok.png` (menu values),
and `034-menu.png` / `039-menu.png` (shooting indicators).

Remaining UI work: the two unobserved bitmap pairs, the ART dial/example screen
format gap, and any intended renaming of the stock Watercolor labels. Remaining
processing work is unchanged: real pixel output, calibrated recipe values and
the native ownership/concurrency/code-lifetime limits in the owner report.
