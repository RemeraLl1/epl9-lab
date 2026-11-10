# E-PL9 T1/T2: SD recipes connected to native image configuration

The subsequent [placement and memory-lifetime report](epl9-sd-placement-lifetime.md)
rebuilds these modules at actual in-image addresses and validates their early
loading and normal session retention. Complete teardown remains unqualified;
this document retains the original synthetic-address generation.

2026-11-10. A separate offline consumer now connects the
[T1/T2 loader and session state](epl9-sd-state-slots.md) to native image
configuration. Embedded defaults and accepted SD records use the same
processing route. Missing or rejected files retain the embedded recipe.
Both Watercolor v3 generations, their recipe inputs and encoded packages
remain byte-identical.

The new consumer is **16384 bytes**, including **2253 code bytes / 649
instructions** and two embedded fallback descriptors. Module SHA-256:
`716f6e9874d2cec8a5fabd24cfbc7664210efe9dd25a67b5ce32c3097ff0000c`.
Its address **`0x6a000000` is synthetic**. It calls the unchanged 6144-byte
state module at synthetic `0x69000000`; that module still hashes to
`6cd7311db65d3e7b4d6773095c93c13b5cacf2d94852d191f5e25de78293dda4`.

These results establish SD-to-native-configuration control flow, including
connected requests reaching the existing unmapped TruePic boundary. They do
not establish a finished pixel frame, camera SD I/O or installation readiness.
No camera command, firmware container or card preparation was performed.

## Selection, preparation and lifetime

The preceding HLS manager layout remains **288 bytes**. Its reserved word
**manager +212** now holds the descriptor-arena pointer. Initialization of
that word was already part of the preceding zeroed tail; no additional BSS
address is assumed.

The new event adapter calls the old `sd_state_event` first. Once both slot
attempts have completed (states 2/3/4), and loader busy is clear, it prepares
both descriptors in the HLS task. It requests **8192 bytes** from the native
ordinary allocator. Native size classification selects **pool `0x10004`, a
16384-byte block**. Two 4096-byte descriptors occupy its first 8192 bytes.
Pool backing and available blocks are declared fixtures. The test arena
address `0x61fc0000` is a fixture, not an allocated camera address.

The arena root is marked 1 while construction is in progress; that value is
outside the allowed pool range and cannot be consumed as a descriptor. Both
descriptors are completed before publishing the real arena pointer. A failed
allocation resets that word to zero, retains usable embedded descriptors and
can retry on a later event. A successful arena is prepared once per initialized
session. The module's embedded descriptors also work before manager creation,
while SD is not ready and while a file RPC remains pending.

| Descriptor-relative bytes | Meaning |
| --- | --- |
| 0–3 | `DCP1` magic `0x31504344`, written last by native materialization |
| 4–7 | Version 1 |
| 8–11 | Logical slot 1 or 2 |
| 12–15 | Source record pointer selected by the existing loader |
| 16–19 | Native HSL table pointer, descriptor +64 |
| 20–23 | Retained packed-record pointer, descriptor +3104 |
| 24–27 | Shared gamma pointer, descriptor +3252 |
| 64–3091 | Native 3028-byte COLOR table, with only 72 authored HSL bytes changed |
| 3104–3763 | Complete 660-byte recipe snapshot |

Other bytes are padding and are not interpreted. The native materializer
copies the stock COLOR template and the selected record, then applies the
twelve HSL triplets. Its output is checked against the independent host
materializer, including header pointers, all table bytes and all record bytes.

`sd_descriptor(D0=1/2)` returns the prepared descriptor only when its tag,
slot and source pointer agree with current slot selection. Otherwise it
returns that slot's module-owned embedded descriptor. Unknown IDs return
null. The ABI uses mask `0xf0`, frame 24, result `A0`.

The loader still retains its accepted 2 KiB file blocks. The new arena retains
its own complete recipe snapshots and all referenced tables. No descriptor
or LUT points into a frame's temporary stack. Descriptor and loader-owned
pool regions are read-only during all tested configuration and connected-job
runs. Session teardown, cancellation during preparation, cross-core
publication, cache/DMA aliases and every allocator outcome remain unqualified.
The existing cold-start allocation requirement remains in force.

## Processing route

Logical T1/T2 still use `SLOT01.RCP` / `SLOT02.RCP`. To exercise native routing,
this separate experiment binds them to **synthetic processing keys
`0x01030078` / `0x01040078`**. They retain the known native route family but
are distinct from Watercolor I/II keys `0x01010078` / `0x01020078`. They are
not assigned camera menu entries or established free slots. No claim is made
that these aliases can be deployed without inventorying all key consumers.

The tested RAM overlay has six instruction sites: the old manager allocation
and constructor changes, plus the new HLS adapter, route gate, COLOR entry
and early WB entry. Exact stock bytes are required before creating each
replacement; GNU independently decodes every replacement and module
instruction. Only copies used by the offline interpreter are changed.

| Recipe field | Native consumer |
| --- | --- |
| Twelve HSL triplets | `0x6079e50e` builds the ISP configuration from the retained HSL table |
| Contrast | Loaded from record +136, added to user contrast and clamped to ±2 |
| Highlights / midtones / shadows | Loaded from +138/+140/+142, merged with user values and clamped to ±7; native control conversion and tone selector run |
| Two WB Q10 gains | Loaded from +144/+146 in the early request path; rounded and saturated to 65535, preserving the other two native coefficient slots |
| Shared 256-entry gamma | Native setter `0x6079d7a0` installs the retained +148 curve for all three selected gamma pointers |

The format and native-order WB meaning are unchanged; physical channel labels
remain unverified. Zero in any of the four source WB coefficients bypasses
the bias, preserving the earlier native contract.

COLOR processing uses a private 128-byte context and 1876-byte request in a
2048-byte stack area, plus a 32-byte wrapper area. It changes only these
private copies to effective COLOR key 11 and the merged controls. Native
owner/matrix handling runs normally. After native COLOR, the consumer packs
the selected HSL table, rebuilds tone with the merged controls and installs
the selected gamma. It preserves the native return and the complete caller
request/context in isolated configuration tests. The native owner's +20
comparison token is never repurposed.

The early WB hook intentionally changes the freshly copied request's first
two WB coefficients. It preserves live A0/A2/A3/D3 and replays the original
register setup before the native continuation. COLOR does not apply WB again.
No file I/O or allocation occurs in either image-configuration hook.

Target frames force the native color/tone rebuild using private context flags.
When the cached gamma identifies a preceding T1/T2 recipe, an ordinary frame
also takes a private copy and forces the native rebuild. This prevents stale
recipe data on exit without changing the native parameter-object token.
Ordinary cold frames pass through. Publication is once per session, so the
known embedded and arena gamma identities remain stable for this exit check.
Same-job/output/cache serialization remains required; private parameters do
not make the whole job concurrently safe.

## Retained validation

Report: `local/epl9-sd-processing-20261110-final/validation.json`.
`complete_validation` is true. Earlier `v1`–`v6` directories are development
evidence and do not replace this report.

- **40 SD unit tests pass**, including four new synthetic descriptor/WB tests.
  Synthetic materialization uses a generated ROM table, not firmware data.
- **59 complete 5200-byte native configuration comparisons pass** against
  independent host parameter arithmetic followed by unhooked native COLOR,
  HSL, tone and gamma setters. They cover both slots, four request formats,
  missing files, exchanged files, one missing/corrupt neighbor, SD not ready,
  pending read and close uncertainty. Three extra cases use an arbitrary
  SD recipe with extreme HSL/contrast/H/M/S/WB values and a different gamma,
  including null user controls and an absent parameter owner. Recipe values
  are read from data rather than emitted as Gold/Portra instructions.
- **71 native WB comparisons pass**, including minimum/maximum coefficients,
  rounding, saturation and zero-input bypass. All 1876 request bytes and
  live entry registers are checked. In connected jobs the adjusted WB record
  reaches the real processing request.
- **13 cache/passthrough controls pass**: five warm T1/T2 frames, four exits
  to ordinary modes and four cold unrelated identities, including both real
  Watercolor I/II keys. Full configuration bytes agree with the appropriate
  native oracle; no prior recipe gamma survives an ordinary exit.
- **12 connected native jobs pass to the expected boundary**: both slots,
  job kinds `0x200/0x100/0x40`, with exchanged SD files and with both files
  missing. Native constructor, frame start, executor, request/cache building,
  COLOR and post-COLOR processing execute. Job identity stays unchanged;
  selected gamma pointers and expected adjusted WB reach the native request.
  Each stops at the unmapped TruePic register **`0x9880014c`**. No hardware
  completion or output pixels are synthesized.
- Arena allocation failure keeps embedded processing available; a later
  allocation retry publishes the arena. Repeated successful events do not
  allocate it again. Missing/rejected files and pending/uncertain resources
  retain their earlier state semantics.
- **16 protected inputs remain identical**, including both v3 mains, icon
  OSD, both encoded candidate generations, restoration package, recipe
  sources and the preceding loader/state source generation. The old state
  module is rebuilt and required to match its retained SHA-256.

Finite models remain explicit: pool backing, default-owner lookup, RTOS
task/event/file-service replies and storage metadata for the loader; owner,
resource, event/completion/lock fixtures and inferred finite binary32 leaves
for connected jobs. No model shadows loaded native code. The existing job
harness's allocation-release front remains modeled. Its accepted input grid
is extended in a private function copy; shared job/v3 probe files are unchanged.
These checks do not qualify physical floating-point behavior, full RTOS
scheduling, all owner callbacks or an actual exposure/image result.

## Inputs, source and reproduction

Olympus E-PL9 / IM008 / model 1330, owner-reported displayed body **1.1**,
downloaded main build **1101**. This is not a dump of the installed camera.
Exact stock main: **26214336 bytes**, SHA-256
`8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
Its source package is **104552480 bytes**, SHA-256
`aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`.
GNU reader SHA-256:
`e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae`.
All cached stock listings are byte-checked again; listing, code and protected
input hashes are retained in the report. Firmware-derived fallback records
and native tables remain ignored local artifacts.

Implementation: [builder](../scripts/epl9_sd_processing.py),
[native source](../firmware_src/epl9_sd_processing.s.in),
[probe](../scripts/epl9_sd_processing_probe.py),
[tests](../scripts/test_epl9_sd_processing.py).

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_epl9_sd_*.py
.\.venv\Scripts\python.exe scripts/epl9_sd_processing_probe.py --out local/new-sd-processing
```

The output must be new and under ignored `local/`. `--reuse` can reuse stock
windows from an earlier processing run, with exact byte verification.
`--jobs-only` is a development subset and sets `complete_validation` false.
Only standalone synthetic-address modules, tiny hook fragments and evidence
are emitted; no modified main image or install container is retained.

Real module placement/loading, lifecycle/teardown, hardware SD timing, native
menu assignment and labels remain further work. Both Watercolor v3 candidates
and their first camera-test priority remain separate.
