# E-PL9: native updater, persistent logical flash and readback

## Scope and result, 2026-11-12

This is a connected **offline software experiment**, not camera installation.
The exact `native-source-v1` package is passed through real E-PL9 updater
instructions, into persistent logical component files, then read back from
reopened files. A separate OM-Emu consumer may launch the resulting bytes for
UI comparison. No camera, SD preparation, USB command, physical program/erase,
factory reset or firmware-feature addition occurs. Recipes and the accepted
ART-only firmware pair remain unchanged.

The first complete source-frozen suite is
`local/epl9-virtual-install-20261112/run-v4/summary.json`.
It has thirteen full-size scenarios, including successful candidate installation,
stock return, media errors, corrupted inputs and modeled interruptions. The
new storage/adapters have 32 synthetic tests. Ten full-state comparisons check
the additional accelerated native readback-checksum loop.

The decisive result is narrower than physical safety: complete virtual writes
produce the exact intended main and OSD, including their envelopes, after
close/reopen. Several deliberately failed writes still receive native final
return 0; independent stored-byte verification prevents their classification
as successful virtual installations.

## Exact private inputs

Model: Olympus PEN E-PL9 / IM008, model bytes 1330. Downloaded main build 1101;
owner-reported displayed body version 1.1 is not acquired from a device here.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| Native-source candidate | 52428800 | `10ac83e9beb9dd1bfd12aa6a021135706875d6ea245e58e20ec07fb917229421` |
| Stock main+OSD return | 52428800 | `10a7b949d1509ce627cb3c098c0a01a8ae5758fb2ce84b6c887e34b46e349387` |

Each contains only main 0100 followed by OSD 0101. Each decoded envelope has
26214400 bytes: header 32, payload 26214336, trailer 32. The source stock input
is an official update, **not a full flash acquisition from a camera**. Neither
the return file nor this logical store contains BOOT, device-specific calibration,
all settings, spare bytes, ECC metadata or an authenticated bad-block table.

## What executes, and what is modeled

The existing byte-checked GNU decoder and bounded MN103 interpreter execute:

- updater `6100440a` and its validation, decoding and component selection;
- write selector `604a0f8b`, including its native result-handling behavior;
- program/readback wrapper `6043a0d9`;
- the wrapper's real checksum and conditional return instructions.

Every loaded instruction is checked against the executing image. Candidate
installation executes the stock main. Stock return executes main extracted
from the exact corrected candidate, with all loaded updater instructions
confirmed unchanged. Entry at `6100440a` and a valid caller stack are provided
explicitly. This is not a reset replay or a demonstration of physical OK/power.

Only the storage leaves are replaced:

- `60439f38`: requests a whole decoded component be programmed into the logical
  store. The model erases blocks then programs pages, checkpoints persistent
  files, closes and reopens them before returning the explicit result.
- `604014c6`: reads the actual reopened component into the native caller's
  buffer. It does not substitute expected package bytes. The native wrapper
  then performs its own checksum.

Diagnostics and progress/error notification calls use explicit suppressed
models. USB/SD transfer, filesystem selection and external update entry are
not supplied. Unknown calls/instructions or unmapped accesses stop instead of
implicitly returning success.

The three existing decode/checksum loops retain their guarded accelerations.
The additional loop `6043a110..6043a116` sums stored readback words into d3;
its final iteration executes natively. Ten small intact/damaged controls compare
all registers, flags, loop state and RAM with unaccelerated execution. These
controls establish agreement with this interpreter, not independent proof of
all CPU or hardware behavior.

## Persistent storage contract

`epl9_virtual_flash.py` owns logical main `406e0000` (alias `806e0000`) and OSD
`421e0000`. It uses private `flash/main.flash.bin`, `flash/osd.flash.bin` and
`flash/manifest.json` files. Their contents are decoded envelopes, not encoded
update files or physical NAND dumps.

The chosen model uses 2048-byte pages and 131072-byte erase blocks. Those sizes
have code-analysis precedents, but **the geometry and this erase/program ordering
are explicit logical assumptions**, not an identified memory part or reproduced
controller. The physical program leaf itself is still modeled. Programming
rejects out-of-range writes and 0-to-1 changes without erase. Component sizes,
manifest checksum and actual file hashes are checked on reopen.

Component/fault/close checkpoints flush and fsync the files, then atomically
replace the manifest. There is no fsync per page. Simulated power loss is a
controlled persisted cut point. Real host-crash atomicity is not simulated; an
inconsistent data/manifest pair is rejected on reopen rather than repaired.
Verification reopens use `close(checkpoint=False)`: they must not rewrite cached
RAM over a persisted file before inspecting it. A regression corrupts a file
after a completed checkpoint and confirms that the corruption remains present
and reopening rejects it. Checksums detect inconsistency, not malicious
coordinated rewriting.

## Scenarios and observed distinction

| Scenario | Native final outcome | Independent persisted result |
| --- | --- | --- |
| Install candidate from stock | 0 | Exact candidate main+OSD; verified virtual-only |
| Restore stock from persisted candidate | 0 | Exact stock main+OSD; verified virtual-only |
| OSD erase error | 0 | Main candidate, OSD not target; rejected |
| OSD program error at page 17 | 0 | Incomplete OSD, main candidate; rejected |
| Main program error at page 200 | 0 | OSD candidate, incomplete main; rejected |
| Persisted main corruption after program | 0 | Native readback sees altered bytes; independent comparison rejects |
| Main readback reports error | 0 | Stored target bytes happen to match, but readback failed; not qualified |
| Power loss during OSD page 17, after 512 bytes | No native return | Partial persisted state; main not programmed |
| Power loss during main page 200, after 512 bytes | No native return | OSD completed, main partial |
| Stock return after that modeled main interruption | 0 | Exact stock main+OSD, only after synthetic intact-updater entry |
| Corrupted main input | 3211 | No program request; original store retained |
| Corrupted OSD input | 3211 | No program request; original store retained |
| Check-only mode 2 | 0 | No program request; original store retained; not an installation |

The lower selector's unconditional result clear is now exercised around real
program/readback-wrapper code. Therefore both a corrupted persisted main and
program/readback errors can coexist with outer native return 0. The model does
not fix or alter that firmware behavior. Its own qualification requires exact
persisted target bytes, normal native return, both program/readback operations
and no injected storage failure. A favorable message alone is insufficient.

For stock return, initial bytes are copied from the **actual persisted successful
candidate snapshot**, and its manifest identity is recorded. The recovery-after-
interruption control also starts from actual persisted interrupted bytes. Its
executing main is nevertheless supplied intact in model RAM: it cannot establish
that a real camera could boot those damaged flash bytes or reach recovery.

## Evidence handoff to the UI consumer

Each scenario's `result-components.json` binds:

- actual file paths, full envelope/payload hashes and exact target comparison;
- source-package identity;
- the native execution report and persistent manifest hashes;
- generation, target, virtual verification and explicit physical/reset flags.

Each `native-updater.json` records program/readback calls and their actual bytes,
results, persistent reopen events and native control-flow events. Its
`execution_provenance` captures the reader and nine source/dependency hashes
before execution, and requires them unchanged afterward and between all scenarios in the suite. Native instruction
bytes have a separate identity hash. Fault/schematic-only manifests are not
valid UI installation inputs.

The UI bridge must reopen and validate these files and launch their payloads,
not rebuild the candidate from an old overlay. A fresh OM-Emu launch can show
that the **software-written logical result** still navigates correctly and
returns to stock after virtual restoration. OM-Emu remains a kernel/UI harness
with explicit device stand-ins. It does not start at the physical reset vector
and does not prove sensor/TruePic processing, actual flash behavior or physical
recovery. See the separately bound UI evidence when that stage is complete.

## Reproduction

Requires the existing private exact package pair, decoded stock main and qualified
local GNU reader. Source-only tests do not need camera access or firmware inputs.

```sh
python -B -m unittest discover -s scripts -p 'test_epl9_virtual*.py' -v
python -B scripts/epl9_virtual_install.py --out local/NEW-virtual-install
```

Use a new ignored output directory. Full-suite files contain vendor-derived
component bytes and must stay private and Git-ignored. Publishable project source
and this report contain no manufacturer BIN, decoded component or dump.

## Remaining limits

No BOOT dump, independent recovery entry or complete hardware reset chain has
been obtained. The logical store does not model actual ECC, wear, bad blocks,
controller timing, buses, power rails, asynchronous DMA/cache behavior or every
RTOS/IRQ interaction. Neither virtual success nor a subsequent menu screenshot
changes `install_ready=false`. Hardware actions remain outside this phase.
