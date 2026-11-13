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
