# E-PL9: explicit native v3 input binding

## Result, 2026-11-08

The late native-module builder now has a complete, explicitly hash-pinned
input path for the two frozen recipe slots. This closes a source-level
integration gap: previously `build_late_module` always obtained HSL from
public v0 and contrast/H/S/M from public v2, even when separate RGB, matrix
or WB documents were supplied. Those older defaults remain available for
historical reproduction. They are not final v3 inputs.

The new path transports supplied HSL into the emitted native tables, supplied
contrast/H/S/M into native instructions, RGB into its three native-order
tables, and optional native WB/matrix/six-axis settings into the existing
late-hook implementations. Different midtone biases for Gold and Portra
now generate a native recipe-selection branch instead of inheriting the
historical common `+1`. User controls retain the existing bounded addition
and clamp behavior. Original request restoration and ART-kind gates are
unchanged.

**No final v3 numerical definition is supplied or reconstructed by this
change.** There is no installable package, new photographic rendering,
qualified exact-image run or camera result. Input transport is not visual
recipe validation. The owner still reviews recipe appearance separately.

## Strict transport contract

`scripts/epl9_native_recipe_inputs.py` defines
`epl9-native-film-inputs-v1`. This is an integration transport schema, not a
new version of either film recipe. It requires these root fields:

- `schema`: exactly `epl9-native-film-inputs-v1`.
- `model`: exactly `Olympus E-PL9`; `build`: exactly the string `1101`.
- `recipe_revision`: exactly `v3`.
- `source_definition_sha256`: SHA-256 of the actual originating frozen
  definition. Merely recording this hash does not independently verify its
  contents, the conversion or owner acceptance.
- `recipes`: exactly two rows. Order is normalized by Watercolor key, never
  by array position alone.

Both rows must explicitly provide every field below. Missing or extra
fields, duplicate JSON keys, other slot identities and out-of-range values
are rejected. No numerical field is inferred from v0/v1/v2.

| Field | Required input |
| --- | --- |
| `name`, `watercolor_key` | `gold200-v3` / `0x01010078`; `portra400-v3` / `0x01020078` |
| `native_hsl` | Twelve physical records, each three integers; existing qualified bounds H ±1000, S ±240, L ±100 |
| `picture_mode_contrast` | Integer -2..2 |
| `tone_level` | Explicit integer `highlights`, `midtones`, `shadows`, each -7..7 |
| `native_rgb_curves` | Explicit `stock`, or three native-order arrays of 256 monotone integer 12-bit entries each |
| `native_wb_gain_q10` | Explicit `stock`, or two native-order integer Q10 gains in 512..2048 |
| `matrix_delta` | Explicit null, or the existing nine bounded zero-row-sum delta coefficients |
| `six_axis` | Explicit null, or the existing twelve signed native halfwords |

`stock` explicitly preserves that input component. If only one recipe
requests native WB, the other receives an identity Q10 pair in the shared
hook. If both request stock, no WB hook is emitted. Similarly, null matrix
and six-axis settings for both recipes emit no extension hook. These are
explicit policies, not substituted photographic values.

Native curve/channel order and physical WB channel names remain unverified.
The loader does not silently translate desktop red/blue permille values,
RGB/HSV coordinates, tone knots or arbitrary photographic LUTs into native
coefficients. Obtain the originating native inputs and document any required
translation separately. If v3 needs a different tone/curve representation or
values outside the current qualified bounds, stop and qualify that extension
rather than clipping or fabricating the missing data.

The caller must supply the exact-byte SHA-256 separately from the file.
Immutable input bytes are retained; decoded views cannot mutate the pinned
document. The manifest records the input and source-definition identities,
emitted HSL/RGB table hashes, per-slot stock requests and the absence of any
historical fallback. It does not claim to certify the originating definition
or its acceptance. A partial use of the input through the historical early
builder is refused by `emit_files`; use the late builder for this contract.

The synthetic unit-test markers are not recipes. Do not export them as a
stand-in for the unavailable final coefficients. No sample final-v3 JSON
is added to the repository for that reason.

## Continuing with the real inputs

1. Recover the actual frozen v3 definition and its native numerical inputs
   from the originating workspace. Verify the owner's freeze and record the
   source file's exact hash. Do not rename v2 to v3.
2. Serialize those values without retuning into the contract above, under
   ignored `local/`. Review any conversion against the originating source.
   Record the resulting input-file hash independently. A matching file hash
   proves identity, not that a numerical conversion is correct.
3. Supply the qualified decoded main and GNU reader described below. Run
   both the normal tests and exact-image late probe. The command's expected
   hash must be the reviewed freeze identity, not a value accepted merely
   because a changed file happens to calculate it.

```text
python -m unittest discover -s scripts -p 'test_epl9_native_recipe_inputs.py' -v
python scripts/epl9_film_late_probe.py --recipe-inputs local/frozen-native-inputs.json --recipe-inputs-sha256 REVIEWED_64_CHARACTER_SHA256 --out local/new-v3-native-validation
```

The standalone emitter accepts the same `--recipe-inputs` and
`--recipe-inputs-sha256` pair. Neither command combines this mode with
`--diagnostic-rgb`, `--rgb-tables`, `--color-controls` or `--wb-controls`.
Those separate flags remain historical/diagnostic tools. The exact-image
probe retains its separately labeled historical v0/v2 owner-object
crosscheck; that control is not substituted into the bound v3 module.

Output remains in a new ignored local directory. The qualified reader must
independently decode emitted instructions before a real module manifest is
written. No updater container, camera access or flash operation is provided.

4. Review the new manifest's emitted table identities, five-hook configuration
   as applicable, original request restoration, native-producer ART kind
   `0x1000`, controls, switching, cancellation, owners and placement. Re-run
   the applicable exact-image owner/load checks against this exact module;
   older candidate hashes do not cover newly emitted code.
5. Only then continue the separate full-size install/stock-return container
   work. Preserve main-plus-OSD scope, stock large example photographs and
   existing text labels. Physical entry/recovery and ISP output remain the
   independent gates in [first-integration readiness](first-integration-readiness.md).

## Inputs unavailable in this cloud snapshot

The current source snapshot is PR #1 head
`318d7b4ceacbfe724a7626b18eada87f162497ba`, including published main
`1f4dc523fc8db1a61863da66a09413627d5eb8e8`. The following were not supplied:

- **Actual frozen v3 definition and native input data.** Their authoritative
  filenames and hashes are not published, so no filename is invented here.
  Reported originating-workspace search locations are
  `D:\EPL9Lab\local\gold-portra-scenes-v3-20261107`,
  `D:\EPL9Lab\local\gold-portra-scenes-v3-review-20261107` and
  `D:\EPL9Lab\local\compare-gold-portra-v4-20261107\review`.
  Those directories were not accessible here and do not identify a complete
  native freeze by themselves. Do not reconstruct a full manifest from
  partial numerical excerpts. The originating
  `epl9-v3-integration-status.md` report is also absent.
- **Stock `OLY_E_133_1101_0000_0000.BIN`**, 104552480 bytes, SHA-256
  `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`.
- **Decoded main** at
  `local/epl9-1101-analysis/decoded/00_0100_406e0020.decoded.bin`, 26214336
  bytes, SHA-256
  `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
- **Decoded OSD** at
  `local/epl9-1101-analysis/decoded/01_0101_421e0020.decoded.bin`, 26214336
  bytes, SHA-256
  `ee9a9c3ad1974dd212483ca7d012e51ae23083ce0119589a3b42996aa13ccf1e`.
- **Qualified GNU reader** at `local/mn103-tooling/mn103-reader.exe`, SHA-256
  `e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae`.
- **Matching full-size install and stock-return containers, package-builder
  and native intercepted-write validator source/results.** Their authoritative
  filenames and identities are not supplied by this snapshot. The separately
  reported `epl9-installation-recovery.md` and `epl9-board-readout.md` remain
  unavailable; do not reconstruct missing scripts from a chat summary.
- The pinned external **`references/caduceus-ep7/tools/osd_extract.py`** needed
  for five existing OSD tests. Its exact revision and LF/CRLF identities are
  in [setup](windows-setup.md#clean-checkout-and-cloud-reproduction-2026-11-04).

Existing published decoded-main and OSD candidate hashes describe earlier
qualified runs. Those binaries were not available or reused as a completed
v3 release. Firmware, original media and private reports stay ignored.

## Checks actually performed

Fifteen new tests pass. They cover strict identity/shape/range/hash rejection,
immutable input binding, no historical numerical reads on the explicit
builder path, mutual exclusion of diagnostic inputs, partial-builder output
rejection, actual HSL/RGB/six-axis emission and native WB/matrix handoff.
Synthetic MN103 execution covers separate recipe midtone biases and clamps
with user controls, including the internal early layer. Six distinct RGB
curves and Portra-only overrides check slot separation; equal non-default
midtone biases, both CLIs' paired arguments and mocked-reader manifest
plumbing are covered. Fixed source/module/patch hashes independently derived
from the pre-change PR-head builders, plus a same-number control, confirm
historical output compatibility. The mocked reader is not an independent
GNU qualification.

Including the seven independent [ART gate regressions](epl9-art-hook-gate-regressions.md),
the available suite passes **164 tests** on Linux/Python 3.12.14. Full discovery
was attempted and fails at the missing pinned OSD decoder's setup; its five
tests were not run and are not counted as passed. No identity guard was
disabled in production.

The emission tests use a clearly synthetic main-sized byte array and patch
only the in-process unit-test expected hash. Instruction execution uses the
assembler's authored rows, not independently GNU-decoded vendor code. This
tests transport and emitted native control logic, not exact-image behavior,
TruePic pixels, updater acceptance, UI or camera operation. The final exact
image and pinned-reader checks remain mandatory and were **not run**.

No other ART slots, SD loader, video mode or Wi-Fi code are changed. Log,
10-bit and HEVC remain paused. Preserving this limited implementation path
does not make physical installation safe or establish universal recovery.
