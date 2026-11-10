# E-PL9: indirect SD-task starts and BOOT acquisition evidence

Online follow-up: [public BOOT/dump search and hardware evidence, 2026-11-04](epl9-online-boot-search.md).
It identifies downloaded archive copies and their provenance; this document's
offline execution results and historical source-access statements remain scoped
to the pass described below.

## Result — 2026-11-04

**No physical OK/power producer selecting SD task 89 has been established.**
This pass follows three generic indirect mechanisms further upstream and runs
their native producer/consumer fragments. They transport or wrap a supplied task
ID; none of the reviewed producers discovers/selects 89 from OK input.

The available E-PL9 stock package contains no BOOT-tagged component, including
no valid nested `OE`/model-1330/BOOT envelope in any of its five decoded payloads.
The saved official offer and the two E-PL9 entries in the pinned archive inventory
do not identify another BOOT source. **A confirmed E-PL9 BOOT download is therefore
not established by the available offline evidence.** This is not a claim that
no such file exists anywhere.

No network request, camera access, USB/card operation or firmware write was made.
All endpoint/URL statements below refer to saved records, not present online
availability. No installable image or extracted BOOT binary was generated.

## Exact inputs and source records

Olympus PEN **E-PL9**, model bytes **1330**; displayed body version **1.1** is
owner-reported. Main internal build **1101** is from the downloaded update, not
an installed-device dump.

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| `OLY_E_133_1101_0000_0000.BIN` | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Decoded main `00_0100_406e0020.decoded.bin` | 26214336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |

Main analysis base is `60400020`; addresses below are hexadecimal. The new native
runner records hashes of its source, reader and imported helpers, including the
current shared instruction engine. Other chats' engine/ART/video work was not
modified. The pinned upstream reference remains
[fishcu/oly_fw_analysis](https://github.com/fishcu/oly_fw_analysis/tree/539fcf1fa9eda5fdef8ede4deeab94a4691d94c3),
commit `539fcf1fa9eda5fdef8ede4deeab94a4691d94c3`.

## 1. Queued operation 9 preserves the caller's ID

```text
caller supplies task ID
  → 604318bb chooses local activation or queued forwarding
  → 60433b2f builds operation 9, supplied ID at packet+20, source CPU at +12
  → transport boundary 60433e02
  → 60433ca9 dispatches operation 9
  → 60433d72 calls 60410727 with packet+20
```

The image-wide relative-transfer/exact-pointer survey finds one direct candidate
caller of `60433b2f`, at `604318c7`, and no exact stored function pointer. That
call is instruction-checked inside the general start wrapper. The wrapper
retains its input ID; it does not manufacture 89 or examine OK.

Native cases supply task IDs 1 and 89, source CPUs 0/1/2, and an unavailable
packet control. A successful producer sets operation 9 and preserves the supplied
ID. A separate consumer fragment receives those **same packet bytes**, requests
the supplied ID through a trapped activation API, stores result 0 and completion
state 5. It stops before writing the inter-CPU interrupt register. Allocation
failure returns 255 without a transport request.

The packet allocator, transport result, release and completion notification are
explicit software boundaries. This is packet-contract execution, not a working
cross-core scheduler. Supplying ID 89 demonstrates the carrier's behavior; it
does not supply the missing physical selector.

## 2. Mailbox activation exists, but reviewed senders are used for stopping

| Route | Producer | Command / task / acknowledgement fields | Start slice |
| --- | --- | --- | --- |
| CPU1 mailbox | `60438c39` | `8ff00060` / `8ff00064` / `8ff00068` | `604389bf..60438a05` |
| CPU2 mailbox | `60438fe3` | `8ff00088` / `8ff0008c` / `8ff00090` | `60438d74..60438dba` |

The producers write the supplied command and ID and clear acknowledgement.
Command `10001` reaches the activation API with that ID. The tested start slice
then clears the command and sets acknowledgement 1. Command `10002` bypasses
this start branch; the fixture stops before the subsequent stop-command handling.

Each producer has one direct relative-call candidate, and no exact stored pointer:

- `60431919 → 60438c39`;
- `6043193c → 60438fe3`.

Both reviewed call sites belong to wrapper `604318ff` and explicitly load command
**10002**, not 10001. Four native mailbox cases contrast the two commands for
both mailboxes with supplied ID 89. The 10001 cases are controls of the generic
mechanism, **not discovered recovery callers**. Diagnostics and critical-section
helpers are modeled; mailboxes are RAM fixtures and no CPU is actually notified.

These candidate surveys cannot rule out arbitrary computed writes or other
unreviewed code. They do rule out treating the identified stop-wrapper producers
as proof of an OK-triggered start of SD task 89.

## 3. The existing-thread object route does not discover a dormant SD task

Factory object `6239cf50` is initialized from main `60632210` with vtable
`60ef1a64`. The reviewed caller slice `60dbb3d3..60dbb3ed` calls its current-ID
method, then wraps that ID using vtable+36 (`60db9f77`). The existing-ID constructor
`60db9b9d` stores the supplied halfword at object+4; it sets vtable `60ef19d0` and
two ownership/state words to 1. It does not activate a task.

Native controls supply current-task replies **1** and **89** through query
`604117be`. The resulting objects contain those same IDs and neither case requests
activation. **Current=89 already presupposes that the SD task is running**; it
cannot explain how a dormant task 89 first becomes current.

The object's separate start method `60db9d0a` reads object+4 and calls the kernel
activation API. An explicit method call on a fixture containing 89 requests 89;
a fixture containing `ffff` is ignored. This proves a generic existing-ID route,
not its reachability from OK. Allocation and current-task replies are declared
models; the physical task scheduler does not execute.

Timer constructors also store IDs returned by dynamic creation. Their resemblance
to this existing-ID wrapper must not be used to silently substitute SD ID 89.

### A dormant task does not become a newly allocated thread

Native allocator `60414e95` examines TCB+16 to find an unoccupied ID. Four cases
use stock pointer/count tables and explicitly declared occupancy/cursor state:

| Fixture | Result |
| --- | --- |
| Occupancy from all 143 stock descriptors; automatic allocation | ID **144**, skipping occupied SD ID 89 |
| Same fixture with only ID 89 deliberately cleared | ID **89**, an explicit counterfactual control |
| Explicit ID 89 request against the stock configured explicit-ID range | **-18**; no allocation |
| All 255 slots occupied | **-34**; no allocation |

The first case supports excluding accidental reuse of dormant ID 89 by ordinary
automatic allocation in this state. It does not prove ID 89 can never be deleted,
modified or deliberately reused later. These cases do not activate tasks.

## What the available sources actually offer for E-PL9 BOOT

| Source inspected offline | Evidence | BOOT result |
| --- | --- | --- |
| Saved official catalog response, 2026-11-02 | Model E-PL9 / 1330, offer 1101, 104552480 bytes | Offers the already pinned stock package; that package has no BOOT-tagged component |
| Pinned inventory's E-PL9 stock-reference entry | Same filename, size and whole-file hash as our stock | Same five kinds; no BOOT tag |
| Pinned inventory's historical E-PL9 modification | `e1339999.bin`, 104552480 bytes, SHA-256 `131960883affe65e3200489359486ce643fc19cd0272e1dbccd69ff4f9c25f27` | Inventory reports the same five kinds; no BOOT tag. File itself was not fetched or read |
| All five decoded stock payloads | Bounded search for complete checksum-valid `OE` / 1330 envelopes with low kind byte `10` | Zero accepted or rejected BOOT-header candidates |

The stock kinds are `0100`, `0101`, `0106`, `010e`, `0102`. The low-address
`010e` component is not BOOT merely because its destination is `40002800`.
The nested-envelope scan cannot exclude bare, compressed or differently wrapped
loader code; it establishes only the absence of the searched container form.

Saved official endpoint:
[OM firmware catalog](https://fw01.om-digitalsolutions.net/ww_inform/fcache.do).
Its locally saved response identifies an `E`-body update for model 1330. This is
not evidence for an undocumented BOOT/service endpoint. The request's installed
version field is not a requested historical-version selector. Changing it or
guessing a `1000` filename does not establish an obtainable factory BOOT package.
Temporary signed URLs are omitted from public documentation and sanitized by
the new inspector; their present validity was not tested.

The archive evidence is the pinned
[firmware inventory](https://github.com/fishcu/oly_fw_analysis/blob/539fcf1fa9eda5fdef8ede4deeab94a4691d94c3/provenance/firmware-inventory.json).
Its xdel stock/mod URLs identify historical sources, not newly verified downloads.
Neither replacing an `E133` filename prefix nor renaming a main image creates BOOT.

The SD client contains `S133????BIN` and `E133????BIN` selection patterns. They
show filename handling for this model, **not a known BOOT download location**.
In particular, the `S` pattern is not sufficient to identify a file's contents
or prove an independent recovery loader.

## Where a usable BOOT input would have to come from

These are acquisition requirements, not sources whose availability is confirmed:

1. **An authenticated E-PL9 service/factory package**, obtained from OM support,
   a service archive or its original owner with a traceable source. Request the
   primary loader/BOOT for **E-PL9, model 1330**, not another copy of public 1101
   main. A package with a native BOOT tag is a candidate for analysis; it still
   needs an identified execution/address map and a model/board compatibility check.
2. **A documented read-only dump from an actual E-PL9**, either this body in a
   separately authorized later phase or a donor with reliable provenance. Record
   body/main/boot versions where known, board identifiers, chip/region layout,
   read method, byte count and SHA-256. Distinguish a logical image from a physical
   dump and document handling of service/spare bytes or bad blocks if applicable.
   A whole-flash dump is not automatically a dump of the SoC's internal reset ROM.
3. **An earlier complete E-PL9 factory/update archive**, if independently found
   and identified. It might include BOOT, but no such earlier file was established
   in the reviewed records. Do not infer its build number or contents from the
   displayed version alone.

No camera read/dump, opening of the body, programmer operation, service request
or message to another person was performed. Another camera model's BOOT and an
unattributed repair-site BIN do not satisfy the E-PL9 identity requirement.

## Read-only inspection prepared for a future candidate

[epl9_boot_source_audit.py](../scripts/epl9_boot_source_audit.py) can inspect a local
candidate without installing or extracting it:

```powershell
.\.venv\Scripts\python.exe scripts/epl9_boot_source_audit.py --candidate local/candidate.BIN --out local/new-boot-source-check
```

For `OE` containers it checks model 1330, envelopes, lengths, duplicate kinds,
header/trailer agreement and decoded checksums, recording component builds,
destinations, sizes and hashes. A BOOT low-kind byte is labeled **candidate**,
never independently bootable or ready to install. For raw/non-OE input it records
identity and searches bounded envelopes but leaves the camera model unproved.
It rejects a checksum-valid PEN-F/model-1220 control and does not misclassify
the `010e` low-address component.

## Validation and consequence for recovery

[Native runner](../scripts/epl9_indirect_start_audit.py):
`local/epl9-indirect-start-20261104-verified/results.json` and fifteen byte-checked
listings. **Five queue cases, four mailbox cases, four object cases and four
allocator cases pass**; queue cases include four separate consumer executions.
Inputs deliberately supplied as 89 are marked as fixtures throughout.

[Source inspector](../scripts/epl9_boot_source_audit.py):
`local/epl9-boot-sources-20261104-final/results.json`.
[Eight synthetic guard tests](../scripts/test_epl9_boot_source_audit.py) pass,
including nested-envelope positive/corruption controls. No firmware bytes from
the original images are published in these scripts or documentation.

The new evidence excludes several tempting false joins but does not identify
the missing OK selector. Recovery through the mapped main-resident client still
requires its code/dependencies to survive. **Recovery after arbitrary damaged or
missing main remains unverified**, and no independent loader input suitable for
closing that question has yet been obtained.
