# E-PL9: extended color, icon embedding and deployment qualification

Follow-up: [WB math, early-load placement and callback consistency](epl9-wb-math-placement.md)
qualifies an offline early-load candidate, traverses the new math path under
explicit scalar contracts, and fixes matrix notification consistency. The late
matrix overlay and synthetic-only placement below describe the preceding pass.

## Outcome — 2026-11-04

Watercolor I and II remain the only replacement slots: Gold 200-inspired and
Portra 400-inspired. **Keep stock example photographs**, as explicitly requested
by the owner. Ten recipe icon resources have been embedded in a local decoded
OSD copy. The native module now optionally applies an early four-coefficient
bias, a bounded matrix delta and the separate six-axis block, alongside the
existing HSL, tone and independent curve selectors.

This is a larger, tested configuration implementation, **not a calibrated film
simulation or an installable firmware**. No camera or update media was accessed.
The module remains at synthetic address `68000000`; no installation container
was created. This follows the [late integration](epl9-late-film-integration.md),
[deep-color investigation](epl9-deep-color-controls.md) and
[icon resource audit](epl9-watercolor-icons.md).

## Exact inputs

Olympus PEN E-PL9, owner-reported body **1.1**, downloaded internal main build
**1101**. The downloaded component is not a dump of the installed camera.

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| `OLY_E_133_1101_0000_0000.BIN` | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Decoded main `00_0100_406e0020.decoded.bin` | 26214336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |
| Decoded OSD `01_0101_421e0020.decoded.bin` | 26214336 | `ee9a9c3ad1974dd212483ca7d012e51ae23083ce0119589a3b42996aa13ccf1e` |

The existing hash-pinned GNU reader independently checks every emitted
instruction, operand and branch target. All proprietary inputs and derived
binary outputs remain in ignored directories.

## Early gain bias: why the late color hook was insufficient

Native code copies four unsigned halfwords from job `+10406` to request `+1568`.
Observed producer stores are `607a4499..607a44b6`. The request copy finishes at
`6074f351`. The new optional jump at **`6074f352`** replaces exactly
`00 08 25 7e 0e`, then replays their effects before returning to `6074f357`.
This point follows a fresh copy; it does not repeatedly alter the source data.

The consumers are earlier than the late COLOR entry:

- `60799fdc` calls `607a3df6`, normalizing slots 0/1 by the smaller of slots 2/3.
- `6079a0b2` finds a common right shift and packs the four values as `[0,2,3,1]`.
- `6079a06a` also uses slots 2/3 in input configuration.

This supports a WB-gain interpretation with two green-like denominator values.
**Physical R/B assignment is still an inference**, not a measured camera result.
Changing these fields only inside `6079fb88` misses their earlier consumers.

`--wb-controls` accepts two bounded Q10 gain pairs in native order. The checked-in
`recipes/epl9-native-wb-trial-v1.json` uses `[1106,901]` and `[1060,963]`, rounded
from the previous photographic trials' relative factors. They are trial settings,
not conversions of Fuji WB-shift numbers. There is no claimed exact equivalence
between the ORF experiment and these internal coefficients.

The hook checks the original ART header and supported request kinds, leaves
other modes unchanged, bypasses a record containing zero, rounds and saturates
to unsigned 16 bits, and retains slots 2/3. Shift/add arithmetic avoids multiply,
divide, MDR/MDRQ, stack and loop-cache operations. D0/D2/A1 are restored to the
displaced instructions' values; D1 is overwritten by the following native load.
A0/A2/A3/D3/SP/MDR/MDRQ are checked unchanged. The original source record remains
unchanged in the connected runs.

**Fixture correction:** the historical `[640,480,640,480]` records at job
`+3730/+3738` were collectively described as crop data. A fresh native trace
shows the selected record feeds this color-gain producer. The fixture now names
that uncertainty and accepts explicit synthetic coefficients there. This does
not redefine the separately traced dimension records at `+3746/+3754`.

## Matrix and separate six-axis correction

`--color-controls` accepts a strict two-slot input. Matrix deltas modify the
native packed matrix at output `+80..97`, after native configuration. Each delta
is bounded to `[-16,16]`, and each row sums to zero: the native row sum and its
calibration-dependent base are retained. This is a linear channel-mixing
adjustment, not a second independent mechanism in addition to the matrix.
Two-pass overflow checking skips the whole adjustment if any signed cell would
overflow; no partially modified matrix is left behind.

The separate six-axis block uses native packer **`6079cd40`** and writes output
`+100..123`. Twelve signed halfwords live in read-only module gaps `+1c00` and
`+2c00`. Their physical hue labels, scales and useful ISP ranges remain open.
This block is distinct from the existing twelve-sector HSL configuration.

Both extensions run only for an accepted film configuration. Ordinary-mode
rebuild and warm-cache transitions are compared against independent configuration
oracles. There is no global last-recipe state or new owner allocation.

The combined validation uses **diagnostic** matrix, six-axis and RGB values.
They demonstrate that different values arrive at the correct native outputs;
they are not final Gold/Portra color parameters. Default builds preserve the
stock matrix, six-axis data and shared curve until explicit inputs are supplied.

## Embedded icons; unchanged photographs

`epl9_icon_integration.py` replaces bitmap pairs `4387/4388`, `4420/4421`,
`4458/4459`, `4556/4557`, and inline symbols `A076/A077` with original project
G200/P400 cassette artwork. Each encoded stream fits its original allocation.
No descriptor, address, length, shared Roman numeral or generic ART12 resource
is changed. The existing external decoder remains an ignored, pinned dependency.

The modified component is independently decoded again: **7490 bitmap
descriptors and 240 inline symbols** are checked. All non-target decoded pixels
are identical; reversing the ten replacements reconstructs the complete stock
component byte-for-byte. This also preserves the stock example pictures.
The palette preview was visually inspected; actual screen/palette bindings on
the camera still need confirmation.

Artifact: `local/epl9-embedded-icons-20261104-validated/`.
Modified decoded OSD SHA-256:
`0f1605684aa282a59cf6de2840aeb7d8b8b493824fa7c324d1c9872e46971497`.
The filename explicitly says `OSD-icons-OFFLINE-ONLY.decoded.bin`; it is not an
updater input.

## Placement, stack and synchronization

The combined module is **2039 code bytes / 15360 total bytes**, with four hooks.
Its diagnostic-RGB SHA-256 is
`02df46f487ed30d81eb91fa22d9e0110aafcacafc7d703ff6fc23b052a2b1cd0`.
The default module remains byte-identical to the previous 1171-byte-code build:
`938e2b72a65e0d953c9a50500779aeebfd1e5e679ac4a418634a7bf1027e4ebb`.

Fifteen aligned FF-padding candidates fit a 15360-byte module, but **none fits
wholly inside a known post-entry loaded section**. The large tail beginning
`617bd500` lies after section 9's end `617b9000`; the tempting `60600f00` span
crosses section 1's end `60601000`. Earlier candidates require an unresolved
pre-main mapping. Section bounds come from `604229df` / the `60405f94` records,
as executed in the [early-main audit](epl9-early-boot-recovery.md).
No candidate is approved. FF content and absence of an exact literal pointer
do not establish loading, execution or absence of computed references.

Measured native stack use from the explicit job-entry fixture:

| Request kind, either recipe | Historical COLOR path | Combined path | Increase |
| --- | ---: | ---: | ---: |
| `200` | 1696 B | 2248 B | 552 B |
| `100`, `40` | 1960 B | 2268 B | 308 B |

The wrapper's extra 88 bytes are **not the total increase**: active nested tone
processing also consumes stack. The early gain hook adds no stack. These are
measured paths, not the real task's complete worst case; actual task assignment,
stack allocation and headroom remain unqualified.

The traced late hook edits the request embedded at **job +10440**, not the job
header itself. Both modeled ISP locks (`607a17b7`, `607a1841`) are still unheld
during the observed temporary edits. This does not prove a race, but those locks
cannot justify excluding one. Per-job ownership/reentrancy and other readers
must be established before approving the temporary mutation strategy. Owner
objects remain read-only; restoration alone is not a concurrency proof.

Observer correction: initial exploratory audits wrapped a Memory object later
replaced by the resource models. Their missing access observations were invalid.
The final audit wraps CPU operand reads/writes and has a regression test that
replaces Memory after attachment. Use `local/epl9-deployment-final-20261104/`,
not earlier empty-access exploratory results.

## Validation scope and the remaining software dependency

`local/epl9-film-integration-final-20261104/validation.json` records:

| Check | Result |
| --- | --- |
| Full native frame configurations | 32 |
| Original-key attached-object comparisons | 24 |
| Warm-cache / mode-exit frames | 9 |
| Cold passthrough / excluded states | 12 |
| Whole-job schedule regressions | 120 |
| Effect-flag cases | 1050 |
| Native matrix overflow boundary cases | 36 |
| Native early-gain boundary/passthrough cases | 220 |
| Connected jobs with explicit nonzero coefficients | 12 |

The final workspace test suite passes **221 tests**, including other chats'
existing tests. Stock firmware inputs remain unchanged.

The connected fixture uses `[2048,1536,1024,1056]`. Native consumers read the
adjusted values, not values inserted into their output by Python. Both recipes
reach the established TruePic boundary at `6073eafa`, writing to `9880014c`.
There are no produced pixels, hardware completion events or successful pending
request cleanup. Full pixel processing remains unverified.

The wider coefficient-domain probe deliberately retains another unresolved
path: equal `[1024,1024,1024,1024]` and historical `[640,480,640,480]` inputs,
with either recipe's gain bias, reach native `607a46ce -> 604bbbeb` before
late configuration completes. The latter begins with bytes `f9 e0 40`, which
the generic reader labels `fadd`; its role/ABI in this processor remains to be
qualified. No success stub is installed. A suspended emulator leaves temporary
request edits in its stopped image; that is not evidence of restoration after
a completed call. See `local/epl9-wb-domain-20261104/wb-dependencies.json`.

Thus the 12 passing connected cases are **not unrestricted input coverage**.
Existing field restoration and cache checks continue to describe the native
paths that actually return. This new dependency and the hardware boundary are
different limitations.

## Photographic target and next completion criteria

Initial reference recipes are Fuji X Weekly's authored
[X-T30 Gold 200](https://fujixweekly.com/2020/04/16/my-fujifilm-x-t30-kodak-gold-200-film-simulation-recipe/)
and
[X100V Portra 400 v2](https://fujixweekly.com/2020/12/30/fujifilm-x100v-film-simulation-recipe-kodak-portra-400-v2/).
Both start from Classic Chrome. Gold uses daylight WB, a warm shift, stronger
color and grain. Portra v2 combines a fixed WB/shift with DR400, a softer shadow
setting, color-chrome effects, reduced clarity and grain. These are distinct
camera pipelines; their numeric controls cannot be copied into Olympus fields.

There is no measured Classic Chrome-equivalent base here. Independent curves,
HSL, matrix and six-axis controls provide additional fitting freedom, but do
not by themselves reproduce Fuji's nonlinear hue response, dynamic-range
handling, texture, grain or sharpening. Grain and clarity equivalents are not
implemented. The latest actual photographic outputs remain the Workspace v2
trials; this pass produces no new Gold/Portra photographs.

Completion therefore requires (1) resolving the new arithmetic dependency and
qualifying channel/axis domains, (2) fitting the two complete looks against
representative skin, neutrals, saturated colors and tonal ramps, (3) qualifying
loading, stack and ownership before constructing an update, and (4) observing
camera-side rendering, repeated frames, mode exit and completion in the agreed
installation phase. Existing updater/recovery findings are retained; this
report does not reopen those decisions or turn local tests into camera proof.

Reproduction commands, with new ignored output directories:

```powershell
.\.venv\Scripts\python.exe scripts/epl9_icon_integration.py --out local/new-icons
.\.venv\Scripts\python.exe scripts/epl9_film_late_probe.py --out local/new-color-validation --color-controls local/diagnostic-controls.json --wb-controls recipes/epl9-native-wb-trial-v1.json --diagnostic-rgb
.\.venv\Scripts\python.exe scripts/epl9_deployment_probe.py --out local/new-deployment-audit --color-controls local/diagnostic-controls.json --wb-controls recipes/epl9-native-wb-trial-v1.json
.\.venv\Scripts\python.exe scripts/epl9_wb_dependency_probe.py --out local/new-wb-domain --wb-controls recipes/epl9-native-wb-trial-v1.json
```
