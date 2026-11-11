# E-PL9 ISEQ producer, tokens and job lifetime

## Result, 2026-11-11

The suspected command-1 route through queues 164/165/172 does **not** establish
same-job reuse before completion. The exact stock transaction connector clears
its graph-result list and never fills it before consuming it. Native controls
register two identical payloads with different tokens, but dispatch neither to
an image worker. A supplied completion-kind record makes no progress either.
Metadata admission is not execution, completion or a per-job lock.

A separate, genuinely connected analysis/controller path was identified. It
constructs J in a task-local owner's +12 field, calls start/executor/drain, then
destroys J and clears that field before returning to the controller wait loop.
That is positive sequential-lifetime evidence. Its alias to the command-1
worker's wrapper+0 J is not established; those paths must not be conflated.

No actual overlapping reuse of J, whole-program exclusion or physical scheduler
behavior is proven. No lock, candidate, recipe, firmware package or camera was
changed. This follow-up narrows the [previous ownership question](epl9-native-job-exclusion.md)
rather than turning synthetic repeated entry into a camera race.

## Preserved input and baseline

Before editing, clean commit `e14a42c03dbf3e4417a8474171b2cdf781b5d267` on
`research/native-job-exclusion` was saved in a verified git bundle. Its source
patch and the earlier integration branches remain intact. This work is separate
on `research/iseq-job-lifetime`.

The decoded E-PL9/IM008 main build 1101 has 26214336 bytes, analysis base
`60400020`, SHA-256
`8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
It is downloaded stock firmware, not a readback of the installed camera.
The qualified local GNU reader retains SHA-256
`013c0af69148cc34b74e2a8a46c4efba808c7575a19cd1c08b4f2ab3867712d5`.
Original firmware and private listings stay ignored/local.

## Worker consumers are real; their producer was not identified

Tasks 121/122, `ISEQ_IMG_CM` / `ISEQ_IMG_CS`, consume queues 164/165 through
common handler `609a61d2`. Command 1 calls body `609a649b` at `609a623d`:

- Packet+12 points to payload. The helper reads wrapper=*(payload), then
  J=*(wrapper), not J=payload and not wrapper+12.
- It calls executor `6074e6eb` at `609a64bc`, then drain `6074e97d` at
  `609a64c5`, before returning its result.
- Common completion sender `609a6424` sends the token/status record to fixed
  queue 172, `ISEQ_MAIN_POST`, through `609a6454 -> 609a9985`. Task 72
  `ISEQ_MAIN` receives and stages it. This establishes local ordering after
  execute/drain, not that a producer waits for it before reusing J.

The exact-image six-form relative-reference inventory of `609a9985` finds
three calls, all checked in containing native code:

1. `609a6454`: the fixed queue 172 completion sender above.
2. `609a68e6`: **command 11 to queue 27**, not command 1 to 164/165. Helper
   `609a6835`, selected by common command 9, puts return queue 193 in packet+0,
   a generated tagged token in +4, command 11 in +8 and a stack-copy pointer in +12.
   Its send destination comes from `60420f9c`, value 27. It then waits for a
   12-byte reply on 193. Queue constants 164/165/172/27/193 were read directly
   from this main.
3. `609a6d39`: an upstream response to the original packet's return queue,
   not an image-worker producer. Its payload retains status, original token
   and original payload pointer.

Alternate helper `609a9ac1` is called at `609a6371` and uses a different native
service (`60434a21`), not these command 1 queue sends. No dedicated command 1
producer to 164/165 was found in the inspected API inventory. Raw byte searches,
absence of literal function pointers and containing-body decoding do not
exclude computed calls, another direct kernel producer or runtime replacement.

## What the transaction/token machinery actually does

Native initializer `609a69ed` sets generated-token counter `626882bc` to 1,
clears staging count `626882c0`, forty 20-byte rows at `a2a5e3b8` and seven 32-byte
staging records at `a2a5e6d8`. These are native state tables, not spare lock space.

Stager `609a6a20` copies a 16-byte request for kind 0, or a 12-byte reply into
staging+16 for other kinds, and records the kind at +28. Main `609a6a87` calls
`609a6ac7` for staged records before clearing the batch.

For kind 0, `609a6ac7` builds a local record from the staged request, generates
and increments the counter, and calls `609a6bcc` at `609a6b7d`. The allocator
finds a row with word+0 zero, stores generated token at +0 and copies the four
original packet words to +4..+16. It does **not** compare payload or J identities
with occupied rows. Generated token and the original packet token at row+8 are
different values with different roles.

The crucial bound is earlier in this same body:

1. `609a6ae5` clears a 324-byte graph-result list at local SP+40.
2. There is no native call or writer that populates it before `609a6b97`
   calls consumer `609a6c22` with that same list.
3. Row allocation writes transaction state, not this caller-private list.
4. The consumer therefore sees count 0 and returns 0. Internal D2=`9c01` is
   overwritten by that return; it is **not** the complete function's D0 result.

The neighboring trace hooks `61770f5a/61770f62/61770f6a/61770f74` are actual
no-op stubs in this image. They are not missing emulator implementations of a
live graph scheduler. This shape is consistent with an omitted/disabled graph
connector, but its build intent and runtime code replacement are not proven.
Do not describe the whole ISEQ subsystem as disabled.

Consumer `609a6c22` has conditional logic for a nonempty list: state 3 matches
generated tokens in the row table, calls response sender `609a6ceb`, then clears
the matched 20-byte row. States 2/4 can request a retry. Those branches are not
reached from the actual zero list on this native path. Supplying invented graph
states would test different inputs, not reproduce a stock acknowledgement.

## Bounded native controls

`scripts/epl9_iseq_protocol_probe.py` freshly decodes the exact stock windows
and pins the relevant call inventories. Its only model is the existing explicit
`assumed-byte-fill` software contract for external ROM leaf `4700111e`.
The caller stack is poisoned before use; all 324 result bytes are checked zero
at consumer entry. No graph output, queue success, kernel, IRQ, worker, executor
or hardware completion is supplied.

The useful controls are:

- Two declared kind 0 staged inputs with identical packet/payload values occupy
  rows `[1, original packet]` and `[2, original packet]`, and both return D0=0.
  Payload is deliberately unmapped: it is retained as metadata, never treated
  as a successfully constructed or executed J.
- A declared kind 2 staged reply with the original token returns 0 and leaves
  those rows unchanged. This is explicitly injected reply metadata, not an
  observed worker or hardware completion.
- Kind 1 reaches the same empty-list consumer without allocating a row.

Every execution requires the exact return PC, restored SP, native callsites,
software-fill ranges, zero result list and absence of any dispatch. Unexpected
faults or outgoing calls fail closed. The reported status is
`bounded_connector_only`, never successful job reuse or completion.
Additional local capacity diagnostics do not establish real event arrival
rates, queue capacities or camera faults and are not a rationale for a patch.

## The separate active analysis/controller path

The public initialization flag is real state, not a permanently zero stub.
Getter `609a97d6` reads byte `a2b0abac`. Successful init `609a9559` sets it
through `609a95df -> 609a97cd`; teardown `609a9867` clears it at `609a98f9`.
Public submit `609a5c1f` validates input and initialization before `609a9220`.
These checks do not acquire per-job ownership.

Submission installs callback `609a918c` and user storage `a2b0ab70` in the
separate image-analysis service `6099536d`. Native `609965e9` writes a 52-byte
analysis result and invokes that callback at `60996670`. The callback copies
those 52 bytes through `609a95f3` and posts controller command 0 via `609a6dab`.
This connects an active service to a controller; it does not write the private
324-byte list in `609a6ac7`.

The controller is task 137 (`0x89`), `ISEQ_SUB`, descriptor `60419bc0`, entry
`609a6d7e`, declared stack 4096 bytes. Number 223 is its **event flag**, not a
message queue. `609a6dab` writes command metadata at global `a2b0ab64` and sets
flag mask 1 (bit 0). The task waits via `609a6e23`, snapshots that command, dispatches
through `609a6e90`, and returns to its wait only after the handler returns.

Command 0 reaches `609a71b5`, with these locally synchronous branches:

- `609a7280 -> 609a731e -> 609a7b18`.
- `609a7387 -> 609a7487 -> 609a7d84`.

They create stack-local owner arenas W at the respective caller's SP+32 or
SP+40, retained in local input+12/config+32. Constructor helper `609a8589`
preserves W while clearing configuration, calls `6074df04` at `609a8639`, and
publishes returned J to W+12 at `609a8642`. Calls at `609a7d68/609a7fd6` enter
`609a8e3f`, which loads W+12 and performs start/executor/drain. Subsequent
`609a7d7a/609a7fef -> 609a8ed8` destroys J, then clears W+12 at `609a8f1c`.
Only then can this controller activation return to wait for another command.

Eight native producer/alias fragments independently confirm selection, packet
fields, command 1 double dereference and the W+12 publication/reload/clear aliases,
with no call models or hardware completion. These are fragments and static
call ordering, not a completed ISP run.

This route supplies a concrete sequential J lifetime, but W+12 is not the
command 1 wrapper's word 0. No native join between them was identified. Asynchronous
analysis result storage can still be overwritten; all callback/IRQ aliases,
runtime task instantiation and complete hardware quiescence remain separate
qualifications. Sequential controller dispatch is not universal reentry safety.

## Reproduction, preserved work and next boundary

```sh
python scripts/epl9_iseq_protocol_probe.py --out local/new-iseq-protocol-run
python -m unittest discover -s scripts -p test_epl9_iseq_protocol_probe.py -v
```

All 369 source unit tests, compileall and whitespace checks pass. Optimized
(`python -O`) CLI use is rejected before output is created. Stock, frozen v3,
private-COLOR v3 and the separate native-source main/module identities were
rechecked unchanged. These are source/native-fragment checks, not camera passes.

Qualified output and source identities are retained under
`local/cloud-iseq-job-lifetime-20261111/probe-v2/`. Supporting producer,
transaction and definition reports/listings stay in that parent directory.
No original BIN, decoded image or candidate is included in source control.

The remaining command 1 proof now requires an actual live producer or graph
connector/runtime replacement, its payload→wrapper→J binding, destination 164/165
selection and matching 172 acknowledgement/reuse discipline. The nominal task
names and token table alone cannot supply it. No safe exclusion patch follows
from the available evidence, so none was added. Preserve the positively traced
native owner/controller lifetime and the separate recipe integration variants.
