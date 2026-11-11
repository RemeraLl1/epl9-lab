# E-PL9 native job ownership and exclusion

The [ISEQ follow-up](epl9-iseq-job-lifetime.md) now narrows the producer/token question: the stock transaction result connector stays empty, while a separate active controller has a traced sequential J lifetime. It does not establish command1 worker reuse or global exclusion.

## Result, 2026-11-11

The audited primary ART owner and its wrapper have **structural sequential
ownership**: receive work, construct a job, prepare it, execute/drain it, destroy
it, then return to receive. They do not deliberately call the same live job a
second time while its executor is suspended. This is a narrower and more useful
result than treating the adversarial [cloned reentry controls](epl9-native-source-reentry.md)
as a measured camera race.

There is still no whole-program exclusion proof. The shared executor has no
acquired per-job busy guard, and other task routes accept jobs in message
payloads. Their producers, pointer aliases, enabled callbacks and interrupt
paths are not all closed. No real overlapping use of the same job has been
observed. **Neither a camera race nor global race-freedom is established.**

No firmware guard was added. Reusing an error field, resource lock or guessed
storage would change native semantics without a qualified ownership/atomicity
contract. All recipe data, frozen/private/native-source modules, decoded mains,
OSD and packages remain unchanged. No camera was accessed or firmware released.

## Saved baseline and exact input

Before any changes, clean commit `80fe367dd76297638b03293cdaaee0c204c74052`
on `fix/native-source-gate-consistency` was saved in a verified git bundle.
The separate full source patch also retained SHA-256
`291655e416cff52beffe2baca86e4e23af26de4247d5cef602d45bb89f5ff064`.
This investigation is on separate branch `research/native-job-exclusion`.

The stock decoded main is E-PL9 build 1101, 26214336 bytes, base `60400020`,
SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
It is downloaded stock firmware, not a readback of the user's installed camera.
The locally qualified GNU reader retains SHA-256
`013c0af69148cc34b74e2a8a46c4efba808c7575a19cd1c08b4f2ab3867712d5`.
Listings, source controls and evidence are local/ignored; the original image is
not redistributed by this change.

## Primary ART: task 31

The descriptor at `60419028` identifies task 31, `REC_IMAGE`, entry `607ce1b5`,
stack 14080 bytes. Its receive uses queue 74, `REC_EXEC_IMAGE`, via halfword
`60420ffa` and `607c93c4`. Names alone are not the ownership proof; the control
flow and pointer aliases are:

1. The task allocates its owner O in its own stack at SP+16 after a 372-byte
   entry allocation. Receive at `607ce1d4` precedes processing.
2. The selected path reaches `607ce31c -> 607ce3f3 -> 607ce460 -> 607cf061`.
   Operation `1003` selects table row `6090b4f4 -> 607ce44c`. The ordinary ART
   property branch uses `607cf061` directly. Special property branches can call
   it twice, but each call constructs and destroys a job; that is not repeated
   entry of one still-live J.
3. Parent `607cf061` zeroes and produces local parameters at `607cf090`, calls
   constructor `6074df04` at `607cf09a`, then publishes the returned J at O+156
   at `607cf0a1`. Preparation `607cf0ad` reloads this same J. The descriptor
   alias from native leaf `6074e341` is D=J+36.
4. Execution at `607cf0e0` calls `607ce5ae`. Its normal branch loads O+156 and
   passes J, count `ffff`, to executor `6074e6eb` at `607ce63f`. Drain
   `6074e97d` follows successful execution; cancellation/error paths retain
   their original result handling.
5. Parent cleanup at `607cf0e9 -> 607cefeb` occurs before the task can return
   through its processing branch and receive again. The cleanup destroys J,
   but does **not** clear O+156. Pointer presence is therefore not a busy flag.

These are native sequential calls, not queued duplicate executions from this
one task activation. Eight native straight-line alias controls execute the
actual stack/publish/reload fragments without call models. They confirm the
aliases and arguments, not complete task execution or kernel scheduling. The
tracked read-only audit reproduces these fragments with a declared native-sized
14552-byte job, without allocating or executing a full job.

The alternate diagnostic branch of `607ce5ae` calls `6074e7ca`, which uses the
same J sequentially for diagnostic trials and calls executor at `6074e923` and
`6074e970`. It starts/drains trial work and restores descriptors before final
execution. Legitimate repeated API calls must not be rejected merely because
this J was used before.

## Wrapper owner: task 0x2015

Descriptor `6041d7fc` identifies task `0x2015`, entry `607d9cb8`, declared stack
8192 bytes (`0x2000`). This later descriptor row does not prove runtime instantiation or uniqueness.
Its queue handle halfword `6042135c` is `0x2016`; receive
`607d9cd5 -> 607c93c4 -> 607d666c -> 604313e9` precedes work.

Its O is a separate task-local object at SP+28 after 360 bytes of entry
allocation, with parameters at SP+312. Constructor `607d9d52` returns J;
`607d9d59` writes it at SP+184, exactly O+156. The path prepares through
`607d9d62 -> 607d0b8d`, executes through `607d9d94 -> 607ce5ae`, and cleans up
at `607d9d9e -> 607cefeb` before looping back to receive at `607d9ccd`.

Thus these two audited task-local owners are not one shared owner merely
because their callbacks eventually delegate to the same primary handler.
Allocation failure/error states and all downstream kernel/IRQ behavior were
not executed as a complete runtime.

## Executor and other routes

Executor `6074e6eb` uses these established fields:

- J+10388: cursor, advanced after work returns at `6074e7b2/6074e7bd`.
- J+10390: work count.
- J+10392: previous callback result/error, tested at `6074e715` and written
  **after** work returns at `6074e769`.
- J+10394: cancellation, not ownership.

The work limit is the caller's D1. A successful partial return can be followed
by another call on the same J. Before `6074e765` dispatch, no busy acquisition
is stored. This explains the earlier adversarial duplicate-work observation;
it does not identify an actual producer that schedules that overlap.

A six-form relative CALL/CALLS/JMP byte scan of the exact main finds these
eight direct executor calls, each independently decoded in its containing
function window:

- `6071bbda`, caller body `6071bb8c`.
- `6074e923` and `6074e970`, diagnostic helper `6074e7ca`.
- `607cd705`, owner helper `607ccf26`.
- `607ce63f`, primary executor wrapper `607ce5ae`.
- `609a64bc`, message helper body `609a649b`.
- `609a8e82`, helper `609a8e3f`.
- `61028f7f`, helper `61028f22`.

No literal 32-bit pointer to `6074e6eb` occurs in this image. This is **not** an
exhaustive reachable call graph: computed pointers, aliases, indirect function
entries and IRQ routes remain possible. In particular, real calls can target
function bodies after a MOVM/stack prologue; scanning only prologue addresses
misses them.

Task 119 `REC_EXT`, entry `607ccd84`, queue 159, reaches
`607cce1f -> 607ccf26 -> 607cd705`. Its inspected path constructs J locally and
drains/destroys it before returning to receive. This is another sequential
owner route, not evidence of a shared primary J.

Tasks 121/122, `ISEQ_IMG_CM` / `ISEQ_IMG_CS`, entries `609a615e/609a6195`, use
queues 164/165 and common command dispatcher body `609a61d2`. Command 1 calls
`609a649b` at `609a623d`. It dereferences J from a message payload, calls the
executor at `609a64bc`, then drains at `609a64c5`. The packet's command and
payload are words +8/+12; the handler dereferences the payload twice to get J.
After the handler/drain returns, the common path publishes status and a token
through `609a6424/609a6454` to fixed queue172, `ISEQ_MAIN_POST`; it is not a
reply to an arbitrary packet-supplied queue. Task72 `ISEQ_MAIN` consumes this
completion through `609a5ad0 -> 609a5b3f -> 609a5d7a -> 609a990e`.
Completion records are staged at `609a6a20`, consumed at `609a6a87`, and token/
status matching appears at `609a6c22`. This establishes local ordering, not the
producer's exclusive ownership or a complete acknowledgement protocol.

Each consumer loop is
sequential, but two different tasks share that route. A proof that producers
cannot submit the same J to both requires the producer/ack/ownership protocol,
not just these task registrations.

## Synchronous callbacks: one apparent route excluded for ART

Primary callback `607cfe8d` dispatches event 16 to `607cff71 -> 607d004d`.
That helper enters `607d0067` only when O+72 is operation `100c`. Its later
indirect callback at `607d00f2` is therefore not an ART-1003 reentry route.
For `1003`, it instead calls `607d00f7 -> 607d4ef2 -> 607d4ece`. The latter's
allowlist is `1001/100b/1012/100c`, so ART returns zero and the primary handler
returns readiness without invoking that callback.

The read-only audit executes the complete primary event-16 callback for
operation `1003`, with declared ready=1, phase=16 and disabled log output. It
returns 1 with unchanged owner storage and zero modeled calls, without executor,
COLOR or `607d00f2` entry. A contrasting `100c` control stops **before**
`607d0067`, proving the branch is retained rather than silently bypassed.
This is not permission to generalize to arbitrary owner states or other events.

Primary event 14 helper `607cffc7` has diagnostics but no executor call; its
inspected body modifies descriptor state under explicit property gates.
Existing native event-2/13/21/31 controls remain scoped evidence. The wrapper's
extra event-16 `607d55d1` and resource callbacks enter source/service dependencies;
their complete enabled states and transitive indirect behavior are not closed
by this investigation.

## Why no speculative guard was installed

Several superficially small changes would be semantically unsafe:

- Reusing J+10392 changes error propagation and can make native work reject its
  own state. Cursor/count/cancellation and pending handles are also live state.
- Treating O+156 as busy uses a stale pointer after destructor.
- The native constructor allocates 14552 bytes, not the host fixture's 16 KiB.
  The cleared tail is also used by native request/pending state. No fixture
  padding or byte beyond the allocation is qualified guard storage.
- A non-atomic check/store admits preemption between them; no unused per-job
  field, owned global allocation or qualified compare-and-set contract was found.
- `607a17b7` is a try-acquire and `607a1841` a blocking/retry acquire on native
  resource bits, not job identity. Existing descendant acquisitions/releases
  make reusing their keys a resource conflict/deadlock risk, not safe exclusion.
- Helpers `60449006/60449010` clear/set PSW bit `800` through
  `60434c67/60434c60`. They do not save and restore arbitrary caller state.
  Wrapping a long, potentially waiting executor with them would change interrupt
  semantics and may prevent its own progress.
- Holding busy through asynchronous pending completion, or clearing it on a
  guessed callback, changes legitimate partial-execution/drain/cancel lifetime.
  A new error return for overlap also needs an agreed native caller protocol.

A future guard needs demonstrated same-J sharing, authoritative per-job owned
storage/lifetime, an atomic acquisition compatible with the native scheduler,
well-defined rejection or deferral, and release on all supported exits. Those
prerequisites are missing. Adding a global lock or an arbitrary busy bit would
hide that uncertainty rather than resolve it. The separate variant is unchanged.

## Reproduction and next qualification

Run the reproducible read-only inventory, owner-alias fragments and event-16 controls:

```sh
python scripts/epl9_job_exclusion_audit.py --out local/new-job-exclusion-audit
python -m unittest discover -s scripts -p test_epl9_job_exclusion_audit.py -v
```

The final read-only run is `local/cloud-native-job-exclusion-20261111/audit-v3/`.
Its source and imported execution-source hashes match the checked tree; an
independent replay reproduces all eight references, eight alias fragments and
the two event-16 outcomes. All 363 source unit tests, compileall and whitespace
checks pass. Optimized (`python -O`) CLI use is rejected before creating output.
Stock/frozen/private/native-source main identities and native-source module
identity remain unchanged. These are source/CPU evidence, never hardware passes.

The report explicitly keeps `same_job_exclusion_proven`, `scheduler_executed`,
`irq_executed`, `firmware_guard_added` and `install_ready` false. It records
stock/reader/source identities. Source-only regression controls reject changed
reference inventories, missing/extra references, jump substitutions and new
literal pointers; they do not simulate concurrency.

Detailed native listings, owner aliases, resource/IRQ analysis and task routes
are retained in `local/cloud-native-job-exclusion-20261111/`. No original BIN,
decoded image, generated candidate or private listing is added to source control.

The next useful work is the ISEQ producer/ack/alias contract for queues164/165,
remaining helper call chains and full enabled callback/interrupt ownership.
For the audited two film owners, retain their construct/execute/drain/destroy
ordering and no-adversarial-reentry precondition. Physical scheduling, source
acquisition, subsequent ISP submissions/completion and camera testing remain
separate qualifications.
