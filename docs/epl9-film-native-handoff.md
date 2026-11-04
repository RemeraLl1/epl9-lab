# E-PL9: film parameters through the native color builder

## Outcome, 2026-11-04

The complete native **color-configuration builder** `0x6079fb88` now returns with a retained parameter object, the existing draft HSL values, a native-generated draft tone curve, a diagnostic matrix and **three separate gamma pointers present together**. Previously, the RGB setter and selectors had only been checked separately. The wrapper's intervening logic does not discard the three supplied pointers in the tested states.

This is progress toward a camera implementation, **not a working firmware replacement or a new film rendering**. The selector intervention is still Python host code at a native return boundary. RGB shapes and matrix inputs are deliberately diagnostic; they are not new Gold/Portra calibration proposals. No new ORF/TIFF is generated in this step. The [v2 Workspace exports](epl9-tonal-neutral-trials.md) remain the latest actual photographic results.

The full-chain fixture precomputes H/S/M once and supplies the resulting tone through the parameter object. Active H/S/M in the full chain has an additional unresolved interpreter boundary in the chroma stage. That limitation is retained explicitly rather than silently changing arithmetic or dropping real camera controls.

## Exact inputs

Olympus E-PL9; displayed body **1.1**, owner-reported; downloaded build **1101**, not a dump of the installed camera. Stock identity carried from prior audits: `OLY_E_133_1101_0000_0000.BIN`, **104552480 bytes**, SHA-256 `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`.

The runner reads and checks the decoded main: **26214336 bytes**, SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`, base **`0x60400020`**. Reader SHA-256 is `e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae`. Listings are decoded afresh and checked against image bytes. The result records script, dependency and recipe-definition hashes; firmware is checked again after execution.

The [tool](../scripts/epl9_film_handoff.py) imports only existing tracked project modules. It neither changes nor requires the other chat's untracked audit code. Firmware, extracted native tables and generated bundles stay in ignored local storage.

## Retained parameter bundles

Each accepted identity has a distinct immutable host allocation. The native constructor **`0x6078ab39`** runs on a private request copy: it normalizes that copy's key to 2 while selecting companion data. The original processing fixture stays at key 11. In these tested requests the constructor initializes **129 bytes** of its 4184-byte native slot; remaining bytes and guards retain poison. Only the qualified header is reused.

The harness preserves native companion gamma/chroma/variant/inline data, attaches the existing v0 HSL table, and supplies the v2 tone calculated by native scaler `0x6074a061` and tone builder `0x6079f309`. Object `+20` receives an explicit host-owned token, 1 or 2. This is not discovery of its real camera producer.

Each local bundle is 8321 bytes including harness padding: three 512-byte diagnostic gamma arrays, a 512-byte native tone, a 3028-byte HSL table and the 129-byte header. Addresses and placement are synthetic, not proposed camera RAM/ROM allocations. All bundle memory is read-only for the complete native call and remains mapped during repeated calls and switching. Real owner acquisition, reference counting and release are still open.

The request uses synthetic formats `0x200`, `0x100`, `0x40`, secondary format `0x100`, and a declared nonzero four-halfword ratio fixture at request `+1568`. Its physical interpretation and capture-WB transport are not established here. No RAW samples are fed into this configuration test.

## Three gamma results through the complete wrapper

The complete pipeline calls wrapper **`0x6079d7da`**, which calls selector **`0x6079d328`** at `0x6079d7f4`. Immediately after its return, at **`0x6079d7f9`**, the three selected pointers occupy stack offsets **+68/+72/+76**.

The host intervention verifies this exact boundary, the expected caller return `0x6079fbcd`, original common-gamma results and the accepted recipe identity. It then replaces only those three stack words. Registers, flags, saved frames and every other stack byte are preserved. Curve spans must be complete, monotone, within 0..4095, nonoverlapping and read-only.

The remaining native wrapper runs unchanged, including its format checks, interpolation-related branches, cache comparisons and call to setter **`0x6079d7a0`**. The complete pipeline continues through its remaining stages to **`0x6079fc36`** and returns with balanced stack and saved registers. Final output **+2596/+2600/+2604** retains the three distinct pointers.

For each accepted identity and all three formats, a paired no-intervention run supplies a **whole-5200-byte oracle**: the intervened configuration must equal it with only the three pointer words replaced. HSL triplets match the existing recipe definitions; the supplied tone pointer and matrix are checked independently. This validates pointer transport through the complete builder, not hardware reading of curve contents.

The diagnostic remaps differ by slot and recipe but do not establish RGB channel order, input domain, hardware interpolation or film accuracy. The four non-target identities 1, 11, unsupported Watercolor III `0x01030078` and `0x01010079` leave all configuration bytes unchanged under the host selection policy. These are **identity-guard controls on the same effective-key-11 fixture**, not proof of preservation of those modes' complete native processing paths.

## Matrix correspondence

The complete builder calls native matrix setup **`0x6079bf86`** with source `request+1592`, writing configuration `+80`. Two diagnostic off-diagonal patterns produce:

```text
Gold slot marker                 Portra slot marker
126    4   -2                    126   -2    4
  2  126    0                      0  126    2
  0   -2  130                      2    0  126
```

An independent normalization/parity oracle matches all nine coefficients. Rows sum to 128, so under a normalized linear interpretation they preserve equal coordinate inputs. This does not identify the coordinate space, establish free neutral tinting or make these matrices a film look. The native owner dispatcher remains executable; this synthetic request supplies no callback. Actual camera callback correction is not validated.

## Tone composition: correction to an early hypothesis

The object tone **does not bypass H/S/M unconditionally**. At `0x6079f325` the builder installs object `+8` as its base pointer, then branches to `0x6079f366`. When request `+1512` contains active controls, it copies that base into owned output `+2612` and bends it.

Four native composition cases establish the practical rule:

- Native base tone plus the recipe's H/S/M produces exactly the previously generated v2 curve, for both slots.
- An already bent recipe curve plus the same H/S/M produces a different curve, applying the correction a second time.

The full-chain passing fixture therefore supplies an already calculated curve with **no active control pointer**. This is an explicit fixture choice, not permission to discard the owner's live highlight/shadow adjustments in a future firmware hook. A real integration must choose one place to compose recipe and current controls and preserve their intended behavior.

When active controls are passed through the **entire** color builder, both current cases stop earlier in global chroma adjustment at **`0x60749f80`, `udfu01 182,d2`**. The existing interpreter rejects unsigned immediate multiplication with the high bit set because the pinned GNU semantics contain a sign-extension ambiguity. This is a known deliberate stop described in [the bounded prototype](epl9-offline-prototype.md), not evidence of a camera crash. No opcode bypass, guessed result or shared-interpreter change was introduced. Isolated tone composition passes; full-chain active-control behavior remains unverified until that arithmetic is qualified.

## Cache behavior and scenario count

Repeated calls with the same immutable bundle produce byte-identical configurations. The native gamma cache takes its fast branch for format `0x40`: the setter is skipped on the repeated call. Formats `0x200` and `0x100` call the setter again under the seeded native format gate, while retaining identical output. Recomputing there is stock behavior in this fixture, not a cache failure.

A format-`0x40` sequence goes from cold Gold, to a verified cache hit, to Portra with different retained pointers. The setter executes again and the final configuration contains Portra's three pointers, tone and HSL. Thus switching is also checked after an eligible cache hit, rather than only on a path that always recomputes.

The existing native comparator/update regression is rerun separately: changing table pointer `+16` alone leaves the tested rebuild bit unchanged, while token `+20` changes it by `0x10000000`. This preserves the [known cache contract](epl9-service-dependencies.md). The full builder's dirty flag is still supplied explicitly by the host; the complete native token producer/invalidation path is not newly solved.

The report contains **23 scenario records**: eighteen stock/intervened/repeated rows, one three-call switch group, and four paired identity controls. Four tone-composition cases and two explicit active-control stops are recorded separately. These counts do not represent completed image frames.

## Reproduction, validation and next boundary

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_epl9_film_handoff.py -v
.\.venv\Scripts\python.exe scripts/epl9_film_handoff.py --out local/new-film-native-handoff
```

Validated result: `local/epl9-film-handoff-20261104-validated/results.json`; native listings and immutable diagnostic bundles are beside it. Earlier `v1` was exploratory and predates composition controls; the `v2` directory is an incomplete failed validation and is not accepted evidence. The final result supersedes these runs.

The workspace suite passes **183 tests**, including eight new handoff contract tests. New tests check exact target matching, boundary/caller checks, unchanged registers/stack outside declared words, read-only/full/nonoverlapping curves, matrix normalization and local output containment. No emulator semantics, historical worklist fix, connected-job probes or diagnostic saturation markers were changed.

For the eventual firmware implementation, this identifies a concrete intervention candidate and a compatible configuration layout. Still required: a compiled native hook and retained recipe identity, qualified placement/allocation and owner lifetime, active-control arithmetic, WB and channel-domain tracing, real preview/capture callers, hardware completion/output, image calibration and regressions outside the two accepted ART slots. The goal remains in-camera processing; desktop exports are research controls. No on-camera operation, firmware image or installation is performed by this runner.
