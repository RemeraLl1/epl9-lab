# SD recipe files: working computer-side route

2026-11-11. The available cloud source now provides a concrete route for
checking editable recipe definitions, staging already compiled records into
two independent logical slots, checking the staged files, and rehearsing
fallback selection. All writes remain in new directories under ignored
`local/`. No physical card preparation, firmware package or camera operation
is performed.

The exact main component and later Windows shutdown implementation remain
unavailable. The author exporter still requires the real stock gamma; this
follow-up does not replace it with a synthetic or identity curve. T1/T2 are
offline test aliases, without confirmed camera menu entries. The eventual
default recipe library is still undecided.

## 1. Check an editable recipe now

```sh
python3 scripts/epl9_sd_recipes.py validate-author recipes/epl9-sd-example-v0.json
```

This works without firmware. It checks the schema, required fields, recipe
ID/name, all twelve HSL triplets, contrast, H/M/S, native-order WB multipliers
and gamma-knot bounds/order. Controls are validated by the same range rules
as the record codec. It creates neither a gamma table nor an RCP file;
the result explicitly says `gamma_compiled=false` and `record_exported=false`.
JSON author/manifest reads are bounded to 64 KiB and reject duplicate keys
and nonfinite numbers. A Windows UTF-8 BOM is accepted.

The example remains a template, not a calibrated film look. Make changes in
a separate research copy rather than changing frozen v3 definitions.

## 2. Compile when the exact main is restored

```sh
python3 scripts/epl9_sd_recipes.py export local/my-look.json \
  --out local/new-look/SLOT01.RCP
python3 scripts/epl9_sd_recipes.py inspect local/new-look/SLOT01.RCP
```

This step is **currently blocked**. The required private input is
`local/epl9-1101-analysis/decoded/00_0100_406e0020.decoded.bin`, 26214336 bytes,
SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
The unchanged compilation rule composes the authored knots with its exact
native gamma. An actual export attempt on the public author example returned
the missing-input error and created no output file.

Already compiled valid records can be staged without reading firmware: their
final curve values are retained byte for byte. Staging does not compile new
curves, convert desktop recipes or qualify their photographic appearance.

## 3. Stage a checked pair of compiled files

[The bundle tool](../scripts/epl9_sd_bundle.py) binds input records by the
explicit destination option, regardless of the source basename or recipe ID:

```sh
python3 scripts/epl9_sd_bundle.py stage \
  --slot1 local/look-a/SLOT01.RCP \
  --slot2 local/look-b/SLOT01.RCP \
  --out local/new-recipe-pair
python3 scripts/epl9_sd_bundle.py verify local/new-recipe-pair
```

The resulting local directory is:

```text
new-recipe-pair/
  manifest.json
  EPL9MOD/
    SLOT01.RCP
    SLOT02.RCP
```

Omit `--slot2` or `--slot1` to leave that slot without a file. Use an explicit
`--defaults-only` instead of either option to stage no override files. These
cases preserve independent fallback; no dummy or empty RCP is generated.
One record may occupy either or both logical destinations. No fixed/native
ART identity is selected by the record's ID or name.

Every input must already satisfy the complete 660-byte model/build/ABI,
CRC/range/name/curve contract. All inputs are snapshotted before output is
created, so a bad second input does not create a partial accepted pair.
Existing output directories and physical-card destinations are refused.
The tool never overwrites an older staged pair.

The manifest pins exact paths, record sizes, SHA-256, IDs and names. `verify`
rechecks full record contents and rejects changed/missing/extra files,
unassigned slot numbers, symlinks, retargeted paths and malformed metadata.
All camera qualification fields must remain false. The manifest detects
differences from the recorded choice; it is not an authenticity signature.
Names in the report do not implement dynamic camera labels.

## 4. Rehearse selection with explicit research defaults

```sh
python3 scripts/epl9_sd_bundle.py rehearse local/new-recipe-pair \
  --fallback1 local/research-default-a.RCP \
  --fallback2 local/research-default-b.RCP
```

Both fallback inputs are required and independently validated. Their use in
this model does not choose the eventual embedded library. The command first
verifies the bundle, then copies its immutable record snapshot into a private
temporary directory and runs the existing host resolver. The report includes
the selected source/name/ID/hash for T1/T2 and an unchanged built-in reference.
It cannot be mistaken for camera execution: native task/file-service,
physical SD, menu assignment and installation flags remain false.

## A complete source-only demonstration available now

```sh
python3 scripts/epl9_sd_workflow_probe.py --out local/new-sd-workflow
python3 scripts/epl9_sd_bundle.py verify local/new-sd-workflow/both
python3 scripts/epl9_sd_bundle.py rehearse local/new-sd-workflow/both \
  --fallback1 local/new-sd-workflow/synthetic-inputs/record-0.RCP \
  --fallback2 local/new-sd-workflow/synthetic-inputs/record-1.RCP
```

The probe deliberately generates four **synthetic format/range controls**,
including artificial gamma values. They are not exports of the author
example, Gold/Portra v3 records or replacements for the missing stock curve.
Generated files are local test artifacts, not a card installation kit.
The first command requires the already qualified GNU MN103 reader described
in [cloud portability](cloud-portability-20261110.md).

Retained run: `local/epl9-sd-workflow-20261111/validation.json`, SHA-256
`c618513ff9b632000dc4b6aeb7f86d870d6f74fc981e9ba72cd4345044b0dcea`.
It records ten exact source identities and the actual decoder provenance.

- **60 SD unit methods pass**: the earlier 48 plus 12 author/bundle checks.
  The existing 1158-record host acceptance corpus still agrees with its
  authored expectations after extracting common control validation.
- **Six valid staged scenarios pass**: no override files, either single file,
  both, exchanged files and the same record in both destinations.
- **Three altered bundles are rejected**: bad CRC, an extra byte and a
  different model with a recomputed CRC. Separate resolver/native-loader
  checks select fallback for the bad first file and preserve the good second.
- **34 native invocations pass their scoped expectations**. GNU independently
  decodes the unchanged 1322-byte standalone loader. Selected records match
  the host byte for byte. After both accepted and completed missing-file
  attempts, changing the supplied file does not reopen it or change the
  retained selection.
- **Four resource boundaries retain their established semantics**: uncertain
  close keeps file/buffer owned; pending read supplies no fabricated reply or
  free; SD-not-ready allocates nothing; allocation failure keeps fallback.
- Real CLI `stage`, `verify` and `rehearse` commands also completed. The
  original standalone loader SHA remains
  `ed4d4e9055d00393ad1eea267bd265abf4261c3a12fd1980cac7ad216f15d357`.
  The current sample record also matches all 660 bytes of the synthetic
  fallback retained before the host refactor.

The native workflow uses a separate fixture per logical slot, with declared
file/task/pool services. It executes authored loader instructions, not stock
file wrappers, the shared HLS manager, the RTOS or SD hardware. In particular,
independent fixture progress does not imply that T2 can run while T1 blocks
the shared event task. The later shutdown implementation is not executed or
recreated. No native processing configuration or image output is produced.

## Remaining transition to an actual camera route

| Gate | Current status |
| --- | --- |
| Editable JSON validation, record inspection, local staging and host rehearsal | Working with the scoped checks above |
| Export an authored record using the exact stock gamma | Blocked on the identified private main; no alternative curve substituted |
| Integrate/review the reported BUSY/NULL shutdown behavior | Blocked on the five actual later sources and retained evidence |
| Prove HLS_EVENT termination and complete five-list/external borrowers | Still open; [the stock-only inventory route](epl9-hls-stop-cloud-boundary.md) is prepared but lacks its main input |
| Native menu/label/settings assignment for T1/T2 | Unqualified; aliases remain offline |
| Placement, full lifecycle, cache/DMA, physical SD and camera processing | Existing offline evidence only; no new qualification here |

The separate Watercolor v3 candidate, accepted recipe character and recovery
work are unchanged. Missing private candidate data prevents a fresh full
candidate/package regression. Earlier native reports keep their historical
source identities; they are not silently resealed after this host-only
change. `install_ready` remains false.
