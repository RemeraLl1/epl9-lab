# E-PL9 v3: component verification, synchronization and memory

Follow-up, 2026-11-07. Gold 200 v3 and Portra 400 v3, the module,
both packaged binaries and the stock example photographs remain unchanged.
This pass is entirely local. No camera command, card preparation or flash write
was performed. **Physical installation and recovery are still unqualified.**

## Exact inputs

Olympus E-PL9 / model 1330, body version 1.1 reported by the owner;
downloaded main build 1101, not an installed-camera dump.

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| Stock update | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Stock decoded main | 26214336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |
| Frozen v3 decoded main | 26214336 | `501707d09a0eb648e46196752b7ece17cd5368f6d54dbabce7c73e9806f65686` |
| Frozen v3 decoded OSD | 26214336 | `50141904c211fd16bc4c26b35cd52955f96a9e611ca062d84fe0169eeda21b3b` |
| v3 package | 52428800 | `8d606a028f4b533db6431f1a0271a92d8f3f1c71e08833b481dcb2310d79ef8f` |
| Stock restore package | 52428800 | `10a7b949d1509ce627cb3c098c0a01a8ae5758fb2ce84b6c887e34b46e349387` |

Paths and original package checks are in
[the package report](epl9-v3-package-validation.md). The reconstructed main in
the new concurrency test must match the frozen hash before tests start.

## Both-component verification and stock restoration

`scripts/epl9_component_readback.py` now compares **both main and OSD**, with
two separate acquisitions of each, against either frozen v3 or stock. The
required input layout is the full **decoded logical envelope**, 26214400 bytes
per component: header, decoded body and trailer. Encoded update files, body-only
images, raw NAND/OOB dumps and cached runtime images are different layouts.

Main's logical update destination is `406e0000`; the native selector receives
its `806e0000` alias. OSD's destination is `421e0000`. These are not physical
chip offsets or a prescription for acquiring memory. The reference envelopes
match the hashes recorded at the native writer boundary in the earlier audit.

The comparator reports byte identity, repeated-read stability, the recognized
state of each component, and mismatch extent. It rejects mixed states such as
new main/old OSD or old main/new OSD for either requested target. Therefore the
earlier updater error-masking case cannot pass just because its final status
is zero. Header/trailer corruption, truncated bodies, swapped components,
unstable repeats and encoded inputs are also rejected.

Six unit tests and **14 full-size controls** pass. Full-size controls are
synthetic local data derived from known packages. Their report explicitly
leaves acquisition provenance and physical write verification false. Passing
this comparator on copied package bytes proves no camera operation.

**Acquisition is the remaining gap.** The existing
[board-readout investigation](epl9-board-readout.md) found a maintenance
erase/program branch in the ordinary native read route. Its separate diagnostic
read route is not yet an externally reachable, qualified export. No such
command was sent in this pass. Updater mode 2 validates uploaded RAM, and the
unchanged version string cannot verify the installed components.

For stock return, success means both complete logical components match stock
after an attributable acquisition. The existing stock package covers exactly
the two changed components. Ability to invoke that package still depends on a
working update path; this work does not establish recovery after failure to
start the modified main. No new risk/recovery policy supersedes the separate
installation investigation.

## Distinct jobs and the same-job exclusion requirement

`scripts/epl9_v3_concurrency_probe.py` executes the frozen native color path
with two distinct request/context/output/cache/owner/stack sets and **one shared,
writable main image**. It pauses and alternates both executions at the temporary
request, post-native-call and restoration boundaries. Both recipe orders and
formats `200`, `100`, `40`, `1000` give **eight paired cases**.

Every case matches its independently executed, equivalently relocated fixture
over all 5200 configuration bytes. Complete request/context/owner/control bytes
are restored; adjacent guards survive; final gamma/tone pointers do not retain
temporary stack storage. The shared main bytes remain unchanged even though
the test permits writes to that mapping. This is stronger than merely mapping
the module read-only. It covers the executed configuration paths, not every
runtime writer, MMIO alias or DMA transfer.

Two deliberate same-context overlap controls show why caller exclusion matters:
while the outer call temporarily presents COLOR key 11, an inner call bypasses
the full film-bias/post-HSL path and its configuration differs from an isolated
run (693 differing configuration bytes for Gold, 703 for Portra). The gamma
hook executes in both controls; this is a partial, inconsistent path,
not evidence that every recipe operation is skipped. The outer call can still
restore its request, so restoration alone is not a concurrency guarantee.

This is **not an observed camera race**. The native bound-owner tests already
exclude synchronous processing reentry from the tested event 2/13/21 handlers
under their explicit state fixtures. They do not prove that another task or
interrupt can never use the same job. A scheduler, IRQ delivery, enabled
external logging and the full hardware lifecycle are not emulated here.
The specific remaining requirement is exclusive configuration of the same
job/request, not global exclusion between Gold and Portra jobs. No firmware
lock or interrupt-disable workaround was added.

## Stack correction

The former 392-byte prefix omitted two intermediate call frames. The identified
conditional task-31 branch has these native frame allocations:

| Fragment | Bytes |
| --- | ---: |
| Task entry `607ce1b5`: saved registers + local storage | 16 + 356 |
| `607ce31c -> 607ce3f3` | 20 |
| `607ce460 -> 607cf061` | 60 |
| `607cf0e0 -> 607ce5ae` | 28 |
| `607ce63f -> 6074e6eb` | 32, already included in the job probe |

Five byte-checked native fragments measure these changes directly. They are
explicit fragments, not a fabricated continuous task execution. The prefix
before the executor is **480**, so the frozen v3 observed job peak of 2248
gives **2728 bytes** for this scoped branch, against a task descriptor of
**14080 bytes**. The older 2268-byte probe would total **2748**, not 2660.
`epl9_lifecycle_probe.py` now calculates the prefix correctly. Historical JSON
evidence remains unchanged. This is not a whole-task/IRQ worst-case bound or
coverage of every other caller.

## Memory placement

The earlier native load checks establish module inclusion in the early load and
non-overlap with known later startup ranges. This pass additionally checks the
native pool classifiers at `604023b2`, `6040244e`, `604024ce` and the matching
seven ROM records at `60405f10..60405f80`.

Fourteen positive boundary controls select the expected pool IDs. **23040
native word-address checks** reject both module aliases (`604a1300..604a4f00`
and `a04a1300..a04a4f00`) across all three classifiers. The seven classified
pool intervals do not overlap the module after alias normalization. Execution
stops before the actual free/log/kernel calls. This excludes these pool ranges;
it does not prove the contents of runtime allocator metadata or rule out other
overlays, computed writes, DMA, or cache behavior. Pool-table stride arithmetic
is corroborating layout evidence, not a measurement of physical allocation.

## Retained evidence and remaining scope

- `local/epl9-v3-readback-controls-20261107/readback-controls.json`
- `local/epl9-v3-concurrency-final-20261107/concurrency.json`
- `local/epl9-v3-sync-memory-20261107/stack.json`
- `local/epl9-v3-sync-memory-20261107/pools-final.json`
- `local/epl9-v3-sync-memory-20261107/followup-manifest.json` pins the four
  reports and current scripts and rechecks both packages plus all five frozen
  recipe inputs. All seven frozen file identities match.

Offline byte comparison, separate-job isolation, the corrected scoped stack
calculation and exclusion of the seven classified pools are implemented and
checked. **Still open:** attributable component acquisition and an accessible
restore entry on this E-PL9; same-job exclusion on the selected runtime path;
runtime code-slot/cache preservation outside the tested paths. Actual TruePic
output/completion remains an objective of the first camera test. These reports
do not claim that all installation blockers have been closed.
