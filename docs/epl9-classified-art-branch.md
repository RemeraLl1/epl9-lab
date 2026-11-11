# E-PL9: coherent classified ART prefix and finite host resources

## Result, 2026-11-11

The J+10414=1 path now executes to the **first TruePic boundary** for both
Gold 200 and Portra 400 and both audited native owners. The classifier result
is produced by stock code from coherent input fields, not forced to one.
WB executes once, source gains remain unchanged, and the correct recipe RGB
pointers reach native COLOR. No pixels or completion events are produced.

Seven explicitly bounded host arenas are necessary for this prefix. Six fail
at the checked seventh request; seven reach the first submission and then the
same unmapped register `9880014c`. This expands only the host fixture. Its
default remains two arenas, and it never models successful hardware completion.

The separate firmware variant is **unchanged** from the preceding
[native-source gate correction](epl9-native-source-gates.md): decoded main
SHA-256 `2d003930675b47774e9ed3535ee49c64f56ff519bd6f1a33ddafd1a8c688b9b7`,
module SHA-256 `89803a465ae76a81ae6b10055f0b8ff67dc30a1f162785bd8ee4f97e1c70d6e3`.
Old frozen/private-COLOR default hashes and all recipe tables remain intact.
No package, OSD change, publication or camera operation is part of this work.

## Correcting the input contract

The earlier diagnostic forced J+10414=1 while leaving D+268=0, where D=J+36.
It was labeled synthetic, but it is **not a coherent native classifier state**:
the later repeated classifier returns zero and the companion helper selects 5.
That bypasses four scratch allocations needed by the coherent path. Its
two-buffer stop must not be used as proof of the real branch's requirements.

Native diagnostics name D+268 `shSv`. No conversion to photographic ISO or
physical sensor sensitivity is inferred here. For the exact two ART headers
and request kind `1000`, callback `607503e6 -> 60792399` returns one when
`u16(D+268) > 2304`, provided the other audited gates are clear. A selector at
P+21, D+4781 or D+5628 can exclude the path.

The native descriptor stores are executed, not replaced with arbitrary
request tuples:

- Owner operation +72 is the declared `1003`; property +23120 is zero.
- Native helper `607d51ba` reads the declared owner +280 value 2560.
  Store `607d3305` writes D+268=2560. Companion stores produce D+270=0,
  D+278=0, D+280=0 and D+284=0 under the explicitly zero property fixture.
- Helper `607d2562` and store `607d316f` produce D+285=6 for operation `1003`.
- The stock source suffix still produces format `0107`, flags `03`. Source
  address acquisition is declared, not executed.

The same Sv=2560 is set in the **bound owner context before native parameter
production**, not just in the separate source-field fragment. The connected
owner and source therefore do not make contradictory Sv declarations.
Native frame start then produces J+10414/15/16=`[1,0,0]`. The request constructor
copies the same Sv value into R+1610. The repeated classifier's return at
`6078c867` is 1; the complete companion helper returns 3 at caller continuation
`60761e97`. These are distinct return points and are checked separately.

Independent native fragment controls cover threshold boundaries, both keys,
exclusion gates, companion selection and poisoned output flags without models.
Their private evidence is under
`local/cloud-classified-branch-20261111/input-conditions/`.

This establishes internal consistency of a declared native input. Upstream
production of owner+280 and the complete camera property object remain open;
no captured camera session is claimed.

## Minimal finite allocation extension

`FixtureOwner(..., buffer_capacity=7)` and the explicit experiment argument
`owner_buffer_capacity=7` select the expanded host layout. Other callers retain
the original two-slot behavior. The maximum is seven, never unbounded.

| Native ID | Requested payload bytes | Host arena |
| --- | ---: | --- |
| `1000` | 31850496 | `20000000` |
| `7` | 1165632 | `23000000` |
| `8` | 1053760 | `30000000` |
| `a` | 18411008 | `33000000` |
| `b` | 4662528 | `36000000` |
| `c` | 1195520 | `39000000` |
| `d` | 298880 | `3c000000` |

These are native requests and **host addresses**, not camera RAM reservations.
Actual payload totals 58,637,824 bytes, with a separate 16-byte poison guard
per allocation. All payloads and guards retain their expected contents.
The original 32 MiB per-request maximum, native buffer-table alignment,
read/write bounds, overlap detection, ownership/release checks and failure
behavior remain enforced. Extra arenas avoid the owner fixture near `2c000000`.
Invalid size and exhausted capacity have distinct errors; a bad size cannot
be mislabeled as the expected seventh-allocation capacity stop.
No RTOS, DMA/cache coherence or physical allocation capacity is qualified.

The six-arena negative control rejects ID `d` at native call
`6074a8bb -> 6073eab3` (event 19; return `6074a8c2`). The callback dispatch stops
at `6073eac3`. This deliberately expected partial outcome is not a successful
request or completed image.

## Fail-closed checks and current boundary

The previous source probe's conditional gain check has been replaced by
`checked_classified_prefix`. It checks source gains, exactly one gain entry
and return, source/kind/selector fields, gain ordering, output/source/completion
evidence and an explicit expected stop/callsite. Every consumer snapshot must
retain the expected fields and gains. Hardware-prefix checks also require one
submission/COLOR/gain-consumer, the correct gamma pointers and hooks, the
native first-submit event and the `800` write value. An arbitrary fault, missing
evidence, wrong requester, wrong gains or wrong stop is now an error.

The new classified probe checks 12 outcomes across both recipes and owners:

1. Capacity six: only the exact event-19 allocation-limit stop is accepted.
2. Capacity seven, prefix: only the first native submit
   `60762276 -> 6074f11c` is accepted.
3. Capacity seven, processing: only the exact first TruePic fault at
   `6073eafa`, writing `800` to `9880014c`, is accepted. The recipe must have
   applied and gains must match Gold `[1106,901,1024,1024]` or Portra
   `[1060,963,1024,1024]`, without changing the original source gain record.

All these outcomes are explicitly **incomplete**. First submission is not
completion. The hardware fault prevents observation of subsequent submissions;
no ready bit, ISR, completion signal or successful return is synthesized.
Physical packing, pixels, whole-job concurrency and camera behavior remain
unverified. The subsequent [cloned-snapshot reentry investigation](epl9-native-source-reentry.md)
finds no WB accumulation, but demonstrates interrupted-prefix disruption at
gain return under finite host resources. Same-job exclusion remains required.

## Reproduce

```sh
python -m unittest discover -s scripts -p 'test_*.py' -v
python scripts/epl9_classified_branch_probe.py \
  --rgb-tables <the exact existing v3 native-rgb-tables.json> \
  --out local/new-classified-art-audit
```

Assertions must remain enabled. The checked reader, exact stock input and
separate candidate identities remain mandatory. The probe stops on any
unexpected boundary and saves the latest diagnostic case before validation.
Its normal completed report is `classified-branch.json`; it never declares
`install_ready`, whole-job or multi-submit completion.

Retained report for this pass:
`local/cloud-classified-art-v4-20261111/classified-branch.json`.
Firmware, listings, input fixtures and derived binaries remain ignored local
files. Do not substitute this decoded main into old package/readback references.
