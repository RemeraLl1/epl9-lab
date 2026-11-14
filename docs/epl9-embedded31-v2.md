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
