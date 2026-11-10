# E-PL9: 16 KiB blocks and ISC/TCP optimization constraints

Offline follow-up, 2026-11-02. No camera request, firmware edit, patch creation or flash. ART, video work, shared project guidance and other chats' scripts were not modified. Findings are from exact stock code; possible performance gains remain unmeasured.

Later the same day, [live stock-firmware measurements](epl9-wifi-live-20261102.md) confirmed approximately 1.8 MiB/s transfers and repeated 16 KiB body boundaries with about 2.3 ms median receive gaps after those boundaries. No candidate below was applied; those gaps do not isolate internal ISC/SD cost.

The subsequent [isolated offline prototype](epl9-wifi-offline-prototype.md) executes the native `r/rd` read paths and sector-request front on local ORF/MOV copies, plus two complete stock ISC-helper calls with explicit services. All six full-file variants match their sources; 21 tests include a 144-case read matrix and failure controls. Persistent ISC reuse remains a host model. The follow-up also records retained 128-byte physical control allocations, a successful-short-sector assumption and the absence of a wire generation tag. Statements below about missing execution describe the earlier static-audit stage; no camera speedup or installable patch is established by either stage.

## Result and priorities

Increasing the HTTP block is **not a constant-only change**. The selected physical allocator rejects anything above 16 KiB, its fixed pool has 16 KiB slots, and the three existing immediate loads are signed 16-bit. A direct `0x4000 → 0x8000` replacement would load **−32768**, not +32768.

There are narrower candidates at the existing 16 KiB size:

1. Use the existing read-only **`rd`** file mode for the HTTP original-body reader. The stock HTTP handler uses `r`, whose normal read path allocates a 16 KiB bounce buffer for each read and copies its contents. The `d` modifier selects a whole-sector read into the supplied buffer. A native consumer of `rd` already exists in this E-PL9 image. This is the smallest code-change candidate; it still needs execution and byte-identity validation.
2. Reuse the **reply queue and two small ISC objects** for an HTTP worker's lifetime. They are currently created/allocated and deleted/freed on every send. Preserve completion waiting and the request/buffer lifetime.
3. Consider **larger TCP enqueue batches**, while leaving the wire segment/MSS field unchanged. The current stream wrapper divides each 16 KiB send into per-connection-limit pieces, each with queue/semaphore/mutex/scheduling work. This could reduce local operations, but waiting for a larger free extent may change backpressure behavior. An HTTP-specific qualification is needed before any generic TCP change.

None is a demonstrated speedup or an installable patch. Simply deleting waits or shortening timeouts is not an optimization.

## Owner observation and its limits

The owner reports that two parallel video downloads each ran at roughly **1 MB/s**, with no benefit from parallelization. Preserve this result rather than recommending more parallel downloads. It is consistent with sharing a common bottleneck, but does not distinguish radio, ARM/MN103 scheduling, ISC, TCP or SD reads. MB versus MiB, the single-transfer reference, file sizes, durations and RF state remain unspecified. It is not proof of a programmed 2 MB/s rate cap.

## Exact input and address domains

- Model: **Olympus PEN E-PL9**, owner-reported displayed version **1.1**, stock download main build **1101**. Installed camera bytes have not been dumped.
- Stock container: `OLY_E_133_1101_0000_0000.BIN`, **104,552,480 bytes**, SHA-256 `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`.
- Decoded main `0x0100`: **26,214,336 bytes**, SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`. MN103 analysis address = file offset + **`0x60400020`**.
- Decoded common `0x0106`: **38,797,248 bytes**, SHA-256 `abd9d3f3e8598b3844b9b8d2c06d07ef49d5dbdb4cf00ca5dcaf096dcca659b8`.
- Embedded ARM module: decoded-common offset **`0x1ad4fe0`**, **270,336 bytes**, SHA-256 `11f9fe5b597248fc6cc3748d604d4108a316f59cc4381a4af4cff4d5f7452506`; ARM analysis base **`0x10000`**.

The follow-up script reads and rehashes the container and these two components. The other components' identities and prior five-component audit remain in [the first Wi-Fi report](epl9-wifi-transfer.md). ARM and MN103 addresses below belong to different domains. Labels are descriptive research names, not recovered symbols.

## Why a larger HTTP block is blocked

| MN103 site | Concrete constraint |
| --- | --- |
| `0x60f2efe2` | Loads 16384 into `d0` before allocating each of four HTTP send buffers through `0x6040240f`. |
| `0x60f30c6d`, `0x60f30c73` | Loads the read/send cap 16384 into `d1`/`d2`. Allocation and both limits must agree. |
| `0x6040242b..0x60402449` | `scheap_phyalloc` compares requested size with 16384; an unsigned greater-than branch logs `scheap_phyalloc: Size Over :` and returns null. |
| `0x60405f50` | Physical-pool descriptor: start `0xa21ba540`, payload size `0x4000`, **43 slots**, tag `0xdeb40000`. Free slots at runtime are unknown. |
| `0x60402756..0x60402769` | Slot-address calculation uses **16384 + 64 = 16448** bytes per slot. Two allocations cannot be treated as a contiguous 32 KiB payload. |
| `0x60402480..0x60402496` | Physical free dispatch recognizes the fixed range `0xa21ba540..0xa2267000`. Its extent is exactly `43 * 16448`. |
| `0x60402373..0x604023af` | The ordinary `scheap_alloc` wrapper also has a 16 KiB cap; changing to that wrapper does not solve the problem. |
| `0x60439cf3` | BSD send converts an AM alias in `0xa0000000..0xbfffffff` with mask `0x5fffffff`. An arbitrary cached/host-style pointer is not a qualified replacement. |

The block constants use `2c/2d/2e + imm16`, decoded as **signed** immediate moves. Synthetic decoder fixtures verified all three registers at 16384, 24576, 32767, 32768, 49152 and 65535. Values above 32767 become negative. A positive 32 KiB/64 KiB load needs a different instruction sequence/encoding and code-space/control-flow review; 24 KiB fits the old encoding but is still rejected by the allocator.

Resizing the global pool requires changing real storage reservation, slot arithmetic, bounds, allocation/free dispatch and users outside Wi-Fi. That would exceed a narrowly isolated HTTP change and could affect the concurrent ART work. No such change was made. A larger block would need a separately qualified physical buffer/allocator and matching cleanup. Request 6 currently carries **one pointer and one 32-bit length**, not a scatter/gather list, so allocating two separate slots does not coalesce them into one send.

## Existing `rd` route: a smaller candidate

The ordinary HTTP file-body path at **`0x60f30beb`** loads mode pointer **`0x61265c4c`**, which contains `r\0`, and calls the file-open wrapper at **`0x60f30bf1 → 0x609ce1c8`**. The special `do_file_status` path also uses that literal; the candidate concerns only the ordinary body-open call.

| MN103 site | Evidence |
| --- | --- |
| `0x609dcdbc` | File-open implementation initializes mode flags to zero and parses the mode string. |
| `0x60a8c2b4` | Mode table maps `r` (key `ord('r')-42 = 72`) to `0x609dce73`, which adds read flag 1. |
| `0x60a8c2c4` | Mode table maps `d` (key 58) to `0x609dcea1`; `0x609dcea4` adds flag mask **`0x10`**. `b` is a different modifier and does not select this flag. |
| `0x609dcfdb..0x609dcfe9` | Parsed flags are stored at file object **+312**. |
| `0x609de02e..0x609de042` | Read implementation tests mask 16 (`0x10`), selecting `0x609de148` when set and `0x609de04f` otherwise. These are bit masks, not bit-index 16. |
| `0x609de0a7..0x609de0aa` | Ordinary path allocates a fresh 16 KiB physical bounce buffer. |
| `0x609de0c0..0x609de0d4` | Ordinary path reads in groups of at most **32 × 512-byte sectors** into that temporary buffer. |
| `0x609de105..0x609de135` | Copies the resulting bytes into the caller's buffer, then frees the temporary block. |
| `0x609de22e..0x609de242` | `d` path submits whole sectors directly to the caller destination, advanced by any already-copied leading bytes. |
| `0x609de258..0x609de29f` | Trailing partial sector is read through the file's sector buffer, then only the requested tail bytes are copied. |
| `0x60a8ba0c` | An existing stock `rd\0` literal. `0x609d9e7d..0x609d9e86` supplies it to the same open wrapper, followed by a 512-byte read at `0x609d9eaf`. |

This supports `rd` as a **native existing read path**, not an invented CGI command or a setter. It does not establish live HTTP performance or data identity. Pointing the body-open operand to a qualified `rd` literal would preserve instruction width and avoid changes to shared filesystem code. Do not overwrite `r\0` in place with a longer string: the following bytes belong to another format string.

Keeping the 16 KiB block means full sequential reads start at 512-byte boundaries and request 32 whole sectors. Arithmetic for the historical test sizes is:

| Original | Full 16 KiB reads | Final read | Full sectors in final read | Final partial bytes |
| --- | ---: | ---: | ---: | ---: |
| ORF, 14,692,005 bytes | 896 | 11,941 | 23 | 165 |
| JPG, 3,249,056 bytes | 198 | 5,024 | 9 | 416 |
| MOV, 8,105,416 bytes | 494 | 11,720 | 22 | 456 |

These are calculations, not executed camera reads. Short reads, sub-sector files, unaligned initial positions, physical-buffer/cache coherency, error paths, EOF and mode-specific side effects still need qualification. The direct-read routine falls back to the ordinary path for requests with no whole sectors. Do not add the separate `e` modifier: its `0x20` flag can round the final sector behavior. The proposed mode remains read-only `rd`.

For the ordinary `r` path, the full ORF entails at least **897 body sends** and a MOV **495**, plus headers. Each successful full-body read reaches the bounce-buffer allocation/free path, unless file flags have been changed by another runtime owner. No such runtime flags were observed. `rd` removes that particular full-block bounce step; it does not remove the SD read, its control request, the ARM TCP copy or the radio transfer.

## ISC: removable setup and mandatory completion

The 16 KiB data block is not copied through an ISC message of that size. Control request and reply are **64 bytes**. The request carries the shared data address and **32-bit** length; ARM prepares cache lines rounded to 128-byte boundaries through `0x2bb28`. The control packet size is therefore not the source of the 16 KiB application limit.

For each call to synchronous helper **`0x60f31364`**:

| Main site | Per-call work |
| --- | --- |
| `0x60f31368..0x60f31375` | Creates a reply message buffer/queue through `0x60f31258 → 0x60410269`; tracks its ID in a 64-entry cleanup table. |
| `0x60f31378..0x60f31382` | Allocates a 16-byte envelope and 12-byte reply object through `0x60f312fa → 0x604024ab`; that allocator supplies 128-byte shared slots. |
| `0x60f3138c..0x60f313aa` | Publishes reply queue ID, caller/task information, flags and request-frame pointer. |
| `0x60f313ba` | Sends the 16-byte local envelope to the network work queue, with timeout argument **−1**. |
| `0x60f313d8` | Waits for the reply on the per-call queue, also with argument **−1**. |
| `0x60f313f5`, `0x60f313fc`, `0x60f31405` | Frees both objects and deletes the reply queue. |

The network pump at `0x60f31171` takes the envelope, fills reply ID/request return address in the request, and sends 64 bytes on ISC channel **3**. The reply pump at `0x60f311c4` receives 64 bytes on channel **4**, copies the returned request frame back at `0x60f31204`, and publishes the 12-byte completion to the local reply queue at `0x60f3121b`.

ARM handler **`0x2667c`** prepares the source buffer, calls BSD send, stores its result, and sends the reply. The ordinary send's success means its input bytes have been consumed/copied into TCP queue storage. It does not mean all radio ACKs have arrived. The MN103 HTTP buffer and request stack frame must remain valid until this completion; returning early lets the next SD read overwrite bytes still being consumed.

A worker-owned reply queue and two objects could remove **one create/delete plus two allocations/frees per send**, without removing either the send/reply protocol or its completion boundary. It needs a dedicated HTTP helper, one outstanding request per context, correct CPU/queue ownership, teardown after pending completion, and rejection/reconciliation of stale replies. Reuse after an ambiguous timeout must not deliver an old response as the next request's result. No implementation or timing validation exists yet.

`−1` is passed as a wait policy, not a fixed sleep inserted once per block. Replacing it with a shorter timeout can cause transfer failures; it does not make the peer finish sooner.

## TCP: queue space, batching and fixed buffer geometry

In the ARM domain, **`0x12bcc`** splits each stream send by the value at TCP object **+0x64**, loaded at **`0x12c20`**. Each piece calls **`0x1e9a8`**. This is a segment/MSS-like limit: helper `0x1d334` has fallback 536 and computes a path-derived value minus 20, with connection setup negotiating a minimum. The live value is unknown; **1460 is an example, not a camera measurement**.

At limit 1460, one 16 KiB HTTP block would use **12** internal enqueue calls (11 × 1460 + 324). A larger HTTP block reduces ISC message count, but these lower enqueue calls still scale approximately with bytes/segment-limit. It is therefore insufficient to focus only on the HTTP constant.

| ARM site | Constraint or work |
| --- | --- |
| `0x1ea30..0x1ea38` | Each queue operation waits on the send semaphore, even though an available token may make the call return immediately. A call is not evidence of actual sleeping. |
| `0x1ea14..0x1ea24` | Under the object lock, compares requested amount against **capacity − queued**. Insufficient space goes back to waiting. |
| `0x1eaac..0x1eb08` | Copies data into a circular buffer, updates queued count at +0xc0 and pending state. |
| `0x1eb0c → 0x1d264` | Re-signals writable state when space remains; there is no compulsory one-ACK-per-enqueue wait when enough space is available. |
| `0x20b0c..0x20b2c`, `0x20bac..0x20bb8` | ACK processing advances queue position, decreases queued count and wakes the send waiter. |
| `0x1f6b8` | Schedules transport work; it does not create free queue capacity. |

The compiled stream-socket bank has **ten 32 KiB send buffers and ten 32 KiB receive buffers**. This binding is stronger than the earlier literal-only observation:

- Socket type 1 selects bank indices 10..19 at `0x13ea4`.
- Setup at `0x13e10..0x13e38` uses size and stride **0x8000** for those bank entries; send-area base is `0x151574`, receive-area base `0x101574`, each area is `0x50000` bytes.
- Accepted connection creation calls `0x13ea4(1)` at `0x1dc4c`, then `0x13e48` at `0x1dc7c`.
- Binder `0x13e48 → 0x1f138` copies the selected pointer/length into the TCP object; send capacity becomes object **+0xc4**.

This proves the reviewed default initialization/binding path, not current live occupancy or exclusion of later reconfiguration. Increasing just the 0x8000 capacity can overlap the next socket buffer: allocation stride and reserved areas must also change. Doubling all twenty buffers would need another **640 KiB** plus a reviewed memory map. No such free region has been qualified.

The existing BSD option setter **`0x13b9c`** is not a shortcut: `0x13bd4` rejects levels other than **−1**. The conventional TCP-level 6/option 1 (`TCP_NODELAY` on this host) is rejected by this route. At level −1, conventional send/receive buffer options **0x1001/0x1002** also fail its option filter (`0x13c24..0x13c38`). Supported timeout/control options do not dynamically resize these buffers. Default socket timeout fields are initialized with **60000** at `0x13f20..0x13f74`; the send path reads its timeout from BSD object +0x40. This is not an unconditional 60000-unit delay before each send.

A distinct batching candidate is to let the **local enqueue amount** exceed the segment-limit while remaining bounded by real queue capacity, leaving TCP +0x64 and wire segmentation unchanged. For the known 16 KiB request and default 32 KiB queue, one 16 KiB enqueue could replace multiple small enqueues. This must preserve circular-copy correctness, error/timeout handling, flags and source ownership; it can also wait for a larger amount of space before starting. Replacing the generic +0x64/MSS field itself is not this optimization. A global wrapper change would affect other TCP users, so an isolated HTTP/normal-copy path is required for any later prototype.

## What can and cannot be reduced

| Candidate | Eliminates | Does not eliminate | Status |
| --- | --- | --- | --- |
| HTTP `r → rd` operand | Full-block bounce allocation/free and memory copy in the selected filesystem path | SD request, ISC completion, TCP copy/backpressure | Existing native route and mode consumer found; best narrow candidate for execution qualification |
| Persistent HTTP ISC reply context | Per-send queue creation/deletion and two object allocations/frees | Actual request/reply and data ownership wait | Concrete lifecycle sites found; needs an isolated implementation |
| Larger local TCP enqueue batches | Repeated semaphore/lock/copy-dispatch/scheduling overhead per segment-like piece | Queue capacity, wire segmentation, radio/ACK throughput | Algorithmic candidate; batching/latency and error semantics unverified |
| 16 KiB prefetch/double buffering | Possible serialization between next SD read and current send completion | A shared SD/ISC/radio bandwidth ceiling | More complex; extra physical slots and pending-request lifetimes must be qualified |
| Larger HTTP block alone | Some per-block ISC calls, in theory | Allocator, encoding, lower per-piece TCP work | Blocked by exact stock constraints |
| Remove completion/space waits | Nothing safely established | Buffer ownership and capacity | Reject: can corrupt output or overrun the queue |

The owner observation gives no basis for promising any factor of improvement. Which removable cost dominates requires timings/captures when hardware becomes available. This follow-up identifies changes worth modeling and the exact invariants they must preserve.

## Reproduction and validation

```powershell
.\.venv\Scripts\python.exe .\scripts\epl9_wifi_limits.py `
  --out .\local\wifi-limits-new
```

Output for this investigation is `local/wifi-limits-20261102-v6/`: **31 listing/fixture windows**, an `audit.json`, and synthetic instruction bytes. The script verifies **57 MN103 anchors**, **38 ARM anchors**, the physical-pool descriptor/extent, HTTP `r` mode, native `rd` literal/parser binding and **18 synthetic immediate/register cases**. It records arithmetic read shapes for the historical originals. These checks do not execute a camera, the full filesystem, TCP stack, ARM cache or a modified firmware path.

The GNU MN103 reader and isolated Capstone 5.0.6 provenance are unchanged from the first Wi-Fi report. Firmware and extracted disassembly remain ignored. No patch bytes or repacked update were produced.
