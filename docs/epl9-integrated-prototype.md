# Revised offline prototype: preserved schedules and native call chains

## Result, 2026-11-02

The revised host experiment removes the four schedule regressions found in the first prototype. It also runs the worklist builder from its actual entry, preserving earlier optimized paths that the original branch-only experiment did not reach. Both recipe slots execute native COLOR selection, table packing and returns with a complete 5200-byte output comparison.

**The complete image-processing cycle has not passed.** The [hardware-boundary follow-up](#native-parameter-object-color-and-hardware-boundary-2026-11-02) connects job creation, frame start, native parameter-object construction, cache comparison and COLOR execution. Eight cases with attached diagnostic tables reach the first unmapped peripheral write. The later owner-slot follow-up below supplies the missing outputs for four further cases and traces their configuration rejection through consumer cleanup to an OS event wait. No pixel image, JPEG, live view or calibrated Gold/Portra rendering was produced. This is offline analysis, not a firmware patch. Earlier stopping points below are retained as historical results.

## Inputs and execution boundary

Exact input: Olympus E-PL9, owner-reported displayed version **1.1**, downloaded main build **1101**. The installed firmware has not been dumped.

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| `OLY_E_133_1101_0000_0000.BIN` | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Decoded main | 26214336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |

Candidate main mapping is `0x60400020`, not measured RAM. Runners read and hash-check the decoded main and record the container identity from the prior audit. They verify 43 GNU decode anchors, and the integrated runner rejects conflicting overlapping listings. Reader SHA-256 is `e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae`.

The opt-in `mn103_calls.py` extends the existing interpreter with CALL, CALLS, RET, RETF and MOVM for the d2/d3/a2/a3 save masks. Stack behavior follows the pinned [GNU instruction semantics](https://gnu.googlesource.com/binutils-gdb/+/87ffb882e0f4d73401a0746177ffabb8e8bbe4ac/sim/mn10300/mn10300.igen), SHA-256 `355754c61879dc24bf6128bbba5a7931355731000e8cb213082b9b9cd4df0129`. CALL saves below the original SP but adjusts SP by the encoded frame size; CALLS leaves SP unchanged; RET reads the stack return address and RETF uses MDR. Unsupported masks, instructions, memory and absent callees stop execution. No missing function is replaced by a success return.

Synthetic caller frames, job RAM, descriptors and parameter objects are supplied by the harness. This is not a complete MN103/AM33, RTOS or ISP emulator. The old `Machine` still stops at call/return boundaries unless the new opt-in engine is used.

## Routing change and preserved services

The original key remains intact while the native worklist builder evaluates early paths and Watercolor type checks. Only exact keys `0x01010078` and `0x01020078` are eligible for replacement.

If execution reaches `0x60752202`, the host redirects it to `0x607523a5`, the ordinary branch. The current list index and registers remain intact; subsequent native effect-flag logic still runs. If the Watercolor-pass branch is never reached, no redirection occurs. After worklist construction, the harness changes both the job header at +12 and cached key at +10384 to 11, retaining the original recipe identity in host state.

This deliberately separates scheduling from the effective color key. It is not a proposed binary edit, an installed hook, or proof that each optimized path consumes COLOR. The consistent key handoff and eventual attachment of a recipe object still need a native implementation and real caller evidence.

At the old branch-entry boundary, the four already-ordinary cases retain their exact original worklists. The historical blanket key substitution is still reproduced as a negative regression check and still changes four cases. Effect flags matter: the retained short branch and default branch can use different intermediate flags that decide whether a callback is attached or another entry appended. Comparing only function addresses would miss this; all three words of each entry are compared.

From the complete builder entry `0x607519b8`, zero-flag target cases produce these schedules after initialization `0x6075199d`:

| Type | Selector | Revised schedule after initialization |
| --- | ---: | --- |
| `0x0200` | 0 | `0x60751319` |
| `0x0200` | 2 | `0x607518c5 → 0x607511db → 0x607518d3 → 0x60751930` |
| `0x0100` or `0x0040` | 0 | Original early path: `0x607511e9` |
| `0x0100` or `0x0040` | 2 | Original early path: `0x6075124b → 0x607511db → 0x60751259` |

The last two rows are newly executed early paths, not contradictions of the previous experiment entered later at `0x60751eb2`. They retain completion/event-31 handling and pending-handle forwarding. Every nonredirected job is compared byte-for-byte against stock, except the two explicit mode-key fields. Redirected lists match the corresponding ordinary reference in the tested states.

The existing [service contract](epl9-service-dependencies.md) remains in force: pending-request completion, owner callbacks including event 31, status/cancellation handling, buffer ownership, balanced parameter-object references, and table lifetime must survive the replacement. Passing worklist comparisons does not prove completion or DMA behavior. All 11 bounded service checks are rerun without expanding their stated scope.

## What passed and where the full cycle stopped

| Check | Result and scope |
| --- | --- |
| Original branch-entry grid | 30 stock/proposed pairs; zero short-schedule regressions |
| Effect-flag grid at that boundary | 1050 cases: five keys × three types × two selectors × 35 flag values (zero, each single bit, two combinations) |
| Complete native worklist builder | 120 stock/proposed pairs, including calls and returns: same key/type/selector grid × flags 0, `0x10000`, `0x20000`, `0x30000` |
| COLOR integration for each target | `0x6079ebcc → 0x6079e50e → selector return → synthetic caller`, 1155 instructions per slot; full output and restored SP/saved registers checked |
| Existing numerical coefficient tests | 180 saturation cases and two full-table packing cases pass |
| Existing service components | 11 bounded checks pass; still separate from full processing |
| Seeded job execution | 12 attempts, both targets × three types × two selectors; initialization entry completes, then each stops at the unmodeled helper `0x4700111e` |
| Pre-cancelled job | All 12 return error `0x9e01`, mark cancellation, and execute no worklist entries |
| Native job constructor | Stops at allocator call `0x6074df0c → 0x60402373`, before allocation |

Executor stop sites are `0x60751346` (ordinary short worker), `0x6076390c` (long/early worker) and `0x60750b30` (early short processing), all calling `0x4700111e`. Its observed arguments are consistent with a memory-fill helper, but its body is not in the loaded main window. These are currently software/coverage boundaries, not measured hardware failures. The complete constructor was not connected to the separately seeded executor or COLOR tests. Successfully simulating the allocator/fill would not by itself establish the remaining pipeline or ISP behavior.

The COLOR checks use two different synthetic table markers, +50 and -50 in one field. The object, enabling flag and table are supplied by the harness, with the table kept alive through the call chain. This verifies neither native object attachment/refcount integration nor hardware consumption of the LUT pointers. It does not define the Gold 200 or Portra 400 recipes.

The grid does not exhaust every job field, mode or combination of effect flags. Preview/capture caller mapping, optimized-path color consumption, actual pixel processing, error recovery after submitted requests and on-camera execution remain unverified.

## Reproduction and next concrete work

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p 'test_mn103*.py' -v
.\.venv\Scripts\python.exe scripts/epl9_offline_prototype.py --out local/new-bounded-prototype
.\.venv\Scripts\python.exe scripts/epl9_integrated_probe.py --out local/new-integrated-probe
```

Use a new ignored output directory and keep assertions enabled. Retained runs are `local/offline-prototype-20261102-v4/results.json` and `local/integrated-probe-20261102-v2/results.json`. Six new ABI tests plus the ten existing subset tests pass; they validate the implemented conventions against synthetic inputs, not the hardware CPU.

Next: resolve the allocator/fill dependencies or add explicitly labeled, independently checked software models; continue native request creation/submission until the actual external processing boundary is understood. Then trace where each retained optimized path obtains color, connect a recipe table with its native ownership/flag contract, and test pixels. Do not bypass errors or report a mocked success as a complete cycle.

## Follow-up: explicit software contracts and deeper native execution

The subsequent `--software-models` run advances beyond the earlier memory dependencies. It does **not** complete image processing. `mn103_calls.py` still stops at absent code by default. Opt-in models cannot shadow decoded native code; every use has a separate `modeled_call` event rather than appearing as a native instruction execution.

The actual allocator front at `0x60402373..0x604023b2` is now executed. Its 14552-byte request selects pool ID `0x10004` (16384-byte size class), then calls `0x60402595`. The host model supplies exactly one predeclared 16 KiB block, initially filled with `0xa5`, or an explicit null allocation. It rejects a second allocation, another pool ID and an ABI mismatch; it is not a simulated heap or RTOS pool implementation.

The assumed byte-fill helper at `0x4700111e` validates its entire destination before changing memory and rejects writes outside a writable region or into its pending call frame. It records each address, count and byte. Its assumed volatile effects advance a0 by count, zero d1 and preserve d0/a1/flags; the missing E-PL9 implementation's actual clobbers are not established. The allocation model sets a0 and otherwise retains volatile registers/flags. These explicit assumptions limit the conclusions even when caller stacks and memory checks pass.

Both keys, with synthetic task-byte values 0 and 7 at the read-only cell `0x8050`, now execute the constructor through **11 fills**, 32-byte parameter copying, mode-key caching and task-byte assignment. All expected cleared spans, copied parameters and the unused allocation tail are checked. Execution stops at `0x6074e066 → 0x6073e562`. Separate disassembly identifies that callee as another constructor requesting **5764 bytes** and calling an initializer at `0x6073e588`; this second object and its lifetime are not yet modeled or integrated. The forced first-allocation failure returns zero, writes error `0x9ec3`, restores SP and touches neither the job block nor the fill helper.

The executor additionally runs native buffer-slot lookup (`0x6074acf9`), dimension selection (`0x6075088e` / `0x607509b0`) and type classification (`0x607a3c9e`). Current exact stopping points, identical for Gold and Portra in the synthetic grid:

| Type / selector | Stop at call site → absent callee | Executed instructions |
| --- | --- | ---: |
| `0x0200` / 0 | `0x607508bd → 0x60749187` | 214 |
| `0x0100` / 0 | `0x607508bd → 0x60749187` | 231 |
| `0x0040` / 0 | `0x60750942 → 0x607491d5` | 238 |
| All three / 2 | `0x6074f2ab → 0x60750498` | 1434 |

These are **software coverage boundaries**, not identified ISP/DMA boundaries. Only initialization completes as a worklist entry. The executor still starts from a separately seeded job with mostly zero fields; buffer descriptors and owner state are not measured camera state. More executed instructions do not demonstrate a valid submitted request, a connected constructor/executor, optimized-path COLOR consumption, a finished pixel frame or a JPEG.

Revalidated: 120 complete-builder pairs, both 5200-byte COLOR results, 12 pre-cancellation paths and all 11 bounded service checks. Five additional synthetic model tests check range rejection before mutation, zero-length fill, canaries, preserved saved registers/stack, allocation failure/exhaustion and ABI rejection. No unknown image-processing call returns automatic success.

```powershell
.\.venv\Scripts\python.exe scripts/epl9_integrated_probe.py --software-models --out local/new-modeled-probe
```

Retained final follow-up run: `local/integrated-probe-20261102-v5/results.json`. Next connect the real descriptor/dimension/owner inputs and the second object's lifetime, then continue to the request consumer. Keep `full_pixel_cycle_passed` false until there is actual pixel output with independently checked behavior.

## Connected constructor, frame start and consumer, 2026-11-02

This checkpoint is retained for provenance; the later hardware-boundary results below supersede its configuration-call stopping points.

`scripts/epl9_job_probe.py` now connects the **native constructor → native frame start → native worklist executor → request creation → consumer configuration**, with explicitly modeled host resources. It does not claim that a request returning zero, a cursor advancing, or an allocated event token constitutes pixel completion. The input is the same exact E-PL9 1.1/build-1101 main identified above; all work is offline.

### Second object and frame lifecycle

The constructor at `0x6074df04` now returns a job after both allocations: 14552 bytes for the job and 5764 bytes for the object referenced by `job+12316`. The native size-class front selects the same 16384-byte pool for both. The host supplies two separate predeclared slots, initially poisoned with `0xa5`; it cannot allocate a third. This object is distinct from the recipe/parameter object at `job+12320` and from the owner callback context.

The second object's actual initializer `0x6073e588` writes sparse cache defaults, including `0xffff`, `0x8001` and `0x81` sentinels. It does not clear the whole object. Its comparison function `0x6073e6ac` examines the current request and returns a mask of settings needing update; `0x6073e953` stores the comparison fields. Thus a zero-filled replacement is not equivalent to native initialization. The 1832-byte unused tail of the job slot and 10620-byte unused tail of the cache slot remain untouched in the tested cases.

Crucially, the constructor parks the worklist cursor `job+10388` at **16**. The frame-start function `0x6074e348` resets it to zero, resets pending/buffer state, executes installed native callbacks, computes crop-related data and sends owner event 12. Calling the executor directly after construction returns zero **without executing any worklist entry**. Both recipe slots have a negative control reproducing that misleading no-op. The report calls this field `executor_index`, not a successful-entry count; even a failed entry can advance it.

The full constructor can also append `0x60750638` after the worklist-builder result. This extra native entry is retained. The old full-builder comparisons remain valid for their narrower entry point, not a complete constructor's final list.

### Declared frame inputs and owner contract

These are synthetic host fixtures, not captured camera state. Parameters select ROM dimension entry 1, types `0x0200`, `0x0100` or `0x0040`, and selectors 0/2. Two crop-ratio records contain 640:480 values. The source is a zero-filled, declared two-byte-per-pixel allocation: 4608×3456 for the first two types and 640×480 for the third. Format/layout validity for real sensor data is not established. Destinations start with `0xcd` so unchanged output cannot be mistaken for rendering.

Three descriptor locations are supplied explicitly: `job+36`, `job+100`, and the long worker's output at **`job+4264`**. The latter comes from `0x607638cf`, which passes `job+36+4228` to request construction. Omitting it lets a null output descriptor reach the consumer and fault at `0x6073f22f`; it is not evidence of a firmware defect. The owner fixture validates declared descriptor dimensions, full payload ranges and output writability.

Native intermediate-buffer allocation uses 48 records of 88 bytes at `job+5668`. Observed fields are image base `+0`, allocation base `+64`, requested bytes `+72`, identifier `+76`, task byte `+80`, variant byte `+81` and borrowed-state byte `+84`. The event-19 fixture writes only the allocation base; the native caller transfers it to the image base. Allocation size, record alignment, region overlap and capacity are checked before mutation. In the tested ordinary short paths, allocation requests are **31850496 bytes**, with ID `0x1000` for type `0x0200`, or ID 3 for type `0x0100`. These are requested sizes in the synthetic run, not measured camera memory usage.

| Owner event | Declared host response and native evidence |
| --- | --- |
| 12 | Acknowledge crop notification only at `job+10398`; no image processing is simulated. |
| 13 | Return 1 to continue, 0 to cancel. `0x6074f035` converts a zero response to cancellation; the executor returns `0x9e01`. |
| 14 | Supply only declared descriptors 1, 2 and `0xff12`. Unknown descriptor IDs stop, including the current `0xff07` boundary. |
| 19 | Provide one of at most two disjoint, bounded, poisoned allocations, each with a 16-byte guard. |
| 21 | Acknowledge or reject a kind-0 development request at `job+10440`, with the expected cache pointer. Rejection exercises native cancellation and clearing of the pending record. |

Other owner events are not automatic successes. In particular event 31 remains governed by the existing service contract; the connected run does not yet reach it after completing a processed frame.

The probe also declares a single-thread event-bit allocator, one consumer ID `0x8000`, and one 9596-byte workspace. Their native fronts were inspected at `0x6074aea9`, `0x607490c8` and `0x607a038d`. These host models are **not RTOS execution**: they enforce capacity and record allocation separately, never signal completion or synthesize ISP results. The workspace starts at declared zero state; equivalence to a real reused workspace is unverified. Model volatile-register/flag preservation is a host assumption, as with the earlier fill model. Every modeled call is labeled in the report. No model shadows loaded native code.

### Cache invalidation matters for film switching

The connected requests copy the cache pointer to `request+1484`. Eight grid cases then execute the actual consumer constructor `0x6073effd` and its cache comparison. An additional isolated audit executes native **initialize → cold compare → update → warm compare**, with a 24-byte parameter-object fixture attached at `request+1524`.

| Experiment | Native comparison mask |
| --- | --- |
| Freshly initialized cache | `0xffffffbe` |
| Same request after native cache update | `0x80800000` |
| Change only parameter-object table pointer at `+16` | `0x80800000` |
| Change parameter-object comparison field at `+20` | `0x90800000` |
| Change effective mode key | `0x80800002` |
| Change only request byte `+1813` | `0x80800000` |

The nonzero warm mask is recorded as observed; it is not called a fully clean cache. The comparator caches parameter-object fields **+4, +12, +20** at cache offsets 5724, 5728, 5732, controlling bits `0x04000000`, `0x08000000`, `0x10000000`. The COLOR selector's table pointer is at object **+16**, which this comparator does not compare directly. The field at +20 functions as a comparison token here; its native producer and overall meaning are still untraced.

Consequently the earlier isolated COLOR fixture's 20 bytes are insufficient for this consumer: it also reads offset +20 and requires at least 24 bytes. That earlier fixture remains valid only for the selector it tested. A future Gold/Portra handoff must preserve the native invalidation and lifetime contract; changing the table pointer while retaining the same effective key cannot be assumed to request a rebuild. This experiment does **not** prove that changing byte +1813 is ignored by every downstream path, nor authorize an invented on-camera token update.

### Results and remaining boundaries

The routing intervention remains limited to the two accepted keys: keep the original key through construction and frame start, redirect only the Watercolor-specific branch when reached, then set both mode-key locations to 11 before execution. No calibrated film table is attached in this connected grid. Gold/Portra recipe identity remains host metadata; distinct rendered looks are not tested here.

All **12 constructor and frame-start cases** complete with balanced stacks and intact allocation guards. Every executor calls the initialization entry and enters its next processing entry; the index is then 1. None produces output pixels.

| Types / selectors, both recipe slots | Current stopping point | Scope reached |
| --- | --- | --- |
| `0x0200`, selectors 0 and 2: four cases | Absent callee `0x6079bf86` | Request creation, pending record, native consumer/cache comparison, processing configuration |
| `0x0100`, selectors 0 and 2: four cases | Absent callee `0x6079a304` | Same scope through a different input-format path |
| `0x0040`, selectors 0 and 2: four cases | Owner descriptor request `0xff07` is undeclared | Request construction requires an additional caller-owned buffer |

These are still **software coverage / caller-data boundaries**, not a demonstrated ISP hardware failure. Fixed and allocated pixel destinations retain all `0xcd` bytes. Neither request completion, subsequent worklist entries, final output handoff, resource release after processing, nor native COLOR execution in the connected grid has passed. The separate COLOR table tests are not merged into that claim.

Eight negative controls, four per recipe slot, check missing frame start, owner cancellation, request rejection, and a missing long-path output descriptor. Native request rejection clears the pending record, propagates `0x9e01`, and does not enter the processing consumer. The extra controls deliberately keep `full_pixel_cycle_passed=false` even for the no-op's zero return.

The interpreter adds unsigned division, unsigned register multiplication (`udf01` / GNU `mulqu`) and NOT, checked against the same pinned GNU semantics. Unsigned zero-divisor and oversized-quotient cases explicitly stop outside the supported subset rather than emulate those CPU edge cases. Ten added synthetic unit tests cover arithmetic, owner ABI/result polarity, allocation bounds/overlap, missing descriptors, finite pools and completion-token exhaustion. The complete local test discovery passed **63 tests** (including 14 independent Wi-Fi tests present in the shared workspace); this change's relevant prior-plus-new tests total **49**.

Revalidated after the engine changes: all 120 full-builder pairs, both 5200-byte COLOR comparisons, 12 pre-cancellation paths, all 11 service checks, and the historical branch-entry/flag regressions. No firmware was changed or sent to the camera.

```powershell
.\.venv\Scripts\python.exe scripts/epl9_job_probe.py --out local/new-connected-job-run
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p 'test_*.py' -v
```

Use a new ignored output directory and keep assertions enabled. Retained run: `local/job-probe-20261102-final/results.json`. The report records 53 decode anchors, loaded windows, source hashes, exact stock/main identities, native/model events, stop registers, request pointers, guards and negative controls. Follow-up should resolve the two configuration callees and the `0xff07` owner buffer from actual caller contracts, then trace submission/completion and pixel consumption. Do not replace those boundaries with successful no-ops.

## Native parameter object, COLOR and hardware boundary, 2026-11-02

The connected runner now executes the previously absent configuration functions and reaches `0x6073eafa`, which attempts to write `0x800` to **`0x9880014c`**. This address is deliberately unmapped. It is in the hardware-start chain `0x6072fd27 → 0x6073f74f → 0x6073eaea`, followed by accesses to other peripheral addresses. This is a concrete hardware-emulation boundary in the offline run, not a camera failure. Treating these registers as ordinary writable RAM would not implement image processing or completion.

### Build the companion object with native code

A COLOR-only object is insufficient for the connected pipeline. Besides its table and comparison token, downstream stages consume gamma, tone, chroma, a variant byte and inline configuration data. The native builder **`0x6078ab39`** supplies these together. Slot selection at `0x6074b433` uses a **4184-byte stride** for three owner-managed slots; this is stronger layout evidence than enlarging a synthetic object until faults disappear.

The harness pauses the real job at request-consumer entry `0x6072fd27`. On a private copy of its 1876-byte request, with the existing parameter pointer cleared, it runs `0x6078ab39` through its native return on a separate stack. The routine intentionally changes that private request's effective key to 2 while selecting some companion data. The live job/request remains at key 11. This is an explicit host integration experiment, not execution of the complete native owner lifecycle or a validated key-2/key-11 equivalence.

| Header field | Native builder / connected observation |
| --- | --- |
| +0, +4 | Gamma pointer `0x608c37e4`, comparison field 0 |
| +8, +12 | Tone pointer `0x608cf3ee`, comparison field 0 |
| +16 | Native HSL selection, subsequently replaced by the diagnostic table pointer |
| +20 | **Not initialized by this builder**; the harness explicitly supplies comparison token 1 or 2. Its native producer remains open. |
| +24/+26 | Chroma halfwords from native selector `0x6079dd34` |
| +28 | Native gamma-variant byte, zero in these requests |
| +29…+128 | 100 bytes of companion configuration copied from the native selector's result, `0x608bf944` in the tested state |

Both companion curve pointers reference valid ROM spans in all eight attachment cases. The builder initializes only the header in these cases: bytes +129 through the end of the 4184-byte slot and its 16-byte guard retain poison. The connected consumer is therefore given **only the 129-byte header as readable, read-only memory**, plus the separate read-only 3028-byte diagnostic table. Any access past that established header stops. Other builder paths can use in-slot curve storage; this fixture does not claim to cover them.

The old 20-byte isolated COLOR fixture and 24-byte cache-comparator fixture remain valid for their narrower consumers. Neither represents a complete parameter object. Native owner acquisition/release, switching between live objects and the lifetime of in-slot curves are still not integrated. The host retains the header/table through the stopped request.

### Connected table verification

Both replacement identities, input types `0x0200`/`0x0100` and selectors 0/2 form **eight attachment cases**. Each copies a stock HSL table and puts a diagnostic signed marker of +50 or −50 into its first saturation field. These are distinguishable test tables, **not Gold 200 or Portra 400 recipes**.

The native request copies the object pointer, native cache comparison sets rebuild bit `0x10000000`, and the actual common pipeline calls COLOR at `0x6079fc15 → 0x6079ebcc → 0x6079e50e`. Its five-byte CALL returns to `0x6079fc1a`; stack return and decoded instruction length are checked. All **5200 configuration bytes** match the independent packing oracle, including preservation of data produced by earlier stages and relocation of ten table pointers. Different input types legitimately retain different unrelated configuration bytes. Within each type, the two markers produce distinct configuration hashes.

After COLOR returns, the native configuration chain continues to the peripheral boundary in all eight cases. Pixel destinations remain entirely poisoned with `0xcd`; no rendered-image comparison is claimed.

### Additional input and callback requirements

The type-`0x0100` path exposed missing reference dimensions in the old fixture. Request construction at `0x6074f354…0x6074f36a` copies `job+3746` to `request+1576`; the next record comes from `job+3754` to `request+1584`. A later routine reads the first pair and divides by the second halfword at `0x60795691`. Zero-filled fields cause division by zero. The fixture now explicitly supplies four-halfword records `(640,480,640,480)` at both locations. These are declared test values, not measured sensor geometry. Two negative controls retain the zeros and reproduce the exact stop.

Native matrix setup at `0x6079c026` offers nine halfword coefficients to **owner event 2** before packing them. The host accepts only this identified caller with a valid nonoverlapping stack span and leaves all nine values unchanged. This models an owner without additional coefficient correction. The native caller does not inspect that callback's return value. Unknown callbacks, including event 31, still stop unless separately modeled under their established contract.

Two additional host models permit one uncontended acquisition each: resource mask 16 at `0x607a17b7`, and hardware guard mask 8 at `0x607a1841`. Wrong key/ABI or repeated acquisition stops. Five synchronization-counter bytes at `0x8ff001b0` start at declared zero. These models assume one thread and volatile-register preservation; they neither execute RTOS/interrupt code nor release locks, signal events or complete requests. Peripheral memory remains absent.

### Current results and reproduction

| Cases | Result |
| --- | --- |
| Baseline two slots × three types × two selectors | All 12 constructors/frame starts return; eight reach the peripheral write; four type-`0x0040` cases stop at undeclared owner descriptor `0xff07` |
| Two slots × types `0x0200`/`0x0100` × selectors 0/2, attached tables | Eight native object builds, eight complete COLOR configuration comparisons, eight identical peripheral boundaries |
| Five negative controls per slot | Missing frame start, owner cancellation, request rejection, absent long output, and absent reference dimensions reproduce their expected failures |
| Native cache initialize/compare/update audit | Previous pointer/token findings remain unchanged |

Native service routines map descriptor `0xff07` to the first slot at `job+4960`; the associated caller-owned payload and activation notifications still need a complete contract. Its four cases are not included in the attachment success count. Request completion, subsequent worklist entries, final output handoff, balanced releases after processing and ISP pixel behavior remain open.

Retained result: `local/job-probe-20261102-hardware-v1/results.json`, **63 decode anchors**, exact input/source hashes, native and modeled calls, and unchanged destination guards. Twelve job-fixture unit tests pass, including new owner-coefficient, lock and packing-oracle rejection checks. Full workspace discovery passed 77 tests, of which 53 cover this ART/tooling lineage; independent Wi-Fi/video/color-audit tests are separate work. The original prototype again passes 30 route pairs, 180 saturation cases, two full tables and 1050 flag-route cases with zero new ordinary-schedule changes. The integrated regression again passes 120 full-builder pairs, both COLOR results, 12 pre-cancellation paths and 11 service checks.

Reproduce with the connected-job command above and a new ignored output directory. No source firmware bytes or camera state were changed. `full_pixel_cycle_passed` remains **false**. Further work must establish the remaining caller contracts and actual ISP/DMA/interrupt/completion behavior; extending the CPU instruction subset alone does not produce a pixel cycle.

## Owner output slots and failure completion, 2026-11-02

The owner has directed further work toward the software chain; update/install risk assessment belongs to the separate risk discussion. This follow-up makes no new firmware-installation or recovery claim.

The type-`0x0040` stop was not solved by acknowledging descriptor `0xff07`: without caller outputs, its requested dimensions are zero. Native `0x60762916…0x6076296b` examines five optional output descriptors beginning at **job+3984**, with 56-byte stride. Their IDs are `0xff00…0xff04` in the exact ROM table at `0x608f20bc`. The new opt-in fixture supplies the first descriptor with a bounded 640×480, two-byte-per-pixel output and format `0x0302`. This is synthetic caller data, not a measured capture format or proof that type `0x0040` is a camera preview mode.

Native code then distinguishes two cases, both now exercised for both recipe identities:

| Selector | Native output-slot behavior | Host-owned allocation requests |
| --- | --- | --- |
| 0 | Copies the provided output into slot `job+4960`, ID `0xff07`, then notifies owner event 23 | Borrows the existing destination; additional slot `job+5200`, ID `0xff0b`, requires 2560 bytes |
| 2 | Calls `0x6074fbed` to build slot `0xff07` with aligned dimensions | Allocates 614400 bytes for `0xff07`, then 2560 bytes for `0xff0b` |

The second slot is built through `0x6074fc57`, with dimensions reduced by the native caller and stride aligned to 32. Payload meaning remains unverified. The owner model accepts only these declared formats/IDs, checks the full writable range, rejects zero dimensions, overlap, changed payloads and activation before allocation, and allocates disjoint poisoned regions with guards. Borrowed output is not added to its owned allocations. Event 23 activation is tracked independently; repeated activation is outside this finite fixture. Other owner events are not blanket successes.

All four runs proceed into the request consumer. The current synthetic input format then returns **`0x9e40`**, recorded directly before native processor return at `0x6072fdd3`. This is a configuration rejection, not a completed image. The native cleanup at `0x6073f566` executes the cache update and calls the workspace release front. A bounded model for `0x607a06d2` requires the previously allocated live workspace and changes its +9592 state from 1 to 2, matching the inspected front's state transition. It does not free the consumer ID or complete pixels; native pool-lock scanning is not emulated.

The native submission error path invokes `0x6074af81`. Its external event front `0x6074af2c` has a finite host model which accepts only one allocated, previously unsignalled bit for task 0. It records the signal and returns zero; this models a notification of an already failed request, **not successful processing**. The native caller retains its failure status and enters pending-request cleanup `0x6074edd9 → 0x6074b125 → 0x6074b068 → 0x6074af9e`.

The new exact boundary is **`0x6074b02f → 0x60418b31`**, the OS event-wait call. No success result is supplied there. Pending owner/request/consumer-ID/token fields remain intact. Event clearing, token release, consumer-ID release, owner event 22 and final record clearing lie after this wait and have **not** executed. Owned output slots also remain allocated. The current evidence must not be described as complete request cleanup.

Retained report: `local/job-probe-20261102-slots-final/results.json`. It contains the old 12 baseline cases (retained without extra outputs), eight attached COLOR cases, ten negative controls, and four new `owner_slot_cases`. All expected boundaries, processor error codes, workspace states, activation IDs, allocation sizes and unchanged pixel guards passed. Sixteen job-fixture unit tests pass, including four new tests for allocation/activation, borrowed buffers, release preconditions and event signalling. Full workspace discovery passed 90 tests after placing test temporary files in ignored `local/test-temp`; the initial discovery hit a sandbox temporary-directory permission error in an unrelated OSD test. No shared engine semantics were changed.

Next software work is the event-wait/clear/release contract and a valid input-format fixture for the type-`0x0040` path. Preserve the native error result and do not clear pending ownership before the corresponding wait outcome is known. Neither the failure-path progress nor the eight unchanged COLOR cases establishes normal frame completion.

## Failed-request teardown and independent short input format, 2026-11-02

This follow-up supersedes the preceding event-wait boundary. Exact E-PL9 1.1/build 1101 inputs and hashes are unchanged. Reproduction: `python scripts/epl9_job_probe.py --out local/<new-directory>`. Retained report: `local/job-probe-completion-20261102/results.json`.

The native wait/cleanup wrappers now execute through the final return in all four short-route configuration-rejection cases. The OS and finite pool fronts are explicit host models, not an emulated RTOS:

- `0x60418b31` waits for event ID `0xe3`, OR mode 1, timeout argument 1000. The inspected native immediate-success branch writes the full event word. The fixture declares a non-autoclearing event and only accepts an already-signalled allocated bit; an unsignalled wait stops rather than inventing scheduler progress or elapsed time.
- Native `0x6074b125` invokes `0x6074b0f5 → 0x6074b0ce`, supplying the complemented token to `0x60410a51`. That OS front ANDs the current bits with the supplied mask (`0x60410afd…0x60410b02`). The bounded model clears only a live signalled token.
- The `0x6074aef3` front returns the cleared token to the fixture pool. Double release and release before event clearing fail. The real critical section and global pool bitmap are not emulated.
- Native `0x6072fac5` calls consumer teardown `0x60740038`, workspace unlink `0x607a08aa`, then ID free `0x60749116`. These finite models accept only ID `0x8000`, the declared live workspace, and the measured processor result `0x9e40`. They do not claim hardware teardown after successful processing. Workspace task/ID/state fields +9584/+9588/+9592 become zero, matching native `0x607a091f…0x607a0925`; the ID becomes available only afterward.
- Native pending cleanup delivers owner event 22, releases its stored descriptor reference through event 16 (`0x6074ae70`), then clears the full 56-byte record through the fill front. The fixture tracks reference returns separately from slot activation. A supplied `0xff00` reference exists before dispatch: selector 2 returns it without a preceding event-14 fetch. This initial ownership is a declared caller assumption, not proof of the camera owner's complete refcount scheme.

All four cases return **`0x9e40`**, preserve the caller stack, have no allocated/signalled event bits or live consumer ID, and leave all 56 bytes of the pending record zero. **This completes this failed-request path under the declared host contracts only.** Output slots `0xff07`/`0xff0b` remain active and retained by the job/owner; final job destruction and full buffer lifecycle are not established. No payload bytes change. Neither owner event 22 nor the return is evidence of successful image processing.

### Short path: route selector is not a pixel format

The fixture previously used routing kind `0x0040` as the input descriptor format too. These are now independently selectable. Native `0x60799f63…0x60799f71` reads **request+28**, shifts the format by eight bits, and for request kinds 0/16 selects family 1 (`0x607a01b1`) or family 2 (`0x607a02dc`). A format of `0x0040` has family zero and takes the rejection branch. This is a concrete fixture error, not evidence that the short schedule itself cannot work.

| Short routing kind | Independent input format | Both identities × both selectors |
| --- | --- | --- |
| `0x0040` | `0x0040` | Native configuration rejection followed by complete failed-request teardown |
| `0x0040` | `0x0100` | Passes input-family dispatch; stops at unmodeled helper `0x6073920e → 0x604bbfac` |
| `0x0040` | `0x0200` | Passes configuration and reaches the same peripheral write at `0x6073eafa → 0x9880014c` as the long paths |

The short family-2 route requests resource mask 32 rather than the long fixture's 16. Its host lock accepts only that one exact uncontended acquisition; no scheduler/MMIO completion is added. Source remains a synthetic 640×480 two-byte allocation, destination format `0x0302`. **Actual pixel packing, channel order, bit depth, planes and camera-buffer provenance remain unverified**; successful configuration cannot establish them. These new short cases use stock configuration, not the attached diagnostic table oracle.

Validation: the full job probe passes the previous 12 baseline cases, eight attached COLOR comparisons, ten negative controls, four revised failure-cleanup cases, eight independent-input comparisons and cache audit. All 93 workspace unit tests pass, including three new tests for absent signals/invalid output pointers, event-clear/release ordering/double release, and consumer teardown preconditions. `full_pixel_cycle_passed` remains false. Next work is the remaining format-specific helper and actual buffer layout/ISP contract, followed by successful completion and job-owned buffer release; those cannot be inferred from error cleanup.

## Input stride and job-buffer ownership, 2026-11-02

Same exact E-PL9 stock input and hashes as above. The new retained report is `local/job-probe-packing-release-20261102/results.json`; reproduce with the job probe and a fresh ignored output directory.

### Format 0x0200: measured memory configuration

Eight native runs cover both recipe identities, selectors 0/2 and descriptor strides 640/704, with active dimensions 640×480. They stop at the existing peripheral boundary without processing source pixels. The configuration measured at the 9596-byte workspace is:

| Workspace offset | Stride 640 | Stride 704 | Evidence scope |
| --- | --- | --- | --- |
| +112 | 1280 | 1408 | Native programmed row step, two bytes per descriptor stride unit |
| +120 | `0x76543210` | same | Native reorder/configuration word; semantic channel labels unknown |
| +128 / +132 / +136 | `0x01000d00` / 4 / `0x00040001` | same | Exact selected memory-interface configuration |
| +9260 | source base | source base | Zero-origin base-address selection |
| +9264 | 614400 | 675840 | Native size/plane-offset field equals `stride × height × 2`; not independently a validated DMA allocation bound |

`0x6073b330` classifies the descriptor; `0x6073b033` derives the row step and source addressing. In the measured branch the stride calculation at `0x6073b1d6…0x6073b1e3` gives two bytes per unit. The descriptor stride at +10 is distinct from active width +12; padding changes the row step while active width remains 640. The fixture now accepts an independent bounded, 64-unit-aligned input stride and sizes its source accordingly. This alignment is a conservative fixture constraint, not a proven minimum hardware alignment. The configuration words are captured as regression evidence.

This narrows the memory contract but **does not identify RGB565, YUYV/UYVY, Bayer order, effective sample precision, or byte/channel order**. In particular, neither a two-byte step nor `0x76543210` assigns channel names. The payload has not been read by modeled hardware. Cropped/nonzero-origin addressing, other format variants and actual camera-produced samples still need qualification. Do not use the input-format code as a JPEG/RAW file-format label.

### Two cleanup levels, plus owner-managed output slots

Native destructor `0x6074e2fd` calls mode cleanup `0x6074ed61`, buffer sweep `0x6074accb`, cache destructor `0x6073e57a`, then pool free `0x604023b2` for the job. Four post-error experiments now execute this chain and return with balanced stack and no live JOB/CACHE slots. A finite pool-free model rejects unknown/double releases and any nonzero pending record; it retains bytes solely for inspection. This covers the already-returned `0x9e40` path, not destruction while ISP work remains active.

The native sweep visits 48 88-byte records plus two auxiliary records. A new isolated native audit places one owned and one borrowed allocation in the main table:

- A nonzero pointer at record+64 with byte+84 zero and no internal-pool flag routes through `0x6074ad9f` to **owner event 20**, then clears the first 84 bytes and ID. The host accepts only the exact live allocation's pointer, size and ID.
- A nonzero borrowed record with byte+84 set takes `0x6074abee`, clears all 88 record bytes and never sends event 20. Its caller payload remains unchanged.
- A repeat sweep sends no additional release. Internal-pool flag `0x20000` and nonempty auxiliary pools are separate branches and are not covered by this two-record audit.

Output slots `0xff07`/`0xff0b` are **not** these sweep records. Both remain active after the tested destructor, so no claim of complete owner-buffer reclamation is made. Native `0x6074fbd3` emits **event 24**. One caller is the pending callback's event-10 branch (`0x6075056b`): with owner flag job+10396 set, it reads slot IDs at pending-record+36/+38 and notifies the owner through calls at `0x607505a9`/`0x607505c9`; it later signals completion. Other callers include `0x60763dbb/0x60763dca` and `0x60765cc4/0x60765cd3`. This establishes a separate lifecycle notification, not that event 24 necessarily frees physical storage for every real owner. It is not fabricated on the current error path to make counters reach zero.

Validation: previous job regressions pass, plus eight stride cases, four destructor cases and the owned/borrowed/repeat sweep audit. Full workspace discovery passes 116 tests (including independently added tests from other work); two new job unit tests reject pending/double pool release and borrowed/mismatched/double owner-buffer release. One initial audit run failed due to a Python assertion accessing a tuple as a Region; the assertion was corrected and the full probe rerun successfully. Next work is to trace the real owner's event-24 handling and the format's producer/hardware unpacking. Full pixel output and normal completion remain unverified.

## Native completion and Bayer follow-up, 2026-11-04

The [completion-contract audit](epl9-completion-contracts.md) adds native owner callbacks, notification ordering, format-family identification and wide arithmetic. It supersedes the unresolved short-Bayer helper boundary above: all four short Bayer cases now reach the same first peripheral write as the other processing cases. The change executes native arithmetic and configuration; it does not synthesize pixels or hardware readiness.

The exact diagnostic code labels **`0x0200` as 4AspectsData**, **`0x0100` as Bayer/8-bit**, and **`0x0302` as YCC422**. The two-byte stride measurement for `0x0200` remains valid, but its pixel interpretation is still unverified. For two native owners, events 23/24 return the owner's status without freeing physical storage. Separate component runs execute notification → signal → wait → cleanup with supplied status 0/`0x9e40`; these are software-injected notifications, not successful image jobs.

The full job regressions, 330 native arithmetic comparisons, historical route/COLOR checks and 121 workspace unit tests pass. No complete pixel pipeline or deployable film patch is established. See the linked audit for exact input hashes, addresses, host assumptions, reproduction and the remaining peripheral/data-flow boundary.

## Hardware status and destination offsets, 2026-11-04

The [hardware-completion follow-up](epl9-hardware-completion.md) fixes a fixture error affecting the earlier output-address evidence: destination +16/+18 are H/V offsets, while source +16/+18 are area dimensions. Native diagnostic names confirm the distinction. Supplying width/height as destination offsets placed the short-path base exactly beyond its allocation. Zero-origin destination fields now produce the expected base; two negative controls preserve and reproduce the old error. Earlier peripheral-boundary results do not prove valid output addressing or pixels.

The native hardware-status handler `0x607491e9` now runs through native request notification, signal and pending cleanup for 24 explicitly synthetic register scenarios, with masked/empty/busy states retaining the request. Actual registers, DMA/ISP transformation and output pixels remain unexecuted. The report distinguishes native code, finite read/write replay and physical-camera evidence; no complete image or deployable replacement is claimed.
