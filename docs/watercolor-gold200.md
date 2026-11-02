# Watercolor I → Kodak Gold 200; Watercolor II → Kodak Portra 400

The owner selected **Watercolor I → Kodak Gold 200** and subsequently added **Watercolor II → Kodak Portra 400** on 2026-11-02. The second decision supersedes the earlier requirement to preserve Watercolor II. Preserve the other ART modes. These are accepted implementation targets, not working patches or calibrated film recipes.

## Image target

Start with a Gold 200-inspired daylight rendering: warm color, recognizable skin tones, detailed foliage, natural edges and controlled highlights. Tune color and tone before investigating grain. These are initial design choices, not measured film equivalence or calibrated firmware values.

Portra 400 is the accepted second recipe name. Its numerical color/tone parameters have not been chosen; keep it a separate recipe from Gold 200. Neither recipe implies forcing the camera ISO to the number in the film name.

[Kodak's E-7022 technical data](https://www.kodakprofessional.com/sites/default/files/wysiwyg/pro/resources/E7022%20Gold%20tech%20sheet.pdf) describes a daylight-balanced color negative film with fine grain, sharpness and color saturation. Its film response curves are not a ready-made digital-camera LUT; a developed/scanned reference and its rendering conditions are needed for a meaningful match. The name “200” does not mean forcing the camera to ISO 200 at all times.

The [E-PL9 manual](https://learnandsupport.getolympus.com/sites/default/files/media/files/2018/04/E-PL9_MANUAL_EN.pdf), printed page 48, describes Watercolor I/II as lightening dark regions and softening contours. Replacing only its color table would not establish that this spatial processing has been removed.

## Investigation order

1. Locate this exact E-PL9 build's Watercolor identifiers, type-I/type-II distinction and processing dispatch.
2. Trace live-view and still-JPEG routes independently. Find where Watercolor's native passes are selected and how normal color processing could replace them for both types, retaining the I/II distinction for recipe selection.
3. Establish a neutral, detailed replacement before introducing the film recipe. Ensure shared parameters are not changed globally.
4. Tune a first Gold 200 candidate against fixed-exposure, fixed-white-balance RAW/JPEG samples covering skin, red/yellow objects, foliage, blue sky, gray and highlights.
5. Validate saved settings, live view, captured JPEGs, both replacement recipes and unaffected ART modes. Rename the slots after the processing route is established.

No camera writes or flashing are part of the current offline investigation.

## Recipe icons and existing interface

The owner explicitly requested embedded film-recipe icons on 2026-11-02. Gold 200 and Portra 400 should replace the corresponding Watercolor artwork in the existing selection UI, with the same treatment for future explicitly accepted recipes. Preserve the surrounding menus, navigation, controls and unrelated behavior. This is a focused resource/selection change, not an interface redesign.

The [icon-resource audit](epl9-watercolor-icons.md) now identifies separate I/II bitmaps in four pairs, corresponding inline symbols and matched label tables in this E-PL9. All 5417 bitmap streams decode. Some other contexts still use generic ART12 artwork; complete screen/palette selection remains to be traced. Original resources stay local; eventual replacement artwork should be project-authored. No replacement assets or modified firmware have been produced yet.

The owner will copy original test media from the SD card separately when required. Camera USB Storage troubleshooting does not block this investigation; no sample transfer has yet been verified by this project.

The owner subsequently included the large photographs shown as ART examples. These are separate from the small badges and inline symbols. [The picture audit](epl9-art-example-pictures.md) extracts the picture bank and identifies a visual Watercolor pair, with exact screen bindings still unresolved. Final examples may be film cards, owner images rendered through the eventual recipes, or suitable existing photographs. The choice has not been made; no stock or third-party photo is being presented as our recipe output.

## Reference material

The external E-P7 project at commit `7d42c1f258737b7196c6b17cec5d643b5080ece6` documents a Water Color base ID `0x78` and type-I key `0x01010078`. It also contains a `lib2_gold` recipe. Both are search/comparison references, not E-PL9 implementation evidence or calibrated Kodak values:

- [E-P7 identifier research](https://github.com/cakelesscoder/caduceus-ep7/blob/7d42c1f258737b7196c6b17cec5d643b5080ece6/docs/BLOOM_HALATION.md).
- [E-P7 recipe source](https://github.com/cakelesscoder/caduceus-ep7/blob/7d42c1f258737b7196c6b17cec5d643b5080ece6/sim/recipes/library_v2.json).

Use only the exact stock E-PL9 1.1/build 1101 input identified in [initial findings](epl9-1.1-initial-findings.md). Raw firmware, disassembly and local reports remain ignored.

## First E-PL9 code observations (2026-11-02)

Input: E-PL9 1.1, main internal build `1101`; stock container `104552480` bytes, SHA-256 `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`. Decoded main: `26214336` bytes, SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.

The [local GNU-based reader](mn103-tooling.md) now disassembles the relevant windows. Address calculations use candidate base `0x60400020`, consistent with the startup sequence: load `0x604000f9` into `a0`, then jump through `a0` to the initialization prologue. This is an offline mapping, not a camera memory measurement.

The Watercolor names below still come from the E-P7 reference. The E-PL9 observations establish matching keys, separate branches and parameter addresses; the user-facing mode-to-key mapping has not yet been measured on this camera.

| Observation in exact E-PL9 main | Evidence |
| --- | --- |
| Separate key comparisons and branches | At file `0x393461`, `cmp 0x01010078,d0` leads to candidate address `0x60793584`; the following type-II comparison at `0x39346c` leads to `0x607936f7`. |
| A shared routine for both keys | Key/target pairs at file `0x5009d8` and `0x5009e0` both contain target `0x6079cfc5`. That routine selects two data addresses, `0x608e0eae` and `0x608e0eba`. Its complete processing role is not yet established. |
| Separate parameter selections elsewhere | Key/target pairs at file `0x500f70` and `0x500f78` contain targets `0x6079e395` and `0x6079e39e`. These load `0x609000c4` and `0x609000f8` respectively, then jump to the same continuation. |
| Separate combiner parameter candidates | The type-II comparison at candidate address `0x6078f4ac` selects `0x608f4186` when equal and `0x608f417c` otherwise. At decoded offsets `0x4f4166` and `0x4f415c`, the five signed 16-bit values are `(0,1024,0,255,0)` and `(-10,1066,-10,245,10)`. These match the E-P7 reference's parameter tuples; the default branch is not proven exclusive to type I. |
| Native consumer of the shared COLOR table | Code compares the assembled mode key to `11` at candidate address `0x6079ec3b`. On equality it loads table `0x608ee360` and calls `0x6079e9e2`. The callee reads 28-byte sector records in two groups of six and installs associated LUT pointers. |

The last observation advances the earlier literal-only finding: the shared table has a native code consumer. It still does **not** prove that a user-selectable COLOR mode or a safe Watercolor-to-COLOR replacement exists. The custom instructions shown by GNU as `udf00` have not been emulated here.

Practical consequence: changing a shared table could affect other consumers and would not provide two independent recipes. Follow-up [routing analysis](epl9-art-routing.md) now identifies the common Watercolor worklist, request-header propagation, and separate ordinary/late color paths. It establishes a concrete replacement design to test offline; live-view/capture coverage and a functioning replacement remain unverified. No patch locations are approved by these observations.

## Reproduce

After building the local reader as described in [tooling](mn103-tooling.md):

```powershell
.\.venv\Scripts\python.exe .\scripts\epl9_art_probe.py --out .\local\new-watercolor-audit
```

The probe rejects a different main-image hash, writes into a new ignored local directory, records key occurrences and parameter pairs, and checks nine relevant decoded instructions. The initial run is stored locally under `local/watercolor-gold200-20261102/`. It reads no camera devices and creates no modified firmware.
