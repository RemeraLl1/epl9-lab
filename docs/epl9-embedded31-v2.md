# Embedded film library V2: separate from the SD extension

## Owner decision, 2026-11-13

V2 must contain **all 31 film recipes inside the firmware**, replacing the old
ART looks. An SD card is not required for those recipes. The later Delete
extension selects **additional** recipes from the card, then returns to the
built-in film library, not to the original Olympus ART effects. 31 is therefore
the built-in target, not a total library limit.

The older proposal to reserve some of the 31 positions exclusively for SD is
superseded. The earlier two-slot T1/T2 prototypes and bank-controller tests are
research inputs, not the release layout.

Keep the existing native-source-v1 Gold/Portra candidate unchanged:
`10ac83e9beb9dd1bfd12aa6a021135706875d6ea245e58e20ec07fb917229421`.
The `v3` in that candidate's filenames is its recipe-generation name; this
new **release V2** is a separate generation, not an in-place overwrite.

## What can honestly be frozen now

The scope is fixed, but a second installable firmware has **not** been produced
or frozen. Do not assign a firmware SHA, claim 31 embedded looks, or use the old
2-look binary as V2. The prerequisites below are implementation work, not extra
camera backup requests.

- Recover the actual V6 renderer and Astra R3 source/parameters; the recovered
  31-name roster is in [future recipe banks](epl9-future-recipe-banks.md).
- Port the effects to actual E-PL9 controls, with unsupported spatial/grain
  operations called out rather than silently omitted. Name lists are not recipes.
- Establish every visible ART selection and its processing identity, then bind
  the 31 looks, labels and icons. A 31-record serializer does not prove 31 menus.
- Connect retained built-in descriptors and correct routing for each selection;
  no SD or Delete hook belongs in this V2 candidate.
- Build and fingerprint a separate source-reproducible package, keep the first
  candidate intact, and distinguish native/configuration tests from camera output.

## New exact-stock coverage result

`epl9_embedded_art_inventory.py` reads only the exact stock decoded main. It
inventories the two worklist tables already located in the E-PL9:

| Table | Capacity | Occupied rows | Unique keys in table |
|---|---:|---:|---:|
| ART `608f22c0` | 32 | 19 | 19 |
| Special `608f23c0` | 16 | 12 | 12 |

All 12 special keys also occur in the ART table. Thus **31 occupied rows mean
19 unique processing keys, not 31 distinct ART positions**. This does not say
there are only 19 possible UI selections: other modes can take default/other
paths, and label aliases are not processing keys. It prevents an invalid
one-row-per-recipe assignment.

Watercolor keys `01010078` and `01020078` share `607521db` and occur only in the
ordinary ART table. Other keys have different special and ordinary targets.
The V2 route cannot be generalized merely by increasing the existing 2-recipe
array to 31 or copying the Watercolor hook over every row.

The JSON audit preserves null recipe/UI bindings for unresolved keys and reports
`install_ready=false`. It emits only interpreted metadata, never firmware bytes.

```sh
python -m unittest discover -s scripts -p 'test_epl9_embedded_art_inventory.py' -v
python scripts/epl9_embedded_art_inventory.py --main local/private/main.bin
```

Verified with stock decoded main SHA
`8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
Four parser tests passed; the exact-stock inventory produced 19/12/19 counts.
No camera, SD, native instruction execution or physical update was performed by
this inventory. The existing private candidate and stock-return files were not
modified.

## 2026-11-14: 31 distinct UI choices located separately

The previous worklist-table warning remains correct, but it must **not** be read
as evidence that a new 31-position UI has to be invented. A new bounded audit
cross-checks three different stock main tables:

| Table | Address interval (end exclusive) | Record size | Records |
|---|---|---:|---:|
| Named ART choices | `615724d8..6157264c` | 12 | 31 |
| Choice decomposition | `6155d37c..6155d5e8` | 20 | 31 |
| Variant property mapping | `6155d648..6155d8d0` | 24 | 27 |

The first two have exactly the same 31 unique selection values **in the same
order**. The third covers 27 of them, matching base mode, variant and choice
resource. The remaining four are single-type choices: Soft Focus `9`, Light
Tone `b`, Gentle Sepia `10`, and Instant Film `3f`.

The 16 groups represented are Pop Art (2), Soft Focus (1), Pale & Light Color
(2), Light Tone (1), Grainy Film (2), Pin Hole (3), Diorama (2), Cross Process
(2), Gentle Sepia (1), Dramatic Tone (2), Key Line (2), Watercolor (2), Vintage
(3), Partial Color (3), Bleach Bypass (2), Instant Film (1): **31 UI records**.
English label identities were inspected in exact stock OSD through the pinned
Caduceus decoder already described in `epl9-watercolor-icons.md`; no OSD strings
or artwork are bundled in the new script.

### Native setter evidence, not just a row count

Static GNU decoding of `61169ccc..61169d60` shows the existing UI commit path:

- `61169cd3` loads table `6155d648`.
- `61169cdf..61169ce4` compares the selected value against each row's first word.
- On a match, `61169cf5..61169cfd` loads row +16 (base mode) for the first
  settings dispatch, whose property ID comes from the UI object's field +84.
- `61169d08..61169d17` loads row +8 (variant property ID), row +4 (variant), and
  makes the second settings dispatch.
- `61169d38..61169d3d` advances by 24 and stops after 27 rows.
- The fallback `61169d43..61169d5e` writes the selected value directly when no
  variant row matched.

For Watercolor I/II, rows are UI `1301/1302`, base mode `13`, variant `1/2`,
variant property `1d4`. These are distinct from processing keys
`01010078/01020078`. Do **not** substitute the UI key as a worklist key.
The two virtual property dispatches have not yet been followed into the capture
job producer. Other runtime mode restrictions can still affect visible choices.

### Consequence for V2

There is now a concrete existing **31-record UI surface** to target rather than
an invented 31-row extension of a 19-key hash table. The next integration step
is to join base-mode plus variant settings to the processing-key producer and
validate preview/capture consumers. This audit does not bind any V6 recipe,
install a menu patch, or assert all 31 choices are active on hardware.
`processing_key` and `embedded_recipe` deliberately remain null in its output.

```sh
python -m unittest discover -s scripts -p 'test_epl9_art_ui_inventory.py' -v
python scripts/epl9_art_ui_inventory.py --main local/private/main.bin
```

Six synthetic parser/reconciliation checks passed and the exact-stock audit
passed with 31/27/4. This is static metadata and instruction inspection, not
native instruction execution, camera testing, or full firmware qualification.
The frozen candidate, stock-return, SD/Delete code and proprietary images were
not changed.

## 2026-11-14: native ART header producer, with an explicit missing join

The next step now has **bounded native execution**, not only static table
inspection. `scripts/epl9_art_header_probe.py` runs stock instructions from
`607d26a0` through `607d2756`, including the actual call/return of formatter
`60743621`. It uses the existing GNU-decoded MN103 subset and declared synthetic
RAM; there are no replacement-call models or TruePic stubs.

### What is demonstrated

For a declared owner `A`, the producer reads configuration pointer `C=A[152]`:

- `C+22955`: one-byte processing mode, copied into the formatter's first u16.
- `C+22926`: alternate u16 mode. Its ART branch is not used for mode >=100.
- `C+23688`: ART variant, used when mode >=100; zero becomes one.
- The formatter writes four bytes: group `1`, variant, u16 mode (little endian).
  Thus declared processing mode 120 and variant 1/2 produce `01017800` /
  `01027800`, corresponding to worklist keys `01010078` / `01020078`.
  The processing key notation is **not** the raw little-endian u32 of the bytes.

There is an important real branch after that call: owner operation (`A+72`)
`2001` or `2006`, together with submode (`A+86`) `2`, overwrites the header with
`00000200` (group 0, variant 0, identifier 2). The probe exercises both override
and non-override branches. It stops **before `607d2756`**: later producer code
contains further conditions. This is not a claim of final header preservation
for all capture operations.

20 executed controls passed: modes 100/120/255 with variants 0/1/2/3, and mode
120 variants 1/2 with operations 2001/2006 and submodes 0/2. Values 100 and 255
are boundary controls, **not a claim that these are usable camera modes**.
Every control executed one native formatter call and zero modeled calls.

### Static connection to the job producer

Separately inspected native callers provide a concrete next trace route:

1. `607ce515`, call at `607ce549`, sends its output buffer +8 to `607d26a0`.
2. `607d38d5`, call at `607d3904`, fills a 32-byte local parameter buffer via
   `607ce515`; call at `607d390e` passes it to job constructor `6074df04`.
3. Existing job audits describe the copied header and downstream worklist
   selector. This new probe does **not** execute the whole constructor or these
   caller functions, and does not identify all preview/video consumers.

The UI setter's two virtual dispatches have also been statically traced through
settings object getter `60b64310`, vtable `60e2d0ec`, first-slot function
`60b651b7`, underlying setter `60b91f18`, and native property path
`6069ba76` → `6069cc82`. This is a search route, not a completed semantic join.
**Still missing:** proof that UI base mode `13` and variant property `1d4`
actually write the producer configuration fields as mode 120 and variant 1/2.
Consequently the UI inventory keeps `processing_key=null`. No cross-join is
silently filled using matching labels or expected Watercolor values.

### Reproduce

```sh
python -m unittest discover -s scripts -p 'test_epl9_art_header_probe.py' -v
python scripts/epl9_art_header_probe.py --main local/private/main.bin \
  --reader local/mn103-tooling/mn103-reader
```

The reader must pass existing provenance verification and the image must match
the exact stock main hash listed above. Output contains summarized observations,
not OEM code or images. The four contract tests reject invalid domains, missing
native code, and a wrong stock image before reader execution. Together with the
20 stock controls this advances the UI→job investigation without inventing the
remaining join. Preview/capture parity, all 31 per-choice processing bindings,
physical rendering and V2 install readiness remain unproven. Frozen V1 and
stock-return artifacts, SD/Delete behavior, and recipe coefficients are unchanged.

## 2026-11-14: backing properties and the active-variant gap

A further exact-stock inventory connects the 12 variant properties used by the
27 non-singleton UI rows to one shared storage family. Native helper
`606ba478..606ba4ca` indexes a primary table `608aca18` with property ID *4
for IDs 0..1619; its first u16 is the backing storage ID. Helper
`606ba68f..606ba6a8` reads the second u16 as element index. Generic setter
`606ba3a6` uses both before calling storage writer `6043e702` at `606ba3f2`.

All 12 variant properties resolve to storage `44c1`, but **different elements**:
`16b/16c/16d/16e/16f/170/171/1d4/253/294/296/5ad` map to indices
`1/2/3/4/5/6/7/8/9/10/11/12`. In particular Watercolor property `1d4`
is `(44c1,8)`, **not `(44c1,0)`**. Property `6f` maps to `(9481,0)`;
its identity as the specific UI object's base-mode property is still a candidate.

The capture-configuration assembly fragment gives the other end:

- `60693cd3..60693ce2` calls reader `6043e62b` with storage `44c1`, index 0,
  then writes its returned byte into configuration offset 23688.
- `60693ce6..60693cfb` calls that reader with storage `9481`, index 0,
  then writes its returned byte into offset 22955.
- Reader `6043e62b` forwards the index to `6043eb2a`; the latter indexes the
  returned storage buffer. Thus index 0 is not silently reinterpreted as 8
  by this inspected reader path.

This is a useful constraint, not a completed link: changing the saved Watercolor
variant alone is insufficient evidence that the current capture variant changes.
We must find the activation/copy/notification path from saved slot 8 to active
slot 0, and the base-mode conversion to processing mode 120. Property mutation
`6069d4eb` can dispatch per-property callbacks via runtime registry `6261f3e8`,
then notification helpers; those dynamic bindings have not been reconstructed.
No absent callbacks were stubbed or treated as no-ops.

```sh
python -m unittest discover -s scripts -p 'test_epl9_art_property_inventory.py' -v
python scripts/epl9_art_property_inventory.py --main local/private/main.bin
```

Four parser/guard tests and the stock 12-slot audit passed. This addition is
static evidence, distinct from the preceding native header probe. The original
stock image is available locally; further reverse engineering is **not blocked
by a missing image or missing recipe coefficients**. Completing 31 actual film
recipes still separately requires the authored coefficients and per-choice
processing bindings. No firmware artifacts or frozen release inputs changed.

## 2026-11-14: saved-to-active activation route located

The previous active-slot question now has a concrete native route. A new probe
executes the actual registry builder `6069d798..6069d7ea`: it hashes 311 stock
60-byte descriptors starting at `60813a24` into declared RAM at `6261f3e8`.
Executing native lookup `6069d7ed` for property `1d4` returns descriptor
`60816c88`, whose +24 post-change callback is `606a1ae1`. This is no longer an
invented callback binding, although actual camera startup invoking the builder
has not been demonstrated.

The callback reads current UI mode through `6069cc01`, compares it to decimal
19 (`13` hex), and only on a match calls `606a3f37` with mode19 and context0.
That routine calls `606a38bf`, whose native jump table `6083cd2c` sends mode19
to `606a3d0b`. This branch reads saved variant property `1d4` through
`6069e27c`; its returned value goes into local +4, then output +32 at
`606a3ee3..606a3eea`. Caller `606a3f37` passes that output value to setter
`6069e295` with destination property `16a`. Its native dispatch resolves to
`6069cc7d`, the ordinary property setter. The previously audited backing table
maps **source1d4→44c1:8 and destination16a→44c1:0**.

`epl9_art_activation_probe.py` executes the registry construction and lookup,
plus bounded dataflow slices for variants1 and2 and a non-Watercolor callback
control. The slices verify the actual jump-table choice, source getter
arguments, variant retention/output offset, destination setter arguments, and
indirect setter target. They explicitly supply the declared getter return at
that boundary; they **do not execute storage reads/writes or claim a continuous
end-to-end mutation**. No called native function is replaced by a software
model. Other color/effect properties processed between these slices are not
implicitly assumed to succeed.

```sh
python scripts/epl9_art_activation_probe.py --main local/private/main.bin \
  --reader local/mn103-tooling/mn103-reader
```

The probe passed against the exact stock image. The remaining base-mode
conversion (UI19 versus processing120), complete callback lifecycle, and
preview/capture output still need investigation. This result narrows the gap;
it does not make V2 install-ready or change the frozen firmware.

## 2026-11-14: UI19 → processing120 conversion executed

The base-mode gap is now narrowed to the real storage/notification boundary.
Property `6f` is a **composite setting**, not a scalar identity conversion.
Its conversion descriptor at `608a33f8` has type6, record size64, data length1600
(25 records), value data at `608925c8`, and logical labels at `60885bd0`.
Logical UI label19 is record index20, address `60892ac8`. Its first raw value is
120. Adjacent logical labels are not safely convertible with a fixed offset.

New `epl9_art_base_mode_probe.py` executes, with no modeled calls:

1. Stock callback-registry builder (311 descriptors).
2. Stock conversion-registry builder `606a5932` (1200 descriptors).
3. Property setter `6069cc82`, with declared property6f and logical UI value19.
4. Native conversion via `606a5251` and its table lookup helpers.
5. Compound-property dispatch through `6069d4eb` and `6069ce1d`.

Execution stops at `6069ce3f`, immediately before its call to raw property
writer `6069cbd9`, with **d0=6f, d1=120**. There are 826 executed instructions
in this setter path, excluding registry construction. Controls UI18→119 and
UI8→100 also passed (814 and 694 instructions respectively). All intervening
called functions on these paths were actual loaded instructions, not success
stubs. Registers/stack are declared fixtures, not a captured camera session.

The prior storage inventory connects raw property6f to `(9481,0)`; the capture
configuration assembler reads that storage into offset 22955; the header probe
shows mode120 and variants1/2 produce Watercolor worklist keys. These pieces now
have a concrete conversion bridge. **Still not claimed:** raw storage write,
notification completion, whole UI-object commit, complete capture producer,
TruePic output, or full preview/capture parity. The mutation boundary is
intentional: uninitialized storage/service state is not replaced with pretend
success. The separate variant activation probe retains its explicit declared
getter-return boundary.

```sh
python scripts/epl9_art_base_mode_probe.py --main local/private/main.bin \
  --reader local/mn103-tooling/mn103-reader
```

All three exact-stock controls passed. No frozen candidate or OEM image was
changed or published. This is useful executable reverse-engineering evidence,
not a new installable firmware build.

## 2026-11-14: native RAM registration and raw write/read, service boundary

`epl9_art_storage_probe.py` advances past the previous raw-write boundary without
inventing successful service calls. It executes native descriptor-registration
fragments from `6043d697` using three actual stock record headers:

| Storage | Stock descriptor | Elements | Purpose in this investigation |
|---|---|---:|---|
| `9481` | `6049a5cc` | 1 | Raw processing mode |
| `44c1` | `60477ca0` | 13 | Active and saved ART variants |
| `8b54` | `604955d8` | 1630 | Property-associated metadata writes |

The initializer writes real index entries at `a2abc6cc + (storage_id>>4)*8`.
Its output data pointers refer to explicitly declared zero-filled RAM buffers.
The probe stops each initializer fragment before it advances into the next
unrelated descriptor: **this is not the complete service/startup sequence or a
copy of the camera's persistent settings**.

With explicitly declared context-selector0, write-lock0 and lazy-cache-init0,
actual instructions of raw writer `6069cbd9` complete, including metadata,
storage resolution, and byte writes. Actual storage reader `6043e62b` returns:

- property6f=120 → storage9481[0]=120;
- property1d4=2 → storage44c1[8]=2;
- property16a=2 → storage44c1[0]=2.

No helper calls are modeled. This demonstrates direct **RAM** mutation/readback
under the stated state, not live camera settings, NVRAM persistence, or a complete
UI callback chain.

### Why this is not reported as complete cross-context validation

A contrast with context selector1 at `8050` takes a different real branch:
writer `6043e702` calls `6043e3b4` instead of direct writer `6043e76a`. The probe
requires an explicit external-call stop there. Static inspection shows the
service path invokes state/locking helpers, updates a 16-entry ring at
`a2ad2710`, and dispatches a callback through `604383c1`; its lock/scheduler and
startup state have not been qualified. Substituting a success return or forcing
mode0 would conceal the exact missing behavior. Full initialization itself
also invokes these service helpers and depends on previously populated settings
buffers. There is no missing stock-image blocker, but live service emulation
is a separate required next step for continuous writes/notifications.

```sh
python scripts/epl9_art_storage_probe.py --main local/private/main.bin \
  --reader local/mn103-tooling/mn103-reader
```

Three native write/read controls and the cross-context stopping contrast
passed. No new installable image is produced; frozen artifacts are untouched.

## 2026-11-14: queued native write and the cross-context boundary

**Terminology correction:** `8050` must not be called a boolean service-mode
flag. Dispatcher `604383c1` compares its requested context with this selector:
matching contexts call the callback directly, differing contexts choose separate
queues. Observed branches distinguish0/1/2. The previous0/1 experiments remain
valid but do not prove that a service was switched off/on. Script output names
and the preceding section now use context selector.

The new `epl9_art_queue_probe.py` executes the actual producer serialization
fragment `6043e3e4..6043e448` and consumer `6043e341`. Its scope is deliberately
split: producer inputs are declared at the **post-lock** boundary; the consumer
is then explicitly invoked, not claimed to have run through a scheduler.

Verified native behavior for operation1 (single-value write):

- Queue base `a2ad2710`,16 records ×28 bytes; head/tail at +448/+450.
- Producer records operation, storage ID, element index, destination pointer and
  value. It does not yet mutate the destination.
- Consumer dispatches operation1 to real writer `6043e76a`, writes120 into the
  declared mode buffer and advances the tail to the head.
- Both ordinary slot0→1 and wraparound slot15→0 pass.
- Full-queue contrast takes the rejection branch without writing a payload or
  destination. The head has already wrapped before that branch; subsequent
  error/recovery behavior is deliberately not inferred or silently repaired.

Executing dispatcher `604383c1` with target context0 and current context1
now executes helper `604113a1` using declared context-control RAM, then stops
at `6041894e` (`mov psw,d0`). The following code modifies the processor status
word and interrupt state. Those CPU/kernel semantics are not qualified by this
probe; no successful lock or callback is fabricated. Static routing passes consumer `6043e341` to this dispatcher from
`6043e456..6043e45e`. This establishes the queued payload→native consumer→RAM
write link, **not cross-context scheduling, lock correctness, notification
completion or durable persistence**.

```sh
python scripts/epl9_art_queue_probe.py --main local/private/main.bin \
  --reader local/mn103-tooling/mn103-reader
```

Ordinary/wrapped writes, full-queue rejection and cross-context stop passed on
exact stock code. No called functions in the executed slices are modeled.
The remaining integration boundary is now explicit: native synchronization and
cross-context dispatch, not a missing ART recipe or guessed header format.

## 2026-11-14: qualified opt-in PSW register semantics

The PSW instruction boundary can be advanced using an authoritative semantic
reference, without inventing interrupt delivery. `mn103_subset.Machine` now
accepts explicit `psw=...` initialization; existing callers without it still
reject PSW instructions. Only four exact encoding forms are admitted:
`mov PSW,Dn`, `mov Dn,PSW`, `and imm16,PSW`, and `or imm16,PSW`.
PSW NZCV bits remain tied to the subset's arithmetic flags. In particular PSW
AND/OR modify the word directly; they do **not** perform the ordinary logical
instruction's NZCV recomputation. Interrupt delivery, privilege enforcement,
asynchronous scheduling and a complete CPU model are not implemented.

Semantics were checked against the same pinned GNU simulator revision used by
the existing subset:

- [GNU mn10300.igen](https://gnu.googlesource.com/binutils-gdb/+/87ffb882e0f4d73401a0746177ffabb8e8bbe4ac/sim/mn10300/mn10300.igen),
  move forms at lines120–143, PSW AND at2348–2360, OR at2424–2436;
  decoded-source SHA256 `355754c61879dc24bf6128bbba5a7931355731000e8cb213082b9b9cd4df0129`.
- [GNU mn10300-sim.h](https://gnu.googlesource.com/binutils-gdb/+/87ffb882e0f4d73401a0746177ffabb8e8bbe4ac/sim/mn10300/mn10300-sim.h),
  NZCV masks1/2/4/8 and interrupt-enable bit11;
  SHA256 `9ba3ea7e3ec929b2235a8859c35711208b7ad8dd52b7543dc1d844757be4874a`.

Six focused PSW tests cover move read/restore, flag preservation, direct logical
semantics, ordinary arithmetic preservation of control bits, wrong encoding and
opt-in rejection. All 49 MN103-layer tests passed. These are implementation
controls, not a claim of independent silicon validation.

### Native context helper now completes

Queue probe v2 executes the previously blocked `604113a1`, including native
`6041894c`/`60418975` PSW save/mask/restore, with declared context-control RAM.
The helper sets context byte+2 and the expected control bit, restores the PSW
control bits, then returns to dispatcher address `604383fd`. A busy-context
control returns -25 and does not set the success flag. No lock-success return is
stubbed. The existing native queue producer/consumer controls continue to pass.

The next boundary is **after this helper**, in the cross-context dispatch and
mailbox/scheduler path. The producer's earlier lock acquisition is still outside
the queue serialization slice, and consumer invocation remains explicit. Thus
this result does not convert the queue probe into full asynchronous firmware
emulation or prove notification completion. Frozen firmware remains unchanged.

### Cross-context callback mailbox (native slices, 2026-11-14)

`scripts/epl9_art_mailbox_probe.py` advances beyond the PSW helper without a
successful-lock stub. On the pinned private stock main image it executes
`604383c1` through `60438486`, stopping **before** unlock helper `60411489`.
For target context 0, sender 1 selects callback bank `a2abb744`, sender 2 selects
`a2abb844`. Each bank has 32 eight-byte entries: callback pointer and argument.
Dispatch scans for a zero callback, stores `6043e341` and queue argument
`a2ad2710`, and forms token `(sender << 16) | slot`. Native selector callback is
`604384ea`. This is callback publication, not proof of asynchronous delivery.

The context-0 receiver's post-receive slice `604385ba..604385e4` decodes the high
16 token bits as sender and low 16 as slot, selects the same bank, calls the
stored callback with its stored argument, then clears the callback pointer.
Six executable controls cover senders 1/2 and slots 0/7/31. Each executes this
receiver slice and the actual queued storage callback `6043e341` / writer
`6043e76a`, reads back raw mode 120, advances queue tail to 1, and releases its
mailbox slot. Dispatch uses 99–318 native instructions; receive/write uses
76–77. Earlier occupied slots are fixtures, not executed callbacks.

Reproduce locally with the exact private stock image and validated GNU reader:

```sh
python scripts/epl9_art_mailbox_probe.py --main /private/main.bin --reader /private/mn103-reader
```

**Explicit gap:** the test supplies a pending storage record and transfers the
produced token to the receiver's stack manually. The current selector is also
explicitly switched to 0. It does not fake execution of the missing interval.
Unlock `60411489` calls additional kernel helpers `60418889`, `60415995`, and
`60418900`. Dispatcher then calls `60437feb`; callback `604384ea` passes a runtime
handle from `a2abb948` to `60411ca6`. The worker obtains that handle through
`60431fd5` and waits via `60416bf7`. Those RTOS creation/wait/wake and interrupt
paths require grounded scheduler/control-state work, not merely an empty bank.
Their successful lifecycle is not demonstrated here. This narrows the ART
transport gap to explicit boundaries but is not a UI-to-processing end-to-end
proof, preview/capture equivalence, installation readiness or safety evidence.
Frozen Gold/Portra and SD/Delete are unchanged; no OEM image is published.

### Native RTOS ring transport (probe v2, 2026-11-14)

The mailbox probe now also executes the native data-queue initializer
`60410bc3`, send slice `60411d4f..60411d9c`, and nonblocking-data receive slice
`60416cc0..60416db5`. It no longer injects the token directly into the worker's
receive slot: the send instructions store it in the RTOS ring, and receive
instructions fetch it and write the worker output pointer. The subsequent
worker callback still writes raw ART mode 120 and releases the callback slot.
All six controls pass, including last-entry wrap for both sender contexts.

Object layout derived from these instructions: configuration at +20, capacity
+24, backing buffer +28, write cursor +32, read cursor +36, last-entry address
+40, free-entry count +44; sender and receiver wait-list heads are +4 and +12.
The real worker requests capacity 33 through `60431fd5` -> `60410137`.
Creation obtains an object from `60415177`, copies the configuration and calls
`60410bc3`. Stock passes a NULL backing pointer, causing allocation through
`6041600d`. Probe v2 instead exercises the initializer's supported non-NULL
backing-buffer path with declared RAM. It does **not** claim that the actual
stock heap allocation or handle-creation lifecycle ran successfully.

This is a useful reduction, not elimination, of the transport gap. The token
is still supplied at the send slice's input and stages are invoked explicitly.
Dispatch first traverses another cross-context transport (`60437feb`), whose
queue-selection table is at `604560ec` and whose lock/interrupt handling has
not been executed here. Callback `604384ea` then uses runtime handle
`a2abb948` to call the RTOS send function. The queued-data path is covered;
empty-queue waiting and wakeup of an existing waiter instead require kernel
scheduler paths (`6041442d`, `60414508`, `60414482`). These are not replaced by
success stubs. Full startup, allocation, scheduling, notifications and camera
behavior remain outside the evidence. No frozen firmware changed.

### Intermediate transport ring (probe v3, 2026-11-14)

The same executable probe now follows the intermediate cross-context ring
rather than copying the dispatch token directly to the RTOS send entry.
It loads the actual ROM descriptor at `604560ec + target*48 + sender*16`.
For target 0 / sender 1 the descriptor gives head/tail `a2abb12e/f`, ring
`a2abaf2c`, signal mask `0x10`; sender 2 gives head/tail `a2abb130/1`, ring
`a2abb02c`, signal mask `0x20`. Each transport ring has 32 entries of callback
and argument, distinct from both the callback bank and the RTOS token ring.

Native sender slice `60438037..604380ad` checks space, writes callback
`604384ea` and the dispatch token, and advances its head modulo 32. It stops
before reading interrupt state or writing the signalling register. Explicit
receiver invocation at `60438121` / `60438175` then reads that stored callback
and argument and calls the actual wrapper `604384ea`. At `604384fa`, its native
registers contain runtime-handle fixture 1 and the token fetched from transport
RAM. The subsequent RTOS send/receive and ART callback slices use that result
in the same machine and memory. All six controls pass; final-slot controls
exercise both transport producer wrap and RTOS ring wrap.

The remaining gaps are smaller but important: entering the sender after its
lock, calling its receiver instead of delivering a hardware interrupt, and
bridging the wrapper's send call to the post-validation RTOS slice. The
transport consumer is stopped inside its callback; its post-callback tail
advance has **not** executed in this probe. No pending task is magically resumed.
The three ROM signalling-register pointers are `99200408`, `99300408`, and
`99b00408`; merely mapping these as RAM would not prove interrupt behavior.
The native decoder also labels the earlier descriptor multiplication instruction
`udfu01`; this probe does not invent CPU semantics for it, and uses the verified
ROM descriptor directly. Runtime handle creation and heap allocation remain
unproven. This is connected data-path evidence, not a complete scheduler or
UI-to-rendering run. Frozen firmware remains unchanged.
