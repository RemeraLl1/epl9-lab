# E-PL9: offline installation and stock-restoration assessment

Follow-up on 2026-11-04: [same version, changed size and patch-risk findings](#same-version-changed-size-and-the-meaning-of-a-small-patch--2026-11-04).

## Result, 2026-11-04

Follow-up: [early main and SD-recovery dependencies](epl9-early-boot-recovery.md)
maps startup, the native section reader and ordinary firmware-service activation.
[OK/power input and task construction](epl9-ok-power-entry.md) extends that trace
and corrects a reply-queue/task-ID ambiguity.
[Olympus/OM incident review](olympus-om-update-incidents.md) separates external
failures, recoveries and model-specific limits. Neither closes the physical
OK/power-to-SD entry gap or authorizes installation.

**Stock restoration is technically plausible if the E-PL9 can still enter its
updater. Recovery after an arbitrary failed mod or interrupted write is not
established.** The updater client, service, validator and write wrappers were
located in this exact E-PL9 image and selected original instructions executed
with small RAM-only fixtures. This is new E-PL9 evidence; PEN-F/E-P7 behavior is
not substituted for it.

The selected native path accepts a main component carrying build 1101, without
requiring an increased version in these fixtures. It validates every included
fixture before requesting writes. Two important qualifications emerged:

- Duplicate main components are accepted in the tested case; the last one's
  pointer is used for the single write request. The host must reject duplicates.
- Some lower program/readback errors disappear at an outer write wrapper. A
  successful outer return is insufficient evidence of a correct physical write.

No camera, USB interface, SD device or network was accessed. No update image,
modified firmware or ready-to-install restore BIN was created. Original firmware
and other chats' ART/video/Wi-Fi implementations were preserved.

## Exact inputs and provenance

Olympus PEN **E-PL9**, model bytes **1330**. Displayed body version **1.1** is the
owner's report. Downloaded main build **1101** is identified from the package;
the installed camera's bytes have not been dumped.

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| `OLY_E_133_1101_0000_0000.BIN` | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Decoded main `00_0100_406e0020.decoded.bin` | 26214336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |

The candidate analysis mapping is `0x60400020`; flash/container addresses below
belong to other address domains. All five stock components were freshly decoded
and their model, full 28-byte header/trailer agreement and additive checksums
checked by the new host inspector:

| Kind | Header build | Container destination | Complete component bytes |
| --- | --- | --- | ---: |
| `0100` main | `1101` | `406e0000` | 26214400 |
| `0101` OSD | `0100` | `421e0000` | 26214400 |
| `0106` | `0100` | `43ae0000` | 38797312 |
| `010e` | `0001` | `40002800` | 219168 |
| `0102` pictures | `0100` | `468e0000` | 13107200 |

Per-component decoded hashes are in the private report. The downloaded package
is a software-update input, not a complete physical-flash backup or a backup of
this body's calibration, settings, serial data or an independently identified
early boot image. In particular, kind `010e` must not be relabeled a rescue boot
ROM merely because its destination begins with `4000`.

Reference checkout: [fishcu/oly_fw_analysis](https://github.com/fishcu/oly_fw_analysis/tree/539fcf1fa9eda5fdef8ede4deeab94a4691d94c3),
commit `539fcf1fa9eda5fdef8ede4deeab94a4691d94c3`. Its container specification and
PEN-F updater work guided searches. No upstream source was copied into this
project. The GNU reader is pinned to SHA-256
`e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae`;
see [tool provenance](mn103-tooling.md). The new runner also hashes its own source
and the imported execution helpers.

## E-PL9 paths actually found

| Address | Exact-image observation |
| --- | --- |
| `610039fd` | SD firmware client; descriptor at `60419680` contains task ID 89, priority 45, stack 2048 |
| `61003e85` | Firmware service; descriptor at `60418ebc` contains task ID 18, priority 55, stack 2048 |
| `61003f75` | Service calls shared updater `6100440a` with mode 0 |
| `6100432d` / `6100436e` | Service calls the same shared updater for USB check / commit |
| `6100440a` | Shared component enumeration, validation, selection and write dispatch |
| `610050c3` | Descrambling/validation front |
| `6100395e` / `61003869` | Native descrambler and checksum/header validation |
| `6100511c` | Component-write wrapper |
| `604a0f8b` | Storage-operation selector; normal user update reaches mode 1 |
| `6043a0d9` | Program wrapper with readback/checksum path |

The SD client's table references `S133????BIN` and `E133????BIN`; its directory
argument is the FAT-style padded `DCOLYMP    `. These are real E-PL9 selection
strings. The historically reported `E1339999.BIN` name is consistent with the
pattern. The suffix is not the internal build number, and an appropriate filename
does not establish valid contents or reliable recovery.

The service modes are independently exercised at the shared entry:

- **0:** decode/check, then request writes for the selected components.
- **2:** decode/check only, with zero backend requests in the fixture.
- **1:** commit the buffer already decoded by mode 2. It is not a standalone
  substitute for validation.

The SD client's filesystem, mounting, loading, RTOS message exchange and physical
power-on selection have been inspected only in bounded static windows. They are
not executed end to end by this audit. The number 89 loaded at `60f59c94` was
initially interpreted as a task ID; the linked follow-up establishes that this
argument is a reply queue. It provides no task-89 activation or OK-button selector.

USB-side application routine `6105c1a8` logs `startFirmUp` and performs indirect
application dispatch. This is not a demonstrated USB-ROM rescue entry, and no
vendor operation was sent. The official client's willingness to download or
reinstall version 1.1 remains a different question from the camera-side routine's
fixture acceptance.

## Same version, changed size and the meaning of a small patch — 2026-11-04

**A displayed version/build is metadata, not a byte identity or a safety
certificate.** The reviewed main updater accepts structurally valid synthetic
components with build 1101 and changed lengths/content. It does not compare
them with the stock file's SHA-256. This is a statement about the tested
main-resident validation path, not an unexamined ROM loader, the official host
client or actual flash acceptance.

Inputs are the same E-PL9 / model 1330 / IM008 package and decoded main pinned
above: owner-reported displayed 1.1, downloaded main build 1101, stock package
104552480 bytes, decoded main 26214336 bytes. No modified firmware container
was saved and no camera was accessed in this follow-up.

### New RAM-only size/version controls

`local/epl9-memdump-entry-size-20261104/size_version_probe.py` reuses the
byte-checked saved validator listings against the exact main and records its
source/helper hashes. Its synthetic components are nonfunctional patterns
created only in host RAM. Every request to flash is trapped before execution.

| Native control | Observed scope/result |
| --- | --- |
| Same build `1101`; payloads 16/256/512/1024/4096 bytes | All return 0 and request the actual component length: payload + 64-byte envelope |
| Main build fields `1000`, `1101`, `9900` with consistent checksums | All return 0 in this path; no same/newer-build-only constraint was observed in these cases |
| Changed encoded payload byte, stale checksum | `3211`, no backend request |
| Main kind with factory, shifted or another component's destination field | The reviewed validator forwards those fields, subject to its address-domain translation; this is not a whitelist of safe main destinations |

These are **12** small native cases. They do not validate a runnable enlarged
main, a downgrade procedure or the physical acceptability of a shifted address.
In particular, updating the checksum does not turn a synthetic/random body
into bootable firmware.

Four separate native runs enter only the outer write selector `604a0f8b`,
with lengths **26214400**, **26214416**, **28311552**, **28311568**. Each reaches
the program/readback-wrapper call at `604a10c2` with that length unchanged.
Execution stops **before** `6043a0d9`; no source bytes, flash reads, erases or
program operations occur. This selector does not impose the original main
component's length in those cases. It is not a test of the lower writer's
maximum size, physical storage capacity, partition protection or power-loss
behavior. The numerical spans do not identify available free space.

### Three different sizes must not be confused

1. **Whole update-package size.** The stock 104552480-byte file concatenates
   five components. A deliberately component-selective package could have a
   different total size even if the main's size remains unchanged. The small
   native fixtures support component selection; a real install is untested.
2. **Component envelope and payload size.** The stock main component is
   26214400 bytes, including its 64-byte envelope. Its payload is 26214336.
   Lengths, alignment, component boundaries, matching header/trailer and
   additive checksums must be consistent. Appending bytes to the outside of
   an unchanged envelope is not a supported method of adding tables.
3. **Runtime storage/RAM/executable mapping.** An accepted container length
   does not establish where appended bytes are loaded, copied, executed or
   retained. Native section sizes, address references, placement, stack,
   buffers and adjacent/service regions still need independent qualification.

Inserting bytes in the middle of executable/data regions can shift existing
addresses and break references. Appending code can leave it outside the loaded
sections even when container checks pass. Extending the write extent can also
touch space whose ownership has not been established. Another component's
starting address or a run of padding bytes does not prove that a gap is free.

The lower-risk engineering direction is to preserve validated layouts and use
only space independently established as available. Replacing same-shaped HSL
tables or icon payloads that fit their existing allocations may preserve all
component/file sizes. Added native code still requires a qualified placement;
the film module's synthetic offline base is not one. Increasing a version
number does not supply that placement or protection.

### What the patch's byte fraction says about risk

The final installable film patch does not exist, so a 20% changed-byte figure
has not been measured. For scale, two 3028-byte HSL tables total **6056 bytes**,
about **0.023%** of the stock decoded main, before code/icons/other data. This
is an illustration, not the final module/patch size or probability of success.

The accepted replacement changes ART routing/parameter preparation as well as
look data. An incorrect branch, pointer, stack convention or object lifetime
can stop main even if only a few bytes differ. Conversely, a much larger
verified data replacement can have a narrow functional effect. The actual
diff and the role of its changed regions matter more than a global percentage.

| Failure class | Relationship to a small patch |
| --- | --- |
| File rejected before writing | Format/model/checksum/host checks can reject it; this is different from a bricked main |
| Interrupted or incorrect physical programming | Main installation requests the complete selected component, not only changed bytes; small edits do not proportionally reduce this write exposure |
| Programming completes, patched code/data fails at runtime | A few critical bytes can cause bootloop, assert, memory corruption or capture failure |
| Recovery from the resulting state | Depends on surviving and reachable recovery code plus intact device-specific data, not the displayed 1.1 label |

Main's stock component length is arithmetically **200 x 131072-byte units**;
actual erase/program behavior still needs hardware qualification. A full
five-component package must not be treated as a byte-diff install merely
because only main was edited.

There is no defensible numerical probability of bricking for this project:
no physical modified E-PL9 install/restore trials or representative failure
statistics were obtained. Passing offline configurations reduces specific
software uncertainties but does not measure a field failure rate. Keeping
version 1.1, making a small diff, or seeing successful validation cannot by
itself qualify installation on the owner's only body. A failed main need
not mean damaged silicon, but practical restoration is still unproved.

The complementary [USB shell/memory-read follow-up](epl9-board-readout.md)
maps a conditional export route, not an independent pre-main rescue loader.
No experiment intended to hang/corrupt main or interrupt an update is
authorized or performed.

## Native checks and their limits

[epl9_recovery_audit.py](../scripts/epl9_recovery_audit.py) executes the exact
instructions with the existing opt-in call engine. Main ROM is read-only; stack,
result and package RAM are explicit bounded fixtures. Unknown instructions,
memory and undeclared calls stop the run. Diagnostic and progress output are
explicit models. Each flash request is trapped before storage access; its
arguments and decoded-data hash are recorded.

| RAM-only experiment | Observed result |
| --- | --- |
| Main build `1101`, mode 0 | Return 0; one request to `806e0000` |
| OSD build `0100`, mode 0 | Return 0; one request |
| Main + OSD, mode 0 | Return 0; two requests |
| Mode 2, then mode 1 on its decoded bytes | First zero requests; then one request |
| Corrupt first checksum | `3211`, zero requests |
| Valid first component + corrupt later checksum | `3211`, zero requests; no earlier partial write request |
| Wrong model, with otherwise consistent fixture checksum | `3202`, zero requests |
| Duplicate main | Return 0; one request using the **second** component |
| Explicit backend failure `3105` at shared-updater boundary | Error propagated by the shared updater |
| Selected ART worklist/COLOR code and shared table inaccessible | Updater fixture still completes after explicit updater entry |

The component payloads are 256-byte nonfunctional patterns. Their headers carry
the selected E-PL9 identity/build, but they are not a byte-identical factory
restore, a bootable application, or a camera-ready patch. The entire 104552480-byte
stock package was host-validated; it was not executed through all native
descrambling/checksum loops in this bounded run. Full-size allocations, transfer,
asynchronous scheduling and actual flash acceptance remain unqualified.

The isolation case removes `607519b8..60752f56`, `6079e1f6..6079f309`, and
`608ee360..608eef34` from accessible ROM and code. This establishes a useful
dependency boundary **after entry**. It does not show that reset can reach that
entry with a damaged application, or that an eventual patch has no other effects.

### Write extent and lost errors

The selected branch passes a complete component's length to the write wrapper.
A main-only restore would therefore request **26214400 bytes**, including the
component envelope, rather than rewriting only the edited bytes. The native
lower code contains 131072-byte block and 2048-byte page handling. The full main
component is 200 such blocks arithmetically; this is not a measured flash trace
or proof of every physical erase/program extent.

Four additional native runs inject errors at explicit program/read boundaries:

- Program boundary returns `3101`: native wrapper `6043a0d9` returns `3101`.
- Readback boundary returns `3102`: that wrapper converts it to `3105`.
- Calling outer selector `604a0f8b` around either case returns **0**. Its
  mode-1 path reaches an unconditional clear of the result at `604a11a1`.

The flash-access-mode setter runs natively against a declared RAM halfword.
No program, erase or readback operation is performed on storage. These tests
demonstrate **status propagation**, not an observed camera write failure. They
also explain why the earlier shared-updater error test is insufficient alone:
the error can be lost below the boundary where that test injects it.

## What can be said about restoration

| Camera state after a future experiment | Present assessment |
| --- | --- |
| Boots and updater is reachable | A compatible stock restore is plausible; same-build fixture acceptance supports it. Actual E-PL9 restoration is untested |
| Only ART/UI fails, and an independent entry still reaches the SD updater | The updater's tested independence from selected ART routines is encouraging; the entry condition is unproved |
| Bootloop or hang before updater activation | Recovery unknown. Holding a button or reconnecting USB is not an established guarantee |
| Interrupted write, incomplete main, damaged early boot or storage failure | No verified recovery method; repair could be required |
| Calibration/settings damaged by an erroneous runtime write | Reinstalling the downloaded stock components is not established to restore the missing device-specific data |

The SD client and service being studied are bytes **inside the main component
being replaced**. No separate immutable loader, A/B application images, automatic
rollback, or complete reset-to-SD entry has been established for E-PL9. This is
an evidence limit, not proof that every possible service recovery is absent.

The earlier user report of a working ABel duration mod demonstrates a historical
modification precedent, not recovery from a failed E-PL9 installation. Its
inventory entry identifies a historical package of 104552480 bytes, SHA-256
`131960883affe65e3200489359486ce643fc19cd0272e1dbccd69ff4f9c25f27`,
main build 1101, filename `e1339999.bin`. That package was **not present, read or
installed in this audit**; this is inventory/source evidence only. PEN-F and E-P7
restoration reports likewise do not close the E-PL9 entry gap.

## Gates before a first installation

These gates separate work possible now from a later, explicitly authorized
camera phase. None authorizes flashing during the current offline phase.

1. **Pin the final candidate to this stock identity.** Enumerate every changed
   byte, original/replacement bytes and source revision. Preserve model, component
   destinations, lengths, header/trailer fields and unrelated components. Reject
   duplicate kinds, unexpected components, truncation and trailing data on the
   host; do not rely only on the native checksum. Padding alone does not prove
   unused executable space.
2. **Prepare a matching restore design.** It must replace every component the
   candidate changes: main for processing, OSD for badges/labels, picture kind
   `0102` for large examples, and any additional modified component. Main-only
   restoration cannot undo changes to other components. Verify restore payloads
   against exact stock and retain hashes. No restore BIN was generated here.
3. **Qualify the actual package and patch.** Re-decode/re-encode exactly; check
   modified payloads against the intended edit list; test native acceptance with
   realistic full component sizes and failure controls. Preserve updater code,
   its data/callees and startup dependencies. Execute patch-specific cache,
   callback, ownership and error-path regressions. A successful color preview
   or checksum is not this verification.
4. **Resolve the entry dependency.** Trace reset/early startup, the physical
   button snapshot, task-89 activation, SD initialization and the code that must
   survive a bad mod. Determine whether the entry requires bytes in the component
   being rewritten. Until then, describe a restore as conditional and do not
   promise recovery from a bootloop.
5. **Plan settings compatibility.** Reverting application code does not prove a
   revert of saved parameter formats or calibration. Keep future recipe storage
   compatible with stock, avoid unqualified nonvolatile writes, and establish
   what the actual camera can back up. Do not use factory reset as a recovery
   substitute.
6. **Later camera qualification:** establish the exact E-PL9 update procedure,
   power/card prerequisites and completion indication from model-specific
   evidence; verify media readability and transfer integrity; demonstrate
   stock restoration on a functioning test body before relying on it. Existing
   MTP enumeration and accepted card-reader copying do not establish updater
   readiness. Do not reuse another model's filename, LED timing or forced-stop
   timeout without verification. A test on a healthy body still cannot guarantee
   recovery after power loss or arbitrary boot corruption.

The current decision is to continue offline work. A first installation is not
qualified by this report. The most important remaining research is the physical
startup-to-updater entry, followed by full-size package/write/error qualification.

## Reproduction and retained evidence

```powershell
.\.venv\Scripts\python.exe scripts/epl9_recovery_audit.py --out local/new-recovery-audit
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_epl9_recovery_audit.py -v
```

Use assertions enabled and a new ignored `local/` output directory. On this
workstation the pinned reader requires the approved execution path outside the
Windows sandbox because of the already documented DLL relocation issue. This
does not require camera access, network access or a Windows reboot.

Final evidence: `local/epl9-recovery-audit-20261104-verified/results.json` plus
byte-checked native listings. **11 shared-updater scenarios, four write-status
scenarios and 13 instruction anchors pass. Nine synthetic host-guard tests pass.**
The tests retain rejection of metadata mismatch even when the additive checksum
is repaired. They are not physical recovery or successful-installation tests.
