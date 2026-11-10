# E-PL9: offline `rd` and persistent ISC prototype

2026-11-02. The isolated runner is [epl9_wifi_prototype.py](../scripts/epl9_wifi_prototype.py); its checks are [test_epl9_wifi_prototype.py](../scripts/test_epl9_wifi_prototype.py). No camera access, firmware writes, repacking or flashing. No ART code or shared interpreter changes. The existing generic MN103 interpreter is imported read-only and its source hashes are recorded before/after the run.

**Result:** actual stock read instructions produced identical ORF/MOV bytes with both `r` and `rd`. For full 16 KiB reads, `rd` eliminated the bounce allocation/free and copy. The separate host ISC prototype reduced queue/object construction to once per worker context while preserving every send-completion boundary. This is a validated local experiment, **not a measured camera speedup or an installable implementation**.

## Exact inputs and retained output

Model: Olympus PEN E-PL9. Owner-reported displayed version **1.1**; downloaded main internal build **1101**. The installed image has not been dumped.

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| Stock `OLY_E_133_1101_0000_0000.BIN` | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Decoded main `00_0100_406e0020.decoded.bin` | 26214336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |
| Local ORF from the earlier stock-camera Wi-Fi session | 14692005 | `1deed5a996e6b3d0d724425ef76b8703a37b8130a3a4cb2c9344c6b691a79946` |
| Local MOV from that session | 8105416 | `2adb950f5ae41bf92fa01f921fb8ca06056ee8094e389e83dc266e3ad4877ad0` |

The media are previously downloaded camera copies, **not independent card-reader originals**. Identity here means that the prototype reproduces those exact local reference bytes. Main analysis base is `0x60400020`. Both firmware size/hash gates run before execution.

Retained full-file run: ignored `local/wifi-prototype-20261102-v1/results.json`. It contains input/source/listing hashes, mode flags, six file variants, native instruction counts, allocation/copy/send counts and explicit model/limitation fields. Input/listing/firmware bytes remain in ignored directories. GNU listings are reused from the [exact-stock limits audit](epl9-wifi-transfer-limits.md), `local/wifi-limits-20261102-v6/`; every loaded instruction's raw bytes are compared with the exact main image before execution.

## What executes and what is modeled

The test executes native branches and arithmetic using the bounded MN103 CALL interpreter; it is not a complete camera, CPU timing model, RTOS or DMA emulator. Unknown calls/instructions/accesses stop. Every external service has a named, ABI-checked model. No model shadows loaded native instructions.

| Stage | Executed stock code | Explicit external boundary |
| --- | --- | --- |
| Mode parser | `0x609dce39..0x609dcec5`, including ROM dispatch table | Synthetic mode pointer, initial flags 0; stops before filesystem open |
| `fread` dispatch | `0x609ddff6..0x609de04f` | Declared valid file; full public `fopen`/file routing not executed |
| Buffered/direct read | `0x609de04f..0x609de2b1` | Bounded memcpy and finite physical allocations |
| Sector-request front | `0x609dd646..0x609dd7c2` | Storage request service `0x609b9b40`, volume lookup `0x609b9ef8`, status diagnostic `0x609d4f0b` |
| Stock ISC per-send helper | `0x60f31364..0x60f3140f`, two complete calls/returns | Queue/allocation/task/synchronization fronts and request/reply pumps |
| Proposed persistent ISC helper | **Host Python model only** | Fake byte-consuming backend; no proposed MN103 instructions assembled or run |

File fixtures explicitly provide size at **fd+268**, nonzero storage descriptor at **fd+288**, position at **fd+308**, flags at **fd+312**, and sector-cache pointer/count/index at **+480/+484/+488**. The `inc4 a0; mov (284,a0)` access is fd+288, not fd+284. Other metadata remains declared fixture data: volume ID 0, 64 sectors per synthetic geometry unit, no cached physical-cluster mapping. The storage model copies local sectors, fills the native request's returned count, and poisons bytes beyond logical EOF. This does not validate FAT/SD/fragmentation, large-file routing, interrupts, cache coherency or DMA destination constraints.

The HTTP destination is a bounded physical-alias fixture with 64-byte alignment and guards. All ordinary/direct outputs are compared byte-for-byte with independent Python slicing; bytes after reported length must remain poisoned. The file position, native stack return, allocation ownership and output guards are checked on every read. Models preserve unspecified volatile registers/flags; this is a host ABI assumption, not observed RTOS behavior.

## `rd`: concrete intervention and limits

The native parser yields **`r = 0x01`, `rd = 0x11`**, executing 30 and 58 instructions respectively. The additional bit selects the direct branch at `0x609de032..0x609de039`.

The normal HTTP body opens with the pointer load at **`0x60f30beb`**, passing `r\0` at `0x61265c4c` to `0x609ce1c8`. Existing `rd\0` at **`0x60a8ba0c`** is used by another stock caller. A future narrow body-reader intervention could redirect the four-byte operand at **`0x60f30bed`** from `4c 5c 26 61` to `0c ba a8 60`, retaining instruction length. **The runner does not perform this edit:** it executes the parser on a supplied mode string and supplies the resulting flags to its declared file fixture. It does not execute the entire HTTP/open chain or establish permission to install a patch. Do not overwrite the shared two-byte `r\0` string with a longer string. Do not add `e`: flag `0x20` changes tail rounding.

| Local file / variant | Read calls | Bounce allocations/frees | Copied bytes in read backend | Sector/control requests |
| --- | ---: | ---: | ---: | ---: |
| ORF, `r` | 897 | 897 pairs | 14692005 | 897 |
| ORF, `rd` | 897 | 0 | 165 | 898 |
| MOV, `r` | 495 | 495 pairs | 8105416 | 495 |
| MOV, `rd` | 495 | 0 | 456 | 496 |

Both modes reproduce the entire source file. The `rd` results also remain identical when attached to the persistent ISC host model.

**The lower control allocation remains.** `0x609dd64c..0x609dd64f` asks `scheap_phyalloc` for **128 bytes**, and `0x609dd7a4..0x609dd7a5` frees that control request. This allocator supplies a slot from the physical pool whose blocks are 16 KiB. Executing this front confirms that switching to `rd` does not eliminate physical allocator traffic. The final `rd` read splits whole sectors and a partial sector into two requests, one more than `r` for these files. The remaining partial-sector scratch copy is 165 ORF bytes / 456 MOV bytes. Sub-sector-only reads fall back to the buffered routine and can still allocate its bounce buffer.

Keep the **16 KiB** HTTP block. This prototype does not enlarge the pool, change signed immediates, TCP limits, SD requests or ARM copies. Interpreted instruction counts (ORF `217513 → 202421`, MOV `120028 → 111770`) exclude modeled memcpy, storage, allocation and scheduling costs. They must not be translated into camera CPU savings or goodput.

## ISC reuse: lifecycle prototype

The stock helper creates a reply queue at **`0x60f31370`**, allocates a 16-byte envelope and 12-byte completion object at **`0x60f3137a/0x60f31382`**, publishes at **`0x60f313ba`**, waits at **`0x60f313d8`**, then frees both objects and deletes the queue at **`0x60f313f5/0x60f313fc/0x60f31405`**. The shared allocator uses 128-byte slots. The two native helper calls completed with two creates/deletes, four slot allocations/frees, two publications and two completion waits, with balanced stacks.

The stock request pump supplies queue ID and return-frame address before channel-3 publication; the channel-4 reply pump copies the result back and signals completion. The local model validates the native helper's **16-byte envelope** and **64-byte BSD send frame**, including opcode 6, socket, AM shared-address conversion, length and flags. The native helper receives a synthetic BSD caller frame; unused words are explicitly zero in this fixture, not claimed initialized by every native BSD caller.

`IscContext` allocates one queue and two slots at construction, retains them while idle, and releases them after the last completed request. It supports four separate worker fixtures, with distinct request addresses/queue identities. Constructor failures at each allocation step roll back already-owned resources. It allows only one outstanding request per context. Publishing retains the mutable source and its fingerprint; a new send, teardown or changed source is rejected before completion. Short sends require another completed request for the remainder. An error completion consumes no bytes in the declared fixture.

| File / lifecycle | Queue create/delete pairs | Small-slot allocation/free pairs | Send publications / completion waits |
| --- | ---: | ---: | ---: |
| ORF, per-call baseline | 897 | 1794 | 897 / 897 |
| ORF, persistent prototype | 1 | 2 | 897 / 897 |
| MOV, per-call baseline | 495 | 990 | 495 / 495 |
| MOV, persistent prototype | 1 | 2 | 495 / 495 |

These are **construction-operation counts**, not removed waits or milliseconds. Teardown is once per context in this harness; four retained workers would consume four queues and eight small slots simultaneously. Their availability, task ownership, locks, cleanup registration and shutdown sequencing on the actual camera remain unverified.

Publication rejection can release the source only when rejection before dispatch is established. An ambiguous timeout enters **quarantine**, retaining the source/request/resources and refusing reuse or close until the matching completion is drained. No timer alone converts this state to idle. The actual stock wait remains indefinite; neither timeout shortening nor removing waits is proposed. Completion means input has been consumed/copied by the send path; it does not mean every radio/TCP ACK arrived.

**Wire-generation limitation:** host tickets carry a test sequence number to detect mistaken/stale test callbacks. No generation number is added to the camera protocol. A deliberate negative control proves that two successive identical sends on the same persistent queue/request address have **identical wire frames**. Consequently a late duplicate raw reply after successful reuse cannot be disambiguated by the host sequence number. Exactly-once ordered completion, queue draining and cancellation/shutdown behavior must be established from native transport before translating this model to firmware. The prototype does not claim to have solved that protocol issue. Four-worker tests prove model separation, not multi-core/RTOS correctness or extra radio throughput.

## Local validation and failure controls

**21 tests passed**, with no skipped native cases on this workstation. These include a **144-case native read matrix**: modes `r/rd`, offsets `0/1/127/511/512/513/EOF−1/EOF`, counts `0/1/7/511/512/513/1024/16383/16384`. All expected slices, EOF positions, guards and balanced releases passed. Additional tests cover full-block allocation/copy removal, partial/error reads, physical exhaustion, forbidden block/position, two native ISC helper returns, four-worker separation, delayed completion, source mutation, short send, failed construction, foreign/double callbacks, proven rejected publication and ambiguous timeout retention.

The following controls intentionally expose unsupported contracts rather than conceal them:

- Injecting status **0 with returned sector count 0** on the final one-sector scratch read makes native `rd` copy the poisoned scratch byte and report success. The one-sector head/tail consumers at `0x609de203..0x609de223` and `0x609de27e..0x609de29f` check status but do not require returned count 1. The outer sector front copies the returned count at `0x609dd74b..0x609dd74f` and does not add that requirement. Whether lower storage service guarantees a complete sector on status 0 is **not yet established**. This is a synthetic violation, not an observed camera SD corruption. Test success means this assumption was exposed, not that corruption is acceptable.
- Repeated successful zero-progress reads make the buffered loop hit the interpreter's instruction limit. A single short/zero result can be retried by that loop; zero progress cannot be silently treated as complete data.
- Physical allocator failure stops on native use of the missing allocation. No automatic-success substitute or fake storage result is supplied. Actual exhaustion/recovery behavior remains unqualified.
- Host ticket rejection is not evidence of wire-level late-duplicate rejection; the equal-frame negative control is retained explicitly.

These limits prevent calling the prototype a validated camera patch. The smaller `rd` intervention has concrete executed evidence and fewer lifecycle changes than ISC reuse. Its remaining qualification includes lower successful-sector semantics, real physical/cache/DMA behavior, full native open/HTTP routing, cancellation and file/error cases. ISC reuse additionally needs an actual worker lifecycle and transport completion contract. Nothing here establishes which portion of the previously measured ~1.8 MiB/s / recurring 16 KiB receive gaps is removable; see [stock-camera measurements](epl9-wifi-live-20261102.md).

## Reproduce

Use the exact ignored inputs/listings and a **new** ignored output directory. The runner opens local files only; its full-file run does not import the network bench or contact the camera.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_epl9_wifi_prototype.py -v
.\.venv\Scripts\python.exe scripts/epl9_wifi_prototype.py --out local/new-wifi-prototype-run
```

The native test class is explicitly skipped if its ignored listing fixture is absent; portable ISC lifecycle tests still run. A skipped native class must never be reported as a passed exact-stock execution. Neither command produces a modified firmware/update input.
