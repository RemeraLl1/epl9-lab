# E-PL9: deeper color and tone controls

## Outcome, 2026-11-02

The exact E-PL9 main has more color machinery than its twelve-sector HSL block:

- A native selector can choose **three different RGB-gamma curve pointers**. A stock ART key actually selects three distinct, differently shaped tables.
- A separate **256-point luminance-tone curve** is selected by contrast and other request fields, and can be copied to a per-output buffer and bent by tone controls.
- A **3×3 matrix** stage packs cross-channel coefficients, normalizing the tested rows to a sum of 128.
- A **six-axis hue/saturation** stage exists independently of the twelve-record HSL block.
- The existing parameter-object mechanism supplies separate gamma and tone pointers, as well as the previously found HSL pointer. Its gamma override supplies **one common curve to all three channels**, not three independent curves.

Forty component cases completed using freshly decoded native instructions and synthetic memory. These are configuration-level results, not images, a complete processing cycle, hardware tests or a deployable patch. No shared interpreter or other chat's development files were changed for this audit.

For a Classic Chrome-inspired base, the separate channel curves are a promising additional control: different transfer functions can change the color balance of dark and bright neutral values differently. This is an engineering inference from the configuration structure and stock curves. The exact RGB hardware consumer, input domain, interpolation and on-camera appearance have not been validated here. No Classic Chrome, Gold 200 or Portra 400 rendering has been produced.

## Input and provenance

| Input | Identity |
| --- | --- |
| Model / displayed version / internal main build | Olympus E-PL9 / owner-reported 1.1 / downloaded build 1101 |
| Stock container | `OLY_E_133_1101_0000_0000.BIN`; 104552480 bytes; SHA-256 `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Decoded main | 26214336 bytes; SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |
| Candidate address mapping | `0x60400020`; file offset = address minus this base; not measured camera RAM |
| Reader | SHA-256 `e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae`; [tool provenance](mn103-tooling.md) |

The stock container identity is carried from the prior audit; this runner reads and hash-checks the decoded main, including after execution. It is not a dump of the installed camera. Original bytes and derived listings remain ignored under `local/` and `firmware/`.

Search guidance came from existing ignored upstream checkouts:

- [fishcu/oly_fw_analysis](https://github.com/fishcu/oly_fw_analysis/tree/539fcf1fa9eda5fdef8ede4deeab94a4691d94c3), commit `539fcf1fa9eda5fdef8ede4deeab94a4691d94c3`, notably `docs/color/MODES.md` and `docs/color/pen-f/CREATIVE_PROCESSING_JOBS.md`.
- [cakelesscoder/caduceus-ep7](https://github.com/cakelesscoder/caduceus-ep7/tree/7d42c1f258737b7196c6b17cec5d643b5080ece6), commit `7d42c1f258737b7196c6b17cec5d643b5080ece6`, notably `docs/TONE_ENDS.md` and `docs/VIDEO_LOG.md`.

Their model-specific addresses and field offsets are references only. All E-PL9 functions and values below come from its exact bytes and bounded native execution. Existing interpreter semantics follow the pinned GNU sources documented in [the prototype](epl9-offline-prototype.md); dependency hashes are recorded in each result.

## Ordinary development has separate stages

The previously established common builder `0x6079fb88` calls these stages in its ordinary branch:

| Role | E-PL9 entry / observed output |
| --- | --- |
| Matrix candidate, before that branch | `0x6079bf86`; pipeline passes destination `output+80` and source `request+1592` |
| RGB gamma candidate, before that branch | `0x6079d7da` → selector `0x6079d328`; setter `0x6079d7a0` writes pointers at output +2596/+2600/+2604 |
| Six-axis color candidate, before that branch | `0x6079cdb0` → packer `0x6079cd40`; output +100…+123 |
| Global chroma candidate | `0x6079e14b`; parameter object +24/+26 or stock selector; not executed in this audit |
| Twelve-sector HSL | `0x6079ebcc`; [existing evidence](epl9-art-routing.md) |
| Luminance tone | `0x6079f309`; pointer at output +2608; owned buffer +2612…+3123 |
| Further chroma suppression candidate | `0x6079f40f`; format/mode-sensitive tables and interpolation; static only here |

This is CPU configuration-call order, not proof of ISP pixel-processing order. Some requests take alternate/disable branches. A stock block's existence does not mean every ART or optimized route consumes it.

## Three channel curves: native stock evidence

Selector `0x6079d328` writes three pointer results. The caller eventually passes those to `0x6079d7a0`, which installs them independently and clears output +4 bit `0x1000`.

With request kind 0, format `0x0200`, secondary format `0x0100`, zero variant flags and other documented synthetic defaults:

| Processing key | Three returned pointers |
| --- | --- |
| 1, 2, 3, 4, 5, 8, 10, 11 | `0x608c37e4`, `0x608c37e4`, `0x608c37e4` |
| Watercolor candidate keys `0x01010078`, `0x01020078` | Same common curve in these states |
| `0x01010079` (Vintage I by upstream naming; camera-menu binding unmeasured) | `0x608c63e4`, `0x608c65e4`, `0x608c67e4` |

Each inspected curve is 256 little-endian u16 values, within 0…4095 and monotone. Their table sizes and role agree with the related-model RGB-gamma research; the exact E-PL9 hardware channel order and transfer domain still need downstream tracing.

At knots 0/32/128/255 the three distinct stock tables contain:

| Pointer | Four values |
| --- | --- |
| `0x608c63e4` | 0 / 2727 / 3782 / 4095 |
| `0x608c65e4` | 0 / 2735 / 3866 / 4095 |
| `0x608c67e4` | 1283 / 2224 / 3422 / 3818 |

This establishes real differences, including different endpoints, rather than three aliases for one table. It does not identify any table as a calibrated film response.

A separate synthetic setter case supplies three distinct valid curve-buffer pointers and checks the complete 5200-byte output against the expected pointer/flag-only modification. Stock selection and pointer packing complete with returns; the whole `0x6079d7da` chain and its hardware consumer are not executed.

Channel curves operate on each channel's value. They can offer brightness-dependent color balance on neutral ramps, but do not constitute an arbitrary hue × luminance × saturation mapping or a demonstrated general 3D LUT interface.

## Tone curve: contrast and local bends

The E-PL9 constructor copies parameter byte +4751 into **request+1795**, and +4752 into **request+1796**. The tone selector reads +1795 as signed contrast and treats +1796 as a gradation-like selector. These offsets differ from the E-P7 reference; do not copy that model's +1796/+1797 pair into E-PL9 code.

For effective key 11, default synthetic fields and context +60 = 2, the complete `0x6079f309` chain returns these curves:

| Contrast | Pointer | Knots 32 / 128 / 192 |
| --- | --- | --- |
| −2 | `0x608d05ee` | 158 / 506 / 730 |
| −1 | `0x608cf9ee` | 142 / 510 / 750 |
| 0 | `0x608cf3ee` | 128 / 514 / 770 |
| +1 | `0x608cf7ee` | 107 / 517 / 794 |
| +2 | `0x608d07ee` | 89 / 519 / 817 |

All five curves have 256 u16 points in 0…1023, monotone, with endpoints 0 and 1023.

The request's +1512 pointer references five tone halfwords. Native helper `0x6074a061` scales them and calls `0x60749cbd`, producing eight halfwords at context +64. Builder `0x6079f309` copies the base curve to output+2612 when necessary and invokes `0x6074a322`, which bends the curve in place and updates the active pointer.

Twelve cases vary one tone halfword at a time, indices 2/3/4, using −7/−3/+3/+7. Their measured configuration responses correspond to highlights/midtones/shadows, respectively. At the ±7 endpoints:

| Halfword / response | Measured knot | Base / negative / positive |
| --- | --- | --- |
| 2 / highlights | 192 | 770 / 653 / 887 |
| 3 / midtones | 128 | 514 / 279 / 749 |
| 4 / shadows | 32 | 128 / 19 / 237 |

Every tested curve stayed monotone and retained 0/1023 endpoints. Output changes were confined to the pointer, curve buffer and relevant enable word; context changes during scaling were confined to +64…+79. User-interface producers/ranges, combinations of controls, real caller flags and preview/capture coverage are not established by these cases. The first two tone halfwords are not assigned new user-facing meanings here.

## Parameter-object route and its limitation

The existing object at request+1524 is consumed by several stages:

| Object field | Observed role |
| --- | --- |
| +0 | Single gamma pointer, copied into all three selected channel slots when the variant guard matches |
| +8 | Tone-curve pointer used by `0x6079f309` |
| +16 | HSL table pointer from the existing audit, conditional on its rebuild flag |
| +24/+26 | Two chroma values loaded by `0x6079e14b`; static only |
| +28 | Gamma variant byte, compared to a request-format-dependent flag |

Two synthetic cases exercise matching/mismatching gamma variants: the matching case accepts the synthetic gamma pointer; mismatch uses the stock fallback. Both accept the independently supplied tone pointer with no tone block active. These are pointer-propagation checks, not proof the hardware reads the proposed contents.

Consequently, a custom luminance curve and a common RGB curve have a concrete native attachment candidate. **Three independently customized channel curves need an additional selector/setter intervention**, because object +0 alone supplies only one pointer. The exact native implementation is open.

Retain the [service/cache contracts](epl9-service-dependencies.md), especially object lifetime and cache invalidation. The connected-job research shows that replacing a table pointer alone does not necessarily trigger a rebuild. This audit seeds components directly and does not solve those integration requirements.

## Matrix and another color block

Two native matrix cases run `0x6079bf86` through returns. A neutral source becomes diagonal 128; a synthetic source with off-diagonal markers becomes:

```text
124   10   −6
  8  124   −4
 −2    6  124
```

All row sums are 128. The helper `0x6079bedb` adjusts diagonal values to preserve that sum. This supports cross-channel mixing, but **not** a claim that these tested matrices freely tint neutral gray: equal channel inputs remain equal under the normalized matrix interpretation. The coordinate space and actual calibration/input units need further tracing.

Seven cases run six-axis selector `0x6079cdb0` and its packer, producing differing two-by-six coefficient sets for keys 1/2/3/4/11 and both Watercolor candidates. Its 24-byte output is distinct from the twelve-sector block beginning +688. The stock key-11 coefficients are not all zero in the tested E-PL9 state; do not assume that switching to key 11 neutralizes every other color stage. Exact hue-axis labels and arbitrary attachment were not established.

Naive scans for numeric offsets also found virtual-call-table loads at `0x60c6db0a` and nearby. Decoding showed these were unrelated indirect calls, not the RGB upload path. They were excluded from the final runner; matching an offset is insufficient evidence.

## Reproduction and limits

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_epl9_deep_color_audit.py -v
.\.venv\Scripts\python.exe scripts/epl9_deep_color_audit.py --out local/new-deep-color-audit
```

Validated output: `local/deep-color-20261102-validation-v1/audit.json`, 5150 decoded instructions, 16 instruction anchors and **40 component cases**. Six synthetic tooling tests cover image/hash rejection, output containment/no overwrite, rejection before reader invocation, curve bounds/range/order and unrelated-byte detection. The audit uses the existing call engine without new models, stubs or interpreter modifications. Unsupported/missing instructions or memory abort the case.

These results narrow the previous uncertainty: deeper controls are present in E-PL9 itself. Remaining work is to connect them to recipe-specific native objects/hooks, trace invalidation and hardware consumption, establish real preview/capture callers, and calibrate photographs. There is no camera access, modified firmware, pixel-accurate rendering, installation or recovery claim.
