# E-PL9: native-source executor reentry controls

## Result, 2026-11-11

The separate opt-in native-source variant does **not accumulate WB in these
bounded controls**. Re-entering the same native job does, however, repeat its
work callback. At an unfinished request's gain-return checkpoint, this
reconstructs the request and duplicates an output allocation. The suspended
original prefix then exhausts the declared host resources instead of reaching
its normal first TruePic boundary.

At the later submission and COLOR checkpoints, repeated work stops at the
same resource limit before reconstructing the request. The original prefix
can still resume to its first hardware boundary with byte-identical request
and configuration. This limited result is not general overlap safety.

These are deliberately adversarial **same-job overlap negative controls**,
not a camera scheduling observation, a measured race, hardware completion,
processed pixels or an installation qualification. The prior requirement to
exclude simultaneous access to the same job remains.

## Identities and scope

Olympus E-PL9, owner-reported body 1.1, downloaded internal build 1101. The
stock update is not an independently acquired dump of the installed camera.

- Stock decoded main: 26,214,336 bytes, SHA-256
  `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
- Separate native-source/private-COLOR decoded main: 26,214,336 bytes, SHA-256
  `2d003930675b47774e9ed3535ee49c64f56ff519bd6f1a33ddafd1a8c688b9b7`.
- Separate module: 15,360 bytes, SHA-256
  `89803a465ae76a81ae6b10055f0b8ff67dc30a1f162785bd8ee4f97e1c70d6e3`.
- Frozen main is independently reconstructed as
  `501707d09a0eb648e46196752b7ece17cd5368f6d54dbabce7c73e9806f65686`;
  existing private-COLOR main as
  `72cc1e48e6b42ab02b9911bdb841fe2c5b0cb34f2c08893f6b78be8a6871beee`.
- Every module byte from offset 4096 onward matches both older generations.
  No recipe table, existing candidate, OSD, encoded package or readback
  reference was changed.
- Exact existing RGB JSON input SHA-256:
  `915f5cfd5d89d78a01b36b386bcab4e874ffc664b7de8017c9f0f9cf92c6a1cb`.

The probe covers Gold and Portra with both native primary and primary-wrapper
parameter producers: four original jobs and twelve independent reentries.
Source fields are produced by the stock suffixes described in
`epl9-native-source-gates.md` and `epl9_classified_branch_probe.py`.
The declared source-side owner +280, bound callback owner +280, descriptor
+268 and request Sv are all 2560; descriptor +285 is the native-produced 6.
Native classification yields flags `[1,0,0]`, repeated classifier 1 and
companion stage 3. No classification result is forced. Physical ISO mapping,
source-address acquisition, the full owner-preparation chain and source
packing remain unverified.

## Snapshot and continuation contract

Let J be the 16 KiB job and R=J+10440 its 1876-byte request. Independent
pre-instruction snapshots are taken at:

1. `gain_return`, `60761ca4`, just after the relocated WB hook returns.
2. `submission`, `6074f11c`, before the first request submission body.
3. `COLOR`, `6079fb88`, before the private COLOR-copy prologue.

The historical `epl9_job_reentry_probe.py` is unchanged. It used a different
COLOR boundary, `film_color_original`, and stopped at `6074e765` before the
repeated callback. It did not execute the new variant's repeated work.

RAM and all software models are deep-copied **as one object graph**. Native
owner adapters retain aliases to the copied owner arrays, and resource
adapters retain shared copied event/consumer objects. Copying memory and
models independently would invalidate these bindings. The child is a fresh
`CallMachine`, not a deep copy of observer closures bound to the original.

The child enters `6074e6eb` with D0=J, D1=native entry count 2, mask `f0` and
frame 32. Its explicitly declared synthetic caller SP is `10012000`, below
the suspended original's live stack. The live original stack bytes are
verified unchanged. This is a host caller provision, not evidence of spare
camera task stack or an actual second task.

After each reentry stops, paired continuations resume the exact saved native
PC, registers, flags and loop state on (a) an untouched copy and (b) the
reentry-modified copy. Neither continuation supplies a successful hardware
return. Original RAM/model hashes remain identical before and after every
reentry and both continuations. The actual outer experiment proceeds
independently and retains its expected result.

## Exact repeated-work results

All twelve reentries execute the native indirect call at `6074e765`, selecting
work callback `60751319`, then stop at the existing finite owner contract:

- requester `6074a8bb -> 6073eab3`, owner event 19;
- dispatch instruction `6073eac3`, return would be `6074a8c2`;
- exact error: `owner buffer request exceeds declared fixture capacity`.

The declared capacity is seven non-overlapping host arenas, not camera RAM
or a successful native hardware allocator. It is never enlarged to force a
reentry through. All native cursor/count/error/cancelled values remain
`1/2/0/0`. The pending record is unchanged, including its live nonzero state
at COLOR.

### Gain-return overlap

The snapshot already has one output allocation, id `1000` at `20000000`.
Repeated work allocates another id `1000` at `23000000`, then ids
`7,8,10,11,12` in the remaining five arenas. Its next request cannot be
satisfied by the finite fixture.

The native constructor reinitializes R and copies the unchanged source gains
`[1024,1024,1024,1024]` before the new C9E hook executes once. Resulting gains
are again Gold `[1106,901,1024,1024]` or Portra `[1060,963,1024,1024]`.
They are not the result of multiplying the already adjusted request again.
Source gains stay unchanged throughout.

Although those gains and the admitted source/kind/selector fields are equal,
the complete request is not unchanged. Native descriptor-copy stores at
`60761d8d` populate R+276's unfinished output descriptor. The changed bytes
are R+279, +284..285, +287 and +289..291, seven bytes total. They encode
output pointer `16000000`, format `0302`, and `4608 x 3456` dimensions in
fields which were still zero at this early checkpoint. This is native
reconstruction/advance of an unfinished object, not an unexplained random
write. Job buffer and temporary-descriptor state changes are retained in full
in the local report.

The no-overlap continuation reaches the exact first TruePic stop. Resuming
the original native state after overlap instead fails at the owner capacity
contract, before its first submission. Compared with the no-overlap
continuation, the request differs in twelve byte spans, across R+4..7,
+1199..1211, +1216..1251, +1255, +1260..1267, +1311,
+1316..1317, +1319..1323, +1367, +1372..1379 and +1640..1642
(the first range contains two separated spans). Later descriptor/pending
configuration is unfinished. These different stop points do not establish
that each differing byte was individually corrupted. They demonstrate that
this overlap disrupts the original prefix under the declared finite resource
contract. The native cache also remains incompletely configured relative to
the no-overlap hardware prefix.

### Submission and COLOR overlap

These snapshots already have all seven arenas allocated. Repeated work
initializes the **next unused** native buffer-table row and fails on its
first event-19 allocation. It does not reach the constructor or gain hook,
write any request byte, allocate another payload, or change resource
accounting.

Its only changed job spans are J+6292..6293, +6295, +6297..6299,
+6301..6303, +6309..6311, +6358..6359 and +6361: 15 bytes in the unused
88-byte row beginning at J+6284. No existing live allocation is described as
corrupted by these writes.

Both paired continuations reach the exact same first TruePic stop. All 1876
request bytes and 5764 native cache/configuration bytes are identical at that
boundary. The gains and recipe's three RGB pointers match. Reentry did not
progress far enough to qualify repeated reconstruction or later submissions
at these checkpoints, so this result cannot justify a whole-job lock claim.

## Safety observations and validation

All original jobs and baseline continuations stop at native `6073eafa`,
attempting to write `800` to unmapped TruePic register `9880014c`. Later
submission/COLOR overlap continuations stop there too. Nothing models that
write as success or executes a completed hardware cycle.

Across original runs, reentries and paired continuations:

- Output and allocated payload poison remains untouched, and guards remain
  intact.
- Source-pixel instruction reads and completion signals are zero.
- No camera access, installation, package publication, menu change or
  firmware container generation occurs.

The probe rejects unexpected errors/callsites, missing snapshots, changed
source/gains, absent fresh gain copies, altered pending state, lost aliases,
stack overlap, changed parent state, wrong gamma or hardware-write value,
and any pixel/completion evidence. Twenty firmware-independent unit tests
exercise these controls, shared-clone aliases, isolated model state and
complete byte-difference reporting.

Reproduce with assertions enabled:

```sh
python -m unittest discover -s scripts -p test_epl9_native_source_reentry_probe.py -v
python scripts/epl9_native_source_reentry_probe.py \
  --rgb-tables local/cloud-private-reconstructed-v3-20261110/native-rgb-tables.json \
  --out local/new-native-source-reentry-run
```

Qualified output is
`local/cloud-reentry-native-source-20261111/run-v5/native-source-reentry.json`.
Earlier preparation runs are diagnostic only; v5 includes the corrected
bound owner Sv and exact stop/continuation validators and byte-level regression checks. Source and reader
hashes, native listings, every changed byte span, request writes and resource
states are retained there. These local artifacts and decoded firmware remain
ignored. `install_ready` remains false.
