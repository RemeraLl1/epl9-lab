# E-PL9 early main, section loading and SD-recovery dependencies

## Result — 2026-11-04

Follow-up: [OK/power input and native task construction](epl9-ok-power-entry.md)
now executes the descriptor-to-TCB construction and confirms that the tested
auto-start walk requests only task 1. It also corrects the earlier reply-queue
89 interpretation. The physical OK-to-SD edge remains unresolved.

The **mapped SD updater lives inside main**; no separate rescue image has been
identified in this package. Its client and service are in main's section 6. The ordinary startup chain needs
early main, RTOS services, section loading and additional initialization before
starting the firmware service. Preserving just the updater functions or a stock
BIN on a card does not establish recovery after damage to main.

This pass maps early **main**, not the CPU's physical reset vector. The physical
OK-button-to-task-89 selection is still unconnected. No immutable rescue ROM,
alternate application bank or automatic rollback has been identified. These are
limits of the evidence, not a claim that manufacturer service recovery is absent.

No camera, USB device or SD media was accessed. No update/restore package or
modified firmware was produced. Online community research is recorded separately
in [Olympus/OM incident review](olympus-om-update-incidents.md).

## Exact input

Olympus PEN **E-PL9**, model bytes **1330**; displayed body version **1.1** is
owner-reported. Main internal build **1101** belongs to the downloaded update,
not a dump of the installed camera.

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| `OLY_E_133_1101_0000_0000.BIN` | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Decoded main `00_0100_406e0020.decoded.bin` | 26214336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |

Analysis base is `60400020`. The stock container's main destination is
`406e0000`; executable, container and uncached addresses are different domains.
All addresses below are hexadecimal. See the preceding
[installation/recovery audit](epl9-installation-recovery.md) for all five stock
components, complete checksum checks and native updater/write-status tests.

## Early-main chain found in this image

| Stage | Exact-image observation | Recovery implication |
| --- | --- | --- |
| `60400020` | Early-main entry masks PSW, makes early calls and clears RAM; later installs SP `470007fc` | Already executes bytes from the component a mod would replace; this is not an identified immutable reset loader |
| `604000e9` | Reads register `98e00054` into `6257d7c0` | A latched hardware value, **not a decoded OK-button snapshot** |
| `604000d6..dc` | Loads `604000f9` and jumps there | Native handoff into main initialization |
| `604000f9` | Copies initialized data, sets memory/section-related globals and invokes hardware/service setup | Requires valid code, data, stack and RAM mappings |
| `604001b9..cb` | Requests logical-flash `406f0000` → RAM `a0410000`, length `a0800`, through `604014c6` | Early startup itself needs the flash-read path; this fragment does not test a physical read |
| `604003c5` | Calls `6041009c`, which jumps to RTOS entry `604125e0` | The mapped route depends on the RTOS in main |
| Task 1, `60432197` | Initial task; includes a `40060000` → `a2c65000`, 131072-byte read | Additional storage/configuration dependency; its contents are not identified as a complete recovery backup |
| `604322d6..e1` | Polls `604005d3` until 1, then calls `60421d35` | A readiness wait can prevent later service startup; hardware/peer behavior is not emulated |
| `60421d35` → `604223fa` | Ordinary initialization reaches USTART1 and starts task 46, then other startup workers | This is a distributed startup sequence, not a direct reset-to-updater call |
| Task 42, `6056b7b0` | USTART5 waits for section IDs 7, 8 and 9 before its later service starts | The **ordinary** firmware-service start has additional loading dependencies |
| `6056bf4a..51` | Reads task ID 18 from `60420ba8`, calls `604318bb` | Actual ordinary activation site for firmware service `61003e85` |

Task 46 is `60421f68`; USTART2/3/4/5 are tasks 43/45/44/42, respectively.
Do not equate task IDs with table slot numbers. There are **143 nonempty rows**:
slot 0 is special ID `808a`, slots 1–137 have matching IDs, slots 138–142
contain IDs 139–143, and slot 143 is the zero sentinel. Among these stock
descriptors, only task 1 has nonzero attributes (`2`). Task 18 and SD-client task
89 both have attributes 0. The kernel activation walk tests a runtime task flag
`2`; the complete descriptor-to-runtime construction was not executed here, so
descriptor inspection alone is not a proof of every startup activation. The
linked follow-up now executes this construction/walk with explicit RAM and
allocator boundaries; it does not execute a complete reset replay.

The direct-call candidate survey did not locate a validated task-89 activation
site. Such a survey cannot exclude computed IDs, indirect calls, another CPU or
selection in code outside this downloaded component. The number 89 found
in the previous request was misclassified: it is a reply queue in that request,
not the SD task identifier. See the follow-up's native-helper dataflow review.

## Section map confirmed with bounded original instructions

`604229df` resolves section endpoints through its native jump table.
`60422a3c` combines those endpoints with the 12-byte records at `60405f94`,
translates the source/destination domains and requests a read through `6043ae0d`.
The length is **endpoint minus row start**, not translated destination minus row
start. The call preserves `d2` across address translation. Section 8 is empty in
this stock build; its zero length is not a discovery failure.

| ID | Main start | End, exclusive | Bytes |
| ---: | --- | --- | ---: |
| 1 | `604b7800` | `60601000` | 1349632 |
| 2 | `6066f800` | `6092c800` | 2871296 |
| 3 | `60942200` | `6096d000` | 175616 |
| 4 | `60973a00` | `60abc000` | 1345024 |
| 5 | `60acc800` | `60efe000` | 4397056 |
| **6** | **`60f1b000`** | **`61630000`** | **7426048** |
| 7 | `6164b000` | `61738000` | 970752 |
| 8 | `61741000` | `61741000` | 0 |
| 9 | `61745000` | `617b9000` | 475136 |

Section 6 contains the SD client `610039fd`, service `61003e85`, shared updater
`6100440a`, and selection strings at `61327e54/60`. Filesystem requests from the
client also reach `609b9ef8` / `609c0b12` in section 4 and the RTOS/cross-service
request helper `60434bbe`. The mount/unmount helpers are `61003c58/98`.
Thus, an intact section 6 alone is not a sufficient recovery condition.

The translation helper `60445069` is conditional: it converts addresses in
`40000000..40ffffff` and `60000000..7fffffff` to the uncached alias. It does
**not** blindly convert all `4xxxxxxx` addresses. For section 6 the read request
uses source `411fb000`, destination `a0f1b000`, length `715000`, mode `101`.
These are observed call arguments, not a physical NAND trace.

The ordinary loaders include waits and handshakes; they are not a simple
strictly sequential walk through the table. USTART4 waits for sections 5 and 6.
USTART5 waits for 7/8/9. The complete concurrent boot schedule and error handling
of the lower storage implementation remain unqualified.

### A loaded bit does not establish a good read

The reader tests the low 16 bits of the storage result. On a nonzero result it
logs diagnostics, but then joins the same tail that sets the loaded bit in
`a2aeaa3c`. Native runs with injected read error `3101` for sections 1 and 6
confirm that behavior in the modeled synchronous boundary. No valid section
bytes are supplied by the read trap.

The section-6 wait at `60422ac1` stops at a scheduler-delay call when bit 5 is
clear and passes that first gate when bit 5 is set. This pass does not execute
the subsequent cache/constructor initialization or prove whole-image integrity.
Neither a loaded flag nor reaching the next task is a recovery qualification.

## What must survive, and what remains unknown

For recovery through the **mapped** SD path, the following dependencies need to
remain executable and coherent. This is a lower-bound dependency inventory,
**not a complete byte-level keep list or an established minimal rescue image**.

| Dependency | Code/data already identified | Consequence of damage |
| --- | --- | --- |
| Pre-main selection/loading | Physical reset and OK selection not identified | No assurance that main or updater will be entered |
| Early main and runtime | Entry/initialization above, RTOS, task descriptors, startup workers, RAM/stack/cache initialization | Hangs or incorrect task state can prevent updater activation |
| Section-loading machinery | `604229df`, `60422a3c`, `60422ac1`, section table and storage-read callees | Section 6 or its dependencies may never become usable |
| SD/filesystem/message resources | Client mount/read helpers, section-4 filesystem path, queues and dispatch/allocations | A visible menu or existing BIN filename does not guarantee an update can be read and submitted |
| Updater and metadata | Task 89, task 18, validator/checksum/descrambler, pattern/model tables and callers | No compatible package selection/validation/write dispatch |
| Flash backend and power | `6100511c` → `604a0f8b` → lower program/readback path | A started restore can still fail; previously observed lost error returns remain relevant |

A hang strictly after all required services become usable is a more favorable
state than corrupt early main, but no independent pre-hang SD entry is proved.
The previous updater isolation test starts **after explicit entry** and removes
selected ART/COLOR code; it does not establish a reset-to-recovery route with
those holes. Avoid generalizing it to arbitrary ART changes.

An interrupted main write is more serious than a deterministic runtime bug:
the same component carries startup and the updater. Preservation of downloaded
stock files cannot replace missing executable recovery code on the device.
No on-camera interrupted-write or boot-corruption experiment was performed.

Before first installation, the unresolved gate remains the exact physical
selector: trace the OK/power input, selected startup path and task-89 activation,
including other-CPU/indirect dispatch if necessary. Then close the transitive
dependency map and qualify full-size restore behavior. Until that is done,
restoration must be described as **conditional on a reachable working updater**.

## Reproduction and limits

```powershell
.\.venv\Scripts\python.exe scripts/epl9_boot_recovery_audit.py --out local/new-boot-recovery-audit
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_epl9_boot_recovery_audit.py -v
```

[Runner](../scripts/epl9_boot_recovery_audit.py) and
[synthetic guard tests](../scripts/test_epl9_boot_recovery_audit.py) do not change
the shared CPU subset. Both firmware inputs and the reader are hash-gated;
listings are byte-checked against main. The reader SHA-256 is
`e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae`.
Source and imported-helper hashes are retained in each report. Reference:
[fishcu/oly_fw_analysis](https://github.com/fishcu/oly_fw_analysis/tree/539fcf1fa9eda5fdef8ede4deeab94a4691d94c3),
commit `539fcf1fa9eda5fdef8ede4deeab94a4691d94c3`; other-model boot findings are
comparison material, not E-PL9 offsets or recovery measurements.

Nine native endpoint fragments stop immediately before RETS. A declared bridge
supplies their separately measured result to the section-read fragment because
the shared call engine does not implement RETS. Address conversion and the
rest of that fragment run natively. The lower storage call is trapped and its
return value explicitly injected; diagnostics and section-7 extra initialization
are declared models. Unknown instructions, memory or undeclared calls stop.
No scheduler, flash contents, real media read, image integrity check or complete
physical boot is supplied by these models.

Validation: **11 section-read cases, two section-wait cases, 19 instruction
anchors and 143 descriptors; six synthetic guard tests**. Retained final
evidence is under ignored `local/epl9-boot-recovery-20261104-final/`.
