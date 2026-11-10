# E-PL9 OK/power entry: native input and task-selection follow-up

## Result — 2026-11-04

Follow-up: [indirect starts and BOOT sources](epl9-indirect-start-boot-sources.md)
now executes queue/mailbox/object/allocator controls and audits the saved E-PL9
catalog and stock payloads. It does not yet identify a physical OK producer or
a confirmed BOOT source.

**The physical OK+power → SD-client chain is still not closed.** This pass
narrows the gap and removes a misleading number-89 lead. The mapped main-resident
SD client cannot recover a completely missing main by executing itself. Whether
some other, earlier loader can restore main is still unknown.
It is not yet established that physical OK+power uses this particular client
(task 89) at all; it could use a different path before main.

New E-PL9 evidence:

- The actual native RTOS constructor creates all 143 stock descriptors in a
  255-slot task-control table. The subsequent native auto-start walk requests
  only task 1. SD client 89 and updater service 18 remain dormant at that boundary.
- The ordinary OK state lookup is mapped and runs natively on four declared
  snapshots. It is distinct from the controller's wake-reason decoding.
- Two hooks called during ordinary startup, near firmware-service activation,
  are return stubs in this build. Neither selects/starts the SD client.
- The constant 89 at `60421018` is used as a **reply queue**, not as a task ID
  in the previously inspected request. It does not establish task-89 activation.
- The updater has a BOOT component branch, but none of the five components in
  the available stock update has that branch's low kind byte `10`.

These observations do not prove the physical selector is absent from main.
Computed IDs, unreviewed indirect dispatch, another CPU or code preceding the
available main entry remain possible. No independent reset loader has been
identified or executed here.

No camera, USB device, card or network was accessed. No firmware/update/restore
image was produced. This work extends [early-main analysis](epl9-early-boot-recovery.md)
and the [updater audit](epl9-installation-recovery.md).

## Exact inputs

Olympus PEN **E-PL9**, model bytes **1330**. Displayed body version **1.1** is
owner-reported; downloaded main internal build **1101** is not an installed dump.

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| `OLY_E_133_1101_0000_0000.BIN` | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Decoded main `00_0100_406e0020.decoded.bin` | 26214336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |

Analysis base `60400020`; addresses below are hexadecimal. The stock package
contains kinds `0100`, `0101`, `0106`, `010e`, `0102`. Local firmware inventory
contains this stock BIN and its three download archive parts; no separately
identified E-PL9 boot/whole-flash dump was found in the reviewed local inputs.
Kind `010e` is not relabeled BOOT on the basis of its lower destination address.

## What native task construction establishes

`604129aa` reads stock CPU-zero configuration `6042143c`:

| Configuration field | Stock value / use |
| --- | --- |
| `+60` | Count structure `60421370`; task-slot count at `+2` is 255 |
| `+124` | Descriptor table `60418cc4`, 143 nonempty rows |
| `+204` | TCB pointer table `6041de48`, 255 distinct pointers |
| `+260` | Hook-enable word pointer `62596234` |

The constructor uses the low 12 ID bits to select a TCB, stores the ID at
TCB+16 and copies six descriptor words beginning at descriptor+4 to TCB+68.
It calls native initializer `60410b0c`. That initializer can add allocation flag
`80`; it does not turn on auto-start bit `2` for task 89.

The bounded run supplies CPU number 0, zeroed TCB RAM, a zero hook-enable word
and declared successful stack-address allocations. The actual stock descriptor
and TCB-pointer tables are read from main. No task stack executes. The allocator
boundary supplies addresses rather than proving a working boot-time heap.

Then the original walk `604127b4` visits all 255 slots. It requires a nonzero
low-12-bit task ID and bit `2` in TCB+68 before calling activation `60412230`.
Activation is trapped before scheduling.

| Task | Entry | Constructed TCB | Attributes after initializer | Auto-start request |
| ---: | --- | --- | --- | --- |
| 1 | `60432197` | `62582740` | `82` | Yes |
| 18, updater service | `61003e85` | `62582f38` | `80` | No |
| 89, SD client | `610039fd` | `62585080` | `80` | No |

Only task 1 is requested in this fixture. This closes the earlier
descriptor-to-runtime-flag gap for this native construction path. It is not
an uninterrupted reset replay, nor does it exclude another path changing task
state later. A dormant SD descriptor reserves a task identity; its presence
does not cause execution by itself.

## Ordinary OK input is separate from the wake reason

The image contains the exact mapping:

```text
02000004 → event 44 → EV_PRESS_OK_KEY
```

The pair is at `60e3e6ec`; the event-name row is at `60dda22c`.
State getter `604f427f` calls lookup `604f4e7a` / `604f4f1a` and bit comparator
`604f4eee`. In the **declared board-table variant 0**, the descriptor for key 4
is in group 1, index 6, with comparison level 0. The snapshot is the halfword
at `a2ae73e8`; the relevant bit is `40`.

| Snapshot fixture | Bit 6 | Getter result |
| --- | ---: | ---: |
| `00` | 0 | 0 |
| `40` | 1 | 1 |
| `bf` | 0 | 0 |
| `ff` | 1 | 1 |

The descriptor's active comparison level is zero. Do not reverse this API's
return convention and describe return 1 as a measured physical press.
The tested getter invokes no task-start API. This does not exclude a caller
using its return value to select recovery; that caller-to-SD edge is missing.
No electrical level or actual camera board-table selection was measured.

The initialized pointer data is taken from main `6061f800..6064e718`, 192280
bytes, matching early-main read `408ff800 → a238a540`. Its SHA-256 is
`8ee9f39b809daa23298cb69abecf4440b4a3c38c3e95bf86b0c324083651b439`.
This is a hash-pinned derived input, not a camera RAM capture. It supplies the
stock pointers, including `6238ba7c → 60585550` for the tested group.

Wake selection is a different fragment: `604446ee..6044476f`, within routine
`6044463c`. It reads controller gate `98e00000` and wake state `98e00048`, with
an additional check of `98e00064` bit 31. It stores the decoded ordinal at
`a2ad2a10`; getter `604447db` returns that ordinal. Ordinary key initialization
later translates it into `a2ae718c`, the diagnostic `key_poweron_factor`.

Eleven declared register fixtures exercise that decoder, including the bit-31
condition. They begin **after controller setup** and stop before acknowledgement
and hardware commit. The fixture does not pretend that writing a RAM register
reproduces a live input bit. No decoded wake ordinal is identified as the
physical OK+power recovery condition by these tests.

In particular, `98e00054` must not be substituted for the OK snapshot. Besides
the early-main latch, native code writes channel masks to it and queries its
bits. Finding it in early startup did not identify the recovery selector.

## Startup hooks, message correction and remaining indirect routes

Ordinary startup at `6056bf3c` calls `61003c54`, then calls `61003e82` at
`6056bf43`, before starting firmware service 18 at `6056bf51`.

- `61003c54` clears d0 and returns; it does not test OK or select a task.
- `61003e82` just returns. A nonzero test input remains unchanged.

Both stubs run natively in this audit. Their names/analogues on older cameras
cannot supply behavior absent from these E-PL9 instructions. The local
[upstream comparison](https://github.com/fishcu/oly_fw_analysis/blob/539fcf1fa9eda5fdef8ede4deeab94a4691d94c3/tools/oly_sd_selector_comparison.py)
was used as search guidance only; no other-model firmware was executed.

**Correction to the previous report:** `60f59c94` loads 89 from `60421018`,
but passes it in a1 to request helper `60434bbe`. That helper saves it at
SP+8 and passes it to receive API `604313e9` as the **reply queue**. Its request
goes to a separate queue. This is not a request to start task 89. The older
listing name `message_to_task_89.tsv` is historical and misleading.

The image-wide raw relative-transfer survey covers short branches, 16/32-bit
jumps and CALL, plus relative CALLS encodings. It yields:

| Target | Raw candidates |
| --- | ---: |
| SD entry `610039fd` | 0 |
| General start wrapper `604318bb` | 184 |
| RTOS activation API `60410727` | 25 |
| Stub `61003c54` | 2 |
| Stub `61003e82` | 1 |

The sole exact stored pointer to `610039fd` found in the previous pass remains
the task descriptor. The task-89 constant in the **task** ID block is
`60420c36`, distinct from reply-queue constant `60421018`; no exact pointer
reference to the former was found. These are negative candidate searches, not
a complete control-flow or computed-data proof.

Reviewed indirect start paths include queued operation 9 (`60433b2f` producer,
`60433d72` consumer) and CPU1/CPU2 mailboxes: command `10001` activates the ID
from `8ff00064` / `8ff0008c`. They can carry IDs dynamically, but no physical
OK producer selecting SD ID 89 was established. Initial cross-core startup
calls use other constant IDs. A command-capable mailbox is not a reset loader.

## Why the BOOT question needs separate evidence

The native updater tests the **low byte** of component kind for `10` at
`6100452a`, associates it with `[firmup]...BOOT Gets`, and has a separate
`TYPE_FIRMUP_WRITE_BOOT` branch beginning `610049ee`. None of the five stock
components takes that classification. This is code/format evidence, not a
located CPU reset vector or a demonstrated immutable boot ROM.

The available download therefore does not supply a separately identified BOOT
component whose reset/OK selector can be followed. A whole-flash/primary-loader
image, or another independently identified source of those bytes, is needed
to assess a proposed **main-independent** route. It cannot be replaced by a
guessed GPIO, an injected start of task 89 or another model's recovery report.
This does not establish that the missing selector definitely lies outside main;
an unreviewed indirect path inside main remains possible too.

## Recovery assessment

| Damage/state | Supported conclusion |
| --- | --- |
| Main is intact enough to enter the mapped updater | Stock restoration remains technically plausible; no physical E-PL9 restore was performed |
| Damage is confined to an ART routine used after startup | Prior tests show selected updater independence **after explicit entry**; physical entry still requires qualification |
| Early-main/RTOS/input/SD dependencies are damaged | The mapped route depends on those bytes and cannot be assumed usable |
| Entire main is missing or section 6 including `610039fd` is destroyed | This main-resident SD client cannot execute; a different loader would be required, and none has been verified |
| Interrupted flash write with unknown surviving ranges | Recovery unknown; no demonstrated universal rollback/recovery mechanism |

Preserving BOOT or keeping a stock file is insufficient evidence on its own.
Before relying on recovery, identify the real selector and prove which code it
loads/executes, then qualify complete SD/storage/write behavior. This report
does not qualify a first installation or authorize a camera experiment.

## Reproduction

```powershell
.\.venv\Scripts\python.exe scripts/epl9_ok_entry_audit.py --out local/new-ok-entry-audit
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_epl9_ok_entry_audit.py -v
```

[Runner](../scripts/epl9_ok_entry_audit.py),
[synthetic search guards](../scripts/test_epl9_ok_entry_audit.py).
Both firmware inputs and the GNU reader are hash-gated, and instruction listings
are byte-checked. Reader SHA-256:
`e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae`.
The report retains source/helper hashes and the explicit software boundaries.
Unknown calls/instructions/memory stop execution. No automatic scheduler or
peripheral response is invented.

Evidence: ignored `local/epl9-ok-entry-audit-20261104-final/results.json`
and twelve listings. **143 constructed descriptors / 255 visited slots,
one trapped auto-start request, 11 wake slices, four OK-state cases, two native
stub cases, 15 instruction anchors and five synthetic guard tests pass.**
These are bounded observations, not a complete physical boot/recovery replay.

Reference checkout is
[fishcu/oly_fw_analysis](https://github.com/fishcu/oly_fw_analysis/tree/539fcf1fa9eda5fdef8ede4deeab94a4691d94c3),
commit `539fcf1fa9eda5fdef8ede4deeab94a4691d94c3`. Its PEN-F/E-M5 work informs
questions only; no external project's source was republished here.
