# E-PL9 SD loader: owned session state and two test slots

The [2026-11-10 processing follow-up](epl9-sd-processing-prototype.md) connects
these selected records to native image configuration in a separate module.
This earlier state generation and its bytes remain unchanged.

2026-11-07. The owner's next authorized offline step is implemented separately
from both Watercolor v3 generations: extend the HLS_EVENT singleton's owned
allocation and bind two independent test aliases to fixed recipe files. A
missing file keeps that slot's embedded record. This builds on the
[standalone loader](epl9-sd-loader-prototype.md), whose source and 1322-byte
output remain unchanged.

The new module is **6144 bytes**, including **1877 bytes / 465 instructions**
of code and two local fallback records. Its SHA-256 is
`6cd7311db65d3e7b4d6773095c93c13b5cacf2d94852d191f5e25de78293dda4`.
`0x69000000` remains a **synthetic module address**. Three instruction changes
execute only in an offline RAM copy; no firmware package, card preparation,
camera command or physical write was made. The original firmware files are
unchanged. This is not an installed or hardware-qualified loader.

## Where the state lives

The stock lazy getter at `0x60ae1a4d` uses singleton root **`0x6239790c`**. It
checks that root, acquires lock 2, checks again, allocates **180 bytes**, calls
constructor `0x60ae187f`, publishes the pointer at `0x60ae1a8f`, then unlocks.
The constructor initializes the original object, including five vectors,
task-ID halfword `+172 = -1` and word `+176 = 0`.

The separate variant increases the allocation request to **288 bytes** and
initializes the new tail after the native constructor, before the existing
root store. Both 180 and 288 follow native ordinary allocator
`0x60402373` into **pool `0x10002`, block size 2048**. No guessed free BSS
address or E-P7 state address is used. The returned manager pointer determines
the tail address; `0x62267000` is only the finite pool fixture used by the probe.

| Manager-relative bytes | Use |
| --- | --- |
| 0–179 | Original native object; byte-identical in the constructor comparison |
| 180–191 | Newly owned zero padding |
| 192–195 | `EDS1` magic `0x31534445`, written last |
| 196–199 | Layout version 1 / slot count 2 (`0x00010002`) |
| 200–203 | Manager self pointer |
| 204–207 | Allocation request extent, 288 |
| 208–211 | Session load busy flag |
| 212–215 | Reserved zero |
| 216–247 | T1's independent 32-byte loader context |
| 248–279 | T2's independent 32-byte loader context |
| 280–287 | Newly owned zero padding |

The registry helper requires a nonnull manager equal to the current singleton,
matching magic, version/count, self pointer and extent. The slot accessor
returns its module-owned embedded record if the root is absent or the header
does not match. Unknown logical slot IDs return null. The accessor's native
ABI is `D0=1/2`, result `A0=packed record`, CALL mask `0xf0`, frame **24**.
The extra space below the four saved registers is required by its nested
registry call.

This is persistent **RAM state for an initialized session**, not nonvolatile
state across power-off. The native getter's fast path preserves it on later
calls. The variant requires allocation at its first cold-start getter: it
must not be attached to an already existing 180-byte object. A header read
cannot make that live extension safe.

The raw encoded-CALL scan finds one constructor candidate (`0x60ae1a8a`) and
65 getter candidates. The manager has a native destructor; no root-clear
operation was established in these traced paths. These observations support
the singleton design but do not establish every indirect call, shutdown or
restart path. Module loading before construction and safe retained-buffer
teardown still need qualification.

## Test-slot binding and fallback

| Alias / logical ID | Fixed native path | Context | Embedded test default |
| --- | --- | --- | --- |
| T1 / 1 | `C:\EPL9MOD\SLOT01.RCP` | manager +216 | Existing local Gold example record |
| T2 / 2 | `C:\EPL9MOD\SLOT02.RCP` | manager +248 | Existing local Portra example record |

These are test aliases, not assigned ART/menu modes or a final library split.
Using the existing example records makes the local experiment reproducible;
it neither changes the v3 tables nor selects the owner's eventual fallback
library. The 29 planned recipes remain a planning pool.

Each context retains the earlier loader's 32-byte ABI: state, selected record,
embedded record, owned block, path, mode, error and reserved word. Only state
3 exposes the SD pointer. In addition, selected and owned pointers must agree,
be four-byte aligned and fall within the native 2 KiB pool range. These are
consistency checks on this producer's output, not independent proof of
arbitrary pointer ownership.

The offline event overlay replaces the five-byte CALL at `0x60ae1c6e` with
a JMP to an inline trampoline. That trampoline calls the new adapter and
returns to **`0x60ae1c73`**. The adapter first executes original event getter
`0x60ae2073`, saves its volatile outputs, checks the declared eligible event
and registry, sets a session busy flag and invokes the unchanged loader for
T1 then T2. Normal completion clears the flag and restores original outputs.

The loader retains all earlier readiness gates: event `0x02000100`, CPU 0,
completed section flags, native current task matching manager `+172`, and
SD-specific status `0x6239914c == 0xf000`. Native task-creation adapter
`0x60ae1bb2` sets `+172` from the declared kernel result in this probe. Before
that binding, and while SD is not ready, both slots stay waiting with no file
operations; a later eligible call can retry. Physical event normalization and
mount/service timing remain unverified.

| Condition | Result for that slot |
| --- | --- |
| Missing file | State 2, free temporary block, embedded record |
| Corrupt/incompatible/incorrect-length file | Reject entire file, embedded record |
| Valid 660-byte record | State 3, retain owned block, selected SD record |
| Close uncertainty | State 4, retain file/buffer ownership, embedded record; the other slot can proceed |
| Pending file RPC | State 1, retain file/request/buffer; session busy stays set and the second slot remains embedded |

Completed attempts do not reload during the session, including after a
previously missing file appears. The intended authoring workflow is to export
the [existing recipe JSON format](epl9-sd-slot-study.md#experimental-file-format)
to the fixed slot filename, then start a newly initialized session. No source
edit or firmware rebuild is required to change an accepted SD record in this
design. Actual camera mounting and restart behavior are still untested.
There is no live-reload command in this prototype.

## Native offline evidence

Retained report:
`local/epl9-sd-state-probe-20261107-final-v2/validation.json`.
Reproducible source discovery:
`local/epl9-sd-state-discovery-20261107-final/discovery.json`.
Both are ignored local evidence, as are the native listings and fallback data.

- **36 SD tests pass**, including eight new state/slot tests. The original
  standalone loader remains 1322 bytes with SHA-256
  `ed4d4e9055d00393ad1eea267bd265abf4261c3a12fd1980cac7ad216f15d357`.
- GNU independently decodes all 465 new module instructions and the three
  changed stock instructions. Exact stock bytes are required at every change.
- The native singleton getter, base/manager constructor, owner attachment,
  vector reservation and ordinary allocation/free classifiers execute. Both
  variants have identical original 180-byte prefixes and untouched guards;
  the new header and both contexts exist before root publication under lock.
- Native task-create adapter allocates its 16360-byte stack, obtains task ID
  54 from the kernel fixture and starts that task through the declared front.
  The state tail survives unchanged. Repeated singleton getters neither
  allocate another manager nor reset completed slot state.
- **Eight two-slot cases pass:** both missing, both valid, either one missing,
  first corrupt, SD initially not ready, first close uncertain and first read
  pending. The valid files deliberately exchange the two example records:
  filename/slot binding, rather than recipe identity, determines selection.
  The not-ready case later reaches `[3,3]`; pending remains `[1,0]` with live
  resources. Manager allocation failure keeps a null root and usable defaults.
- All seven normally returning case paths preserve the original nine general/SP
  register outputs and 28 live caller-frame bytes. The caller's first four
  bytes are the dead CALL return slot: the inline trampoline necessarily
  writes its own return address there. They are explicitly excluded, rather
  than claiming the complete 32-byte frame is identical. The traced
  continuation performs its own compare and calls before using PSW/MDR;
  those registers are not compared.
- A deliberately recursive event during file RPC performs no second file
  operation while session busy is set. This is a scoped same-task reentry
  control, not an atomic inter-core/IRQ lock proof.
- **13 protected inputs remain identical**, including frozen main/OSD, old
  encoded candidate/restoration, new private-COLOR main/package, original
  loader and all existing recipe inputs. Both v3 generations remain separate.

Finite models provide pool backing, lock operations, a borrowed default-owner
lookup, kernel task creation/start, delivered event, file-service RPC replies
and storage metadata. Constructor/base/attachment/vector code, pool
classification, get-task-ID, public file wrappers, CRC/range validation and
the logical read backend execute natively on byte-checked listings. These
are software/control-flow checks, not full RTOS execution or physical SD I/O.

## Sources and reproduction

Olympus E-PL9 / IM008 / model 1330. Displayed body version **1.1** is the
owner's report; downloaded main build **1101** is not a dump of the installed
camera. Exact stock package: **104552480 bytes**, SHA-256
`aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`.
Decoded main: **26214336 bytes**, SHA-256
`8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
The GNU reader SHA-256 is
`e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae`.
Instruction encoding uses the same pinned primary GNU opcode source as the
[preceding loader](epl9-sd-loader-prototype.md).

The [source audit](../scripts/epl9_sd_state_audit.py) regenerates 14 exact
native windows and records protected identities. The
[builder](../scripts/epl9_sd_state.py),
[native source](../firmware_src/epl9_sd_state.s.in),
[probe](../scripts/epl9_sd_state_probe.py) and
[tests](../scripts/test_epl9_sd_state.py) are separate from the v3 builders.
All output paths must be new and within ignored `local/`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_epl9_sd_*.py
.\.venv\Scripts\python.exe scripts/epl9_sd_state_audit.py --out local/new-sd-state-discovery
.\.venv\Scripts\python.exe scripts/epl9_sd_state_probe.py --discovery local/new-sd-state-discovery --read-listings local/wifi-limits-20261102-v6 --out local/new-sd-state-probe
```

The probe reuses earlier retained trigger/file/backend listings, rechecking
their bytes against this exact main. It briefly writes a RAM-overlay file
only for GNU decoding, then removes it; the retained binary is the separate
synthetic-address module. A module load address/boot mechanism, complete
object/RTOS/cache lifetime, teardown/cancellation, real mount/removal timing,
RAM-backed film descriptor consumer, UI labels and actual image processing
remain integration work. T1/T2 binding does not allocate native menu entries.
None of this changes the separate Watercolor v3 first-test candidate.
