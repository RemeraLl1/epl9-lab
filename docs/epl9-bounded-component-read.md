# E-PL9: bounded component-reader prototype

2026-11-10. There is now a **separate 877-byte native prototype** that resolves
logical block mappings and submits at most one page read per call, with finite
mapping/completion/status loops and no erase/program/relocation calls. It is
GNU-decoded and passes 44 synthetic native controls. A host collector joins
two full reads of both components and checks them against the frozen candidate
or stock envelopes; five test methods pass, including both full-size targets.

**A usable camera acquisition method is not yet established.** The prototype
has no installed hook, real allocation, acquired controller lock, transport or
qualified hardware abort. A bounded software loop does not prove that a stuck
DMA cannot block the camera. Gold/Portra v3 and both existing package generations
remain unchanged. No device command, flash write or SD operation occurred.

## Identity and retained evidence

Olympus E-PL9 / IM008 / model 1330, body 1.1 reported by owner, downloaded main
build 1101. The source is not a dump of the installed body.

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| Stock update `OLY_E_133_1101_0000_0000.BIN` | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Stock decoded main `00_0100_406e0020.decoded.bin` | 26214336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |
| Pinned GNU reader executable | 71168 | `e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae` |

Primary evidence: `local/epl9-bounded-read-20261110/`, containing the separate
module, independent GNU listing, `native-results.json`, `capture-results.json`
and `manifest.json`. Native helper listings first collected during the resumed
investigation are retained under `local/epl9-bounded-read-20261107/`.
The [preceding maintenance report](epl9-diagnostic-init-read-maintenance.md)
remains unchanged and explains why stock logical readers cannot simply be used.

## What changed in the reader

Original source is `firmware_src/epl9_bounded_read.s.in`; builder and runner are
`scripts/epl9_bounded_read.py` and `scripts/epl9_bounded_read_probe.py`. The
builder reuses the extended assembler utility from the separate SD study; it
does not build, modify or install the SD loader. Base `69200000` is synthetic.

The entry accepts a caller-owned context describing main `0100` or OSD `0101`,
page ordinal 0..12799 and an aligned 2048-byte DMA buffer. Logical component
starts are `406e0000` and `421e0000`. Each complete decoded envelope is
26214400 bytes, including its 32-byte header and trailer.

| Operation | Prototype behavior |
| --- | --- |
| Mapping | Same table relation as `604008a7` at `a03fdf80`; all indices <1024, at most 1024 hops, cycle/out-of-range failure |
| Submission | The reviewed single-page read packet `01402001`; one submission, no read retries |
| Completion | At most 256 register polls; unexpected extra completion bits are refused |
| Maintenance threshold | Sample low nibble >13 returns an error; never calls `604007b0` |
| Status | At most 64 status polls with finite ten-iteration delay; nonzero low five status bits are conservatively refused |
| Data validity | 2048 valid bytes published only after completion and accepted status |
| Unknown completion | Error plus quarantined context; no buffer release, reuse, forced reset or assumed DMA cancellation |

Only read and status commands are emitted. Native test memory restricts MMIO
writes to the reviewed five addresses, validates the exact three-word page
packet and permits only status command `70` afterward. The only native CALL
from this module is its own bounded mapping helper. No firmware read wrapper,
maintenance helper, erase/program routine, allocation or logging function runs.

The mapping table is immutable in these fixtures. Context word +24 declares
that the caller already owns the controller; **it does not implement a lock**.
Buffer address checks establish size/alignment/domain only, not real ownership
or the absence of aliases. No real allocator or cache/DMA coherence is proved.

States are idle 0, in-flight 1, data-valid 2, quarantine 3 and failure 4. Tests
interrupt the first call after its in-flight marker and reject a second call,
then resume the first successfully. This is not an atomic check-and-lock
proof: the caller still needs serialization before entry. Quarantine has no
automatic reset/retry path.

## Why a lower-level bound is not sufficient

Additional exact stock listings show that `6040113a` already limits its polling
counter to the branch following 65535, and status helper `604010f2` also has a
finite counter. Both can enter diagnostic output, whose full boundedness is
not established. The enclosing page/bulk loops retry failed reads indefinitely,
as demonstrated previously. The new module omits that retry and diagnostic path.

Its poll limits are experimental counts, **not calibrated elapsed times** or
recommended camera settings. A completion timeout leaves hardware ownership
and the potentially DMA-visible buffer quarantined. This prevents the tested
premature reuse but may prevent other NAND work until a qualified cancellation
or recovery sequence runs. Neither physical bus-read latency nor controller
abort/reset semantics are known from this test. No claim of a hang-proof camera
implementation is made.

The conservative status-bit rejection is a prototype policy, not a verified
interpretation of every NAND/ECC status bit. Matching and repeated component
bytes remain required; synthetic completion does not establish real data arrival.

## Native and host checks

Forty-four native cases include both components, first/last pages and a block
boundary, identity/one-hop/three-hop mappings, bad indices and a mapping cycle,
invalid component/page/buffer conditions, stale completion, completion timeout,
extra completion bits, maintenance thresholds 14/15, stuck/bad status,
quarantined reentry and one in-flight nested call. All terminate within the
explicit instruction limit, preserve stack/guards and issue at most one read.
DMA bytes are supplied by the fixture only after modeled completion.

`scripts/epl9_page_collection.py` defines the **host-side collection contract**,
not a new working camera protocol. It requires an explicit session, both
components, two passes, ordered page identities, stable expected mapping,
successful state/status and exactly 2048 bytes per page. Missing, duplicate,
reordered, wrong-session, wrong-mapping, short or failed pages cannot produce a
complete result. Existing `epl9_component_readback.compare` supplies the final
full-envelope comparison and keeps all provenance/physical-write flags false.

Five unit-test methods cover these boundaries and feed all 51200 page records
for each of the private-COLOR candidate and stock return: **102400 local page
records total**. A modified repeat is rejected. Those bytes come from existing
local packages, not the camera or 102400 native DMA executions. This validates
assembly/comparison only; the native tests above independently cover page logic.

## USB capture is conditional and needs its own bounds

The previously mapped admitted route is model-oriented debug shell output:
`902a`, selector 47, handler `60f5503b`, calling capture helper `604d5208`.
This investigation sends none of these commands.

Six new native RAM-only controls execute `604d5208`: empty, one byte, 2048
bytes, wrapped content, maximum non-full ring span and an undersized destination.
The helper consumes a 16 KiB capture ring, copies all currently available bytes
and appends one NUL. It has **no destination-capacity argument/check**. The
deliberately undersized fixture is overwritten past its declared capacity;
this is not an observed camera overflow. A full-capacity adapter must guarantee
enough response space, exclusive ring ownership and consistent framing. The
read cursor advances before the copy finishes, so a failed delivery also needs
an explicit retransmission strategy. Concurrent publication was not tested.

Thus the presence of this route does not make it a qualified export. Shell
session initialization still has the lens/wait effects described in the prior
report. Direct `9021 READ_DATA` remains excluded by the reviewed retail-MTP
admission table. No camera-side serializer, owned response buffer, capacity
contract or physical USB adapter is supplied by this pass.

## Remaining implementation boundary

The practical candidate design is a serialized, owned single-page reader plus
bounded export and the host collector above. To make it usable on the camera:

1. Bind a real buffer/context to controller exclusion and stable mapping,
   including cache/coherence and all cancellation paths.
2. Resolve an actual DMA stop/idle acknowledgement before releasing a timed-out
   buffer or controller. Merely changing state or clearing a register is not proof.
3. Establish a deployment/entry route and export adapter that also work for
   stock restoration verification. This synthetic module is absent from stock
   and both frozen candidates; it cannot currently bootstrap its own execution.
4. Qualify session effects and output capacity, then acquire both full envelopes
   twice and compare exact bytes. Physical return and no-boot recovery remain
   distinct from that comparison.

No firmware package is regenerated. Camera installation readiness remains
false. These remaining gates concern acquisition and ownership, not further
color fitting or invented TruePic pixels.

Reproduce the probes with new ignored JSON paths after retaining/building the
exact module and independently decoding it with the pinned GNU reader:

```powershell
.\.venv\Scripts\python.exe scripts/epl9_bounded_read_probe.py --out local/new-bounded-native.json
.\.venv\Scripts\python.exe scripts/epl9_capture_export_probe.py --out local/new-capture-copy.json
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_epl9_page_collection.py
```
