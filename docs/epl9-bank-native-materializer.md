# Bank-to-native-layout bridge (offline, not installed)

This follow-up to the 31-record bank model executes a reusable author-written
MN103 descriptor materializer. It does not change the frozen Gold/Portra build,
install Delete/SD hooks, assign ART keys, or claim that the 31 artistic recipes
have been ported.

## New result

The existing two-slot materializer used a logical-slot getter. The new isolated
entry takes a caller-owned validated E9R0 record and a 4096-byte destination,
so it can prepare any record of a bank without encoding a two-slot limit.
The same HSL/record/gamma descriptor layout is retained. Inputs are selected by
the host; no new camera event or allocation API is guessed.

The emitted module is 246 bytes / 86 decoded instructions. A qualified GNU
reader independently decoded those bytes. Execution of that listing for 31
synthetic records, using the exact E-PL9 build 1101 HSL template, matched the
independent host descriptor oracle byte for byte (4096 bytes per record).
Record validation and 1–31 iteration bounds are host preconditions, not checks
inside the emitted writer. Unit tests use assembler rows; the full CLI experiment
uses independently decoded GNU instructions.

Source records and ROM are read-only, destination guards and calling-convention
saved registers are checked. These are authored native-code tests, not traces
of a real camera executing our code.

A functional test connects the previous Delete controller to this conversion:
an outstanding capture lease retains its old immutable bank, the switch waits,
and new descriptors are prepared after release. Switching back reproduces the
old descriptor bytes. This proves only the single-owner host contract, not an
actual camera-wide capture drain or concurrency lock.

The returned byte snapshot contains absolute **synthetic** ARENA/RAW addresses.
The host returns a comparison artifact, not the record storage/Memory object.
It is therefore neither portable nor a lifetime-safe published arena for a
camera consumer; pointer relocation and retained backing ownership remain work.

## Memory implication

- Serialized 31-record bank: **20,484 bytes**.
- 31 expanded 4096-byte descriptors: **126,976 bytes**.
- Retaining both: **147,460 bytes**, excluding allocator/control/stack overhead.

The earlier 8192-byte two-slot descriptor allocation is insufficient for a
31-entry expansion. This is not evidence that an allocation of 126,976 bytes
will succeed on the camera. Possible next designs are a qualified larger arena
or bounded lazy materialization with stable per-capture ownership. Neither has
been connected to the physical allocator yet.

## Reproduce

Run from this branch's repository root:

```sh
python -m unittest discover -s scripts -p 'test_epl9_bank_materializer.py' -v
python -m unittest discover -s scripts -p 'test_epl9_recipe_banks.py' -v
python scripts/epl9_bank_materializer.py \
  --main local/private/main.bin \
  --reader local/mn103-tooling/mn103-reader \
  --out local/NEW-native-bank-proof
```

The full experiment requires the exact stock decoded main, SHA-256
`8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`,
and the repository's qualified GNU reader. The output directory must be new.
The original firmware is not distributed. Unit tests use a synthetic ROM table;
the full experiment uses the private exact ROM table and publishes only hashes
and scalar results. Generated descriptor contents remain private.

## Unresolved

The V6/Astra R3 cloud conversation was re-read. Its source archive still lives
in that task's workspace and is not available in this checkout through the
current supported transfer surface. There is no claim that prose descriptions
are numerical recipes. Mapping all ART modes, physical SD, Delete context,
cache/DMA lifetime, native publication and full teardown remain unqualified.
No hardware installation or image output was attempted. `install_ready=false`.
