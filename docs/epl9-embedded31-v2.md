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
