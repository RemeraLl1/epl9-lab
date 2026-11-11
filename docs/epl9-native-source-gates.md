# E-PL9: native source fields and consistent film qualification

The subsequent [classified-branch follow-up](epl9-classified-art-branch.md)
replaces the earlier forced-bit diagnostic with coherent native-produced Sv
inputs and a finite seven-arena host fixture. Both recipes reach the first
TruePic boundary on that path; subsequent submissions remain incomplete.

## Result, 2026-11-11

The existing private-COLOR v3 candidate has a concrete integration gap on a
stock-produced primary ART source. Its early WB hook accepts the ART key and
request kind, but late COLOR/gamma reject the native source format and flags.
A separate **opt-in** variant fixes this scoped CPU/configuration path for
both Gold 200 and Portra 400. Default builds, frozen recipe bytes, existing
main/OSD candidates and encoded packages remain unchanged.

This is not a camera test, an ISP pixel result or an installation release.
All derived binaries stay in ignored local output. No update container,
camera command, card preparation or flash write was produced by this work.

## Verified inputs and retained identities

Olympus E-PL9, owner-reported body 1.1, downloaded internal build 1101. The
update is not an independently acquired dump of the installed camera.

| Input/output | Bytes | SHA-256 |
| --- | ---: | --- |
| Stock update `OLY_E_133_1101_0000_0000.BIN` | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Stock decoded main | 26214336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |
| Unchanged frozen v3 main | 26214336 | `501707d09a0eb648e46196752b7ece17cd5368f6d54dbabce7c73e9806f65686` |
| Unchanged private-COLOR v3 main | 26214336 | `72cc1e48e6b42ab02b9911bdb841fe2c5b0cb34f2c08893f6b78be8a6871beee` |
| Separate native-source private main | 26214336 | `2d003930675b47774e9ed3535ee49c64f56ff519bd6f1a33ddafd1a8c688b9b7` |
| Separate native-source private module | 15360 | `89803a465ae76a81ae6b10055f0b8ff67dc30a1f162785bd8ee4f97e1c70d6e3` |

The opt-in private module has 1933 code bytes, versus 1781 in the existing
private-COLOR module. **Every byte from module offset 4096 onward is identical**,
including HSL and all three curves for each recipe. No numerical recipe was
changed or replaced with another revision. OSD and package references were
not changed to recognize this new main.

The locally built GNU reader remains qualified by its pinned upstream vectors,
negative controls, source hashes and build receipt. It independently decodes
every emitted instruction and changed hook. This run's reader SHA-256 is
`013c0af69148cc34b74e2a8a46c4efba808c7575a19cd1c08b4f2ab3867712d5`.

## Why the old isolated field tests were insufficient

Let J be the job, P=J+4 its copied parameters, D=J+36 its source descriptor,
and R=J+10440 the 1876-byte request.

1. Constructor `6074f250` clears the entire request. At old WB site
   `6074f352`, R+28/R+48/R+1832 are still zero. R+1568..1575 have just received
   the source gain record. Comparing the late source predicate at this old
   point would disable WB on ordinary native requests too.
2. After the constructor, builder `60761b6a` can invoke a callback with J/R at
   `60761bd9`. Such callbacks can set a selector, including `0900` at
   `60755cac`; selector mismatch is not universally impossible for ART.
3. Native owner event 14/id 1 is then called. The audited primary and wrapper
   handlers do not normalize the first source descriptor's format or flags.
4. Loop `60761c98..60761c9d` copies all 64 bytes D into R+20. Its store at
   `60761c9a` writes R+28 from D+8, and R+48 from D+28.

The native primary preparation chain is
`607cf0ad -> 607ce6b8 -> 607d30bf -> 607d3153 -> 607d336e`.
Helper `6074e341` establishes the destination alias D=J+36. A native prefix
executes 293 instructions without models, reaching source-address resolver
`607c56b5`; that resolver is not executed by this investigation.

For declared ART operation `1003`, the source constructor chooses argument 12
to `607d2601`, producing **format `0107`**, not the old fixture's `0200`.
It unconditionally ORs flags with 3 at `607d3522/3525`. Property halfword +4300
then selects bit 2. With the fresh zero descriptor the result is **03 or 07**.
Native suffix execution confirms both outputs without any modeled calls.

R+48 is therefore a flags byte, not a whole-byte gamma-variant enum. For this
format stock gamma uses `(R+48 >> 2) & 1` at `6079d374..6079d37c`. Flags 03
have variant zero; flags 07 have variant one. Physical source packing and
photographic equivalence are not established by these numeric findings.

The existing candidate, given the suffix-produced 64-byte descriptor, reaches
late COLOR with R+28=`0107`, R+48=3 and R+1832=0. WB is already changed but the
recipe is skipped and the gamma pointers remain stock. This is a connected
native-prefix result under declared resources, not a measurement on a camera.

## Separate minimal correction

`build_late_module(..., native_source_gate=True)` and the builder CLI option
`--native-source-gate` explicitly opt in. Defaults reproduce both old main
hashes above. The late assembly templates and numerical recipe files are
unchanged.

The shared inline predicate in `epl9_native_source_gate.py` accepts exactly:

- source `0100`, flags 00;
- source `0200`, flags 00;
- native source `0107`, flags 03.

Existing exact recipe-key and request-kind checks remain. Selector must be
zero. Unknown formats, unknown flag bits and native flags 07 remain excluded.
The v3 curves were qualified for native gamma variant zero; silently accepting
variant one would require new evidence.

For this variant only, WB moves from `6074f352` to **`60761c9e`**, immediately
after the source copy and optional callback. The six replaced stock bytes are
`fa b4 f0 02 a0 00`; the continuation is `60761ca4`.
Builder SP+52 retains R. WB, COLOR and gamma now inspect the same populated
source/selector fields on the audited path.

The new body preserves A0, D2/A2/D3/A3, SP and MDR/MDRQ, adds no stack or
mutable global, restores D1=0 from the completed copy loop, and replays the
displaced load/CMP. A1 is overwritten before native use on both continuation
branches. Independent GNU decoding and synthetic instruction controls check
the new body and flags. No guessed free request field or persistent lock is
introduced.

This point executes once for a freshly constructed request, rather than at
each processor invocation. Moving WB only to `60762b4d` was rejected because
the J+10414 branch can submit the main request earlier at `60762276/60762326`.
The chosen point precedes those submissions. The audited temporary descriptor
copy/restore retains the original source format/flags: helper `6073a591`
copies the original descriptor back to J+12324 at `6073a7e8..6073a7f4`.

The later FE00 selector write at `60762b04` requires P+8 != 1, which excludes
the exact two accepted ART headers. This does not authorize arbitrary other
owners/admission callbacks or establish whole-job concurrency safety.

## Validation and reproduction

```sh
python -m unittest discover -s scripts -p 'test_*.py' -v
python scripts/epl9_native_source_probe.py \
  --rgb-tables <the exact existing v3 native-rgb-tables.json> \
  --out local/new-native-source-audit
```

The probe fails unless its default reconstruction matches the old frozen and
private-COLOR main hashes. It leaves all previous candidates intact and emits
only separate ignored offline outputs. Assertions must remain enabled.

Retained checks cover:

- Both recipes and both native owner parameter producers: source 03 applies
  WB once and selects the recipe's three distinct gamma pointers. Source 07
  leaves WB unchanged and skips the recipe.
- A selector-0900 negative control for both recipes/owners: WB and recipe are
  skipped. The selector value is explicitly injected at the completed-callback
  boundary; execution stops after native COLOR returns at `6079ff0e`. Its
  downstream special-effect path is **not** a hardware-boundary pass.
- Full 5200-byte configuration oracles for native-source cold/warm switching,
  Gold -> Portra -> stock, and film -> rejected source/selector cleanup.
- Existing legacy-source cache transitions, unrelated-mode passthrough and
  the 24 native owner control cases.
- Dedicated synthetic instruction controls for exact allowlists, unsupported
  keys/kinds/selectors/flags, zero-gain bypass, saturation, register preservation,
  displaced CMP flags and fail-closed template replacement.

The normal and flags-07 connected paths still stop at `6073eafa`, attempting
to write `800` to unmapped TruePic register `9880014c`. Output remains poisoned,
source-pixel instruction reads and completion signals remain zero. This is
configuration evidence, never processed image evidence.

At the initial native-source gate checkpoint, **328 source unit tests** passed;
compileall and diff whitespace checks also passed. These totals describe that
cloud checkout and
do not turn native or camera stages into passed tests.

Reports live under `local/cloud-hook-field-reachability-20261111/` and
`local/cloud-native-source-gate-v6-20261111/`. They identify injected controls,
reader provenance, source hashes and the exact stopped paths. Stock listings,
firmware, descriptors and generated binaries stay local.

## Remaining limits

The source address is declared; the complete native acquisition/preparation
and its real handles are not executed. The classifier's nonzero branch is an
explicit synthetic prefix control, not a camera-observed state. It executes
the new gain hook once, with unchanged source gains, but stops at the existing
host owner's two-buffer allocation limit before its first submission. The
native requester is `6074a8bb` (owner event 19, return at `6074a8c2`); no extra successful allocation
or completed hardware request is invented. Consequently the additional branch
and multiple submissions remain dynamically unqualified. Static hook dominance
and descriptor round-trip analysis are not successful multi-image execution.
Arbitrary later owner writers, same-job overlap, physical source packing,
crop/CFA/black-level/WB calibration, ISP pixels, full runtime preservation,
installation/readback and physical stock restoration remain unqualified.

Do not substitute this main into existing package/readback references or
describe it as ready to flash. The next useful work is to complete the bounded
native source-acquisition and extra-classifier path, then qualify any separate
candidate/package/readback generation together. Actual rendering still needs
the eventual controlled camera test.
