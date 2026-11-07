# E-PL9 ART replacement: service dependencies

Current follow-up, 2026-11-04: the [integrated prototype](epl9-integrated-prototype.md) preserves complete worklist records and the historical 11 component checks. Newer [completion](epl9-completion-contracts.md), [hardware/descriptor](epl9-hardware-completion.md) and [real-RAW](epl9-real-raw-boundary.md) audits reach the peripheral boundary and exercise separate status/cleanup contracts. Those checks are not actual ISP completion. See [project status](project-status.md) before using the older next steps below.

The [connected-job experiment](epl9-integrated-prototype.md#connected-constructor-frame-start-and-consumer-2026-11-02) adds native construction, frame start, declared descriptors, request creation and cache comparison. It confirms two additional requirements: call frame start before the executor (the constructor leaves its cursor at 16), and preserve the parameter object's cache invalidation fields. The cache at `job+12316` compares object fields +4/+12/+20, whereas COLOR reads its table pointer at +16. Merely replacing that pointer does not set the comparator's `0x10000000` rebuild bit in the tested state. The +20 field's native producer remains untraced; this is not a validated patch recipe. Full processing, normal completion and final release remain unverified.

The later [hardware-boundary follow-up](epl9-integrated-prototype.md#native-parameter-object-color-and-hardware-boundary-2026-11-02) runs native parameter builder `0x6078ab39` on a private request copy and connects eight diagnostic-table cases through COLOR to the first unmapped peripheral write. Its 129-byte initialized header includes companion gamma/tone/chroma and inline data; a table-pointer-only object is insufficient. That builder leaves +20 untouched. Owner event 2 offers nine coefficients for optional correction, and request+1576 requires nonzero reference dimensions on the tested type-`0x0100` path. Preserve these contracts alongside completion/refcounts; passing configuration and stopping at hardware does not prove a finished frame.

## Decision, 2026-11-02

Preserve the stock service contracts of the chosen processing path: request submission, pending-request completion, owner callbacks and their result handling, buffer descriptors/ownership, output handoff, and balanced parameter-object references. None of these has been established as dispensable Watercolor styling.

**Do not unconditionally substitute key 11 before routing.** In the four previously identified already-ordinary cases, retain the original short schedule. The next prototype should distinguish routing identity from effective processing identity: bypass the Watercolor-specific passes where present, retain a compatible ordinary schedule, then make downstream processing selectors consistently use the neutral/recipe mode. This is a design constraint, not an implemented hook; changing only a single cached key or request field is still insufficient.

This follow-up establishes several service mechanisms more precisely. It does not establish an integrated replacement, all preview/capture caller contexts, or timing on the camera.

## Exact input

Olympus E-PL9, owner-reported displayed version **1.1**; downloaded main build **1101**. Container `OLY_E_133_1101_0000_0000.BIN`: **104552480** bytes, SHA-256 `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`. Decoded main: **26214336** bytes, SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`, analysis base `0x60400020`. These are downloaded stock bytes, not a dump of the owner's installed body.

## What must remain and why

| Mechanism | Exact-image evidence | Replacement constraint |
| --- | --- | --- |
| Ordinary development request and valid output descriptors | Both short `0x60751319` and long-path worker `0x607638cf` call `0x60761b6a`. The short path builds local descriptors, computes aligned dimensions and obtains buffer ID `0x1000` using `0x6074a8e4` or `0x6074a9bd`. It can also use `0x1060` under flags. | Keep a complete native submission path with matching format, dimensions, allocation and callbacks. One worklist entry is not one CPU operation. |
| Completion and cleanup of the previous request | `0x6074ee9c` reads the previous worklist entry's `+8` handle, calls `0x6074edd9` when nonzero, then clears it. That helper calls `0x6074b125` with argument 1000, reads completion status, calls `0x6074aef3`, conditionally invokes `0x6072fac5`, emits owner event 22, releases associated records through `0x6074ae70`, and clears the record. `0x6074af9e` reaches event-wait-shaped routine `0x60418b31`. | Keep completion ordering and cleanup before reusing intermediate storage. Argument 1000 is not assigned a time unit here. Preserve original error propagation; callers do not all check every returned value. |
| Owner event 31 | `0x60763978` first invokes the completion helper, then calls dispatcher `0x6073eab3` with event 31, an argument pair pointing to `job+4`/`job+36`, and the callback/context stored at `job+4`/`job+8`. A zero callback result sets `job+10394=1` and returns `0x9e01`. | Preserve this owner notification and its continuation/failure contract. It is not an identified image filter or a generic hardware command. |
| Intermediate buffer and transfer request | `0x607518d3` obtains a buffer record with ID `0x1000`, using descriptor `job+4264` and a size candidate `dimension12 * dimension14 * 2`. `0x6074bae2` puts two addresses and a count into a kind-14 request and submits it through `0x6074ef3a`. | Keep this transfer when using that stock long path, or establish an equivalent destination/data-flow contract. The hardware transfer implementation and cache/DMA coherence are not yet traced. Do not append it indiscriminately to already-short paths. |
| Output handoff and optional geometry work | `0x60751930 → 0x60750c2e → 0x60750c73` carries the pending handle forward. The latter checks dimensions, can allocate buffer ID 3, build another kind-3 request, invoke an optional callback, update dimension/offset fields, and finally call `0x6076199b`. | Preserve output descriptors, optional callbacks and pending-result handoff. This is more than copying a pointer; it cannot be dropped merely because the Watercolor effect is removed. Complete pixel/geometry semantics are not yet modeled. |
| Balanced references to parameter objects | `0x607638cf` optionally calls `0x6074b41f`, temporarily installs its result at `job+12320`, submits development, calls `0x6074b429`, then clears the pointer. Their leaves `0x6074b4da`/`0x6074b4eb` increment/decrement a 16-bit count at owner `+15428`; acquire returns the pointer at owner `+15408`. Another inspected routine waits for this count to become zero before cleanup. | Preserve balanced acquisition/release and valid backing storage. The count protects an owner-managed object; this does not prove a new recipe object can be freed immediately after submission, especially because the color builder retains LUT pointers. |

The Watercolor-specific selection of stages `0x0600/0x0601/0x0602` and buffers `0x1040/0x1041` is the part to replace through a coherent alternative route. Removing those entries while leaving callbacks or handles referring to their buffers would not preserve these contracts.

## Event 31 is caller-dependent

The previously unknown operation is an indirect owner callback, not a uniquely named built-in algorithm:

- `0x6073eab3` returns 1 when the callback pointer is absent; otherwise it forwards the 8-bit event code, argument pointer and owner context.
- Parameter builder `0x607ce515` installs callback `0x607cfe8d`. Its jump table at `0x6090b550` sends event 31, row `0x6090b5c4`, to `0x607cffc0`, which returns the owner's byte at `context+195`. The callback performs diagnostic logging before dispatch; this is not a claim that the entire call has no effects.
- Wrapper `0x607d16c7` delegates to that handler and adds special behavior only for event 16, not event 31.
- Separately inspected callback `0x609a836f` handles events 2, 12, 19, 20 and 34; event 31 reaches its default success return. Its creator is in code referencing `iseq_swpa_if_imgpro.c`.
- Other entry points copy caller-supplied callback pointers. Consequently the observed default behavior cannot justify deleting event 31 globally. The existing type/selector grid has not yet been tied to every real owner/capture context.

## Offline validation

`scripts/epl9_service_audit.py` freshly decodes 13 windows, checks **20 instruction anchors** and the event-31 table row, and uses the existing bounded interpreter for **11 cases**:

- Four balanced acquire/release pairs (initial counts 0, 1, 7, 65534), checking the returned pointer and all object bytes.
- Three previous-entry cases: no previous entry, empty pending handle, and a pending handle reaching the completion-call boundary without being cleared early.
- Two event-31 dispatch tails with owner status 0/1, beginning **after** the logging call and returning the corresponding status.
- Two callback-dispatch cases: absent callback and present callback with exact forwarded registers, stopping before the indirect call.

All passed in `local/service-audit-20261102/audit.json`. The interpreter still stops before CALL/RET execution and does not execute OS waits, real transfers, asynchronous completion or full jobs. Synthetic object regions do not establish real allocation/lifetime correctness. Source images were not modified.

```powershell
.\.venv\Scripts\python.exe scripts/epl9_service_audit.py --out local/new-service-audit
```

## Next integration work

Qualify the caller/type/selector contexts and test a routing-aware replacement that retains the four short schedules. Then validate effective-mode propagation and per-job table lifetime through complete request construction and completion. Neither extracting icons nor passing the bounded service tests removes these requirements.
