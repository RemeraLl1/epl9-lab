# HLS_EVENT stop and user inventory: cloud evidence boundary

2026-11-10. This follow-up preserves the later parent handoff and prepares an
independent stock-only inventory. **No new native HLS instruction was decoded
or executed in this follow-up:** the exact stock main and the previous native
listings are still absent. A Library search also did not resolve those inputs
or the missing shutdown files. The separate validator results in
[the cloud continuation](epl9-sd-cloud-continuation.md) concern authored recipe
validation, not HLS task stopping.

## Later handoff, still not available for review

The parent reports that the last completed Windows step is
`docs/epl9-sd-session-shutdown.md`, with these sources:

- `scripts/epl9_sd_session.py`
- `scripts/epl9_sd_session_probe.py`
- `scripts/test_epl9_sd_session.py`
- `firmware_src/epl9_sd_session.s.in`

Its reported final evidence is
`local/epl9-sd-session-20261110-final-v3/validation.json`. The reported
53-test result says live caches/executor retain memory, operations during
closing return BUSY, and the getter returns NULL after closing begins.
**These are handoff statements, not cloud-reviewed implementation or
independently reproduced results.** None of the files or the report is
available here. No substitute shutdown code is created by this follow-up.

Unfinished research into HLS_EVENT stopping and users of five lists was saved
under `local/epl9-hls-stop-discovery-20261110/` on the laptop. That directory
is also absent. Laptop access was interrupted, and stopping the local chat
was not confirmed. The cloud tools used here provide no confirmation that
that chat has stopped. Chat status and the camera's HLS task status are
separate unknowns.

## What the published checkpoint actually supplies

All addresses below come from earlier published source/docs. They have not
been freshly decoded without the exact input bytes. A source audit window
does not establish a complete function, complete caller graph or stop path.

| Recorded location | Existing evidence | Limit for this question |
| --- | --- | --- |
| `60ae187f..60ae1a3e` | Constructor/destructor area included by `epl9_sd_state_audit.py` | Native listings are absent; do not reconstruct instructions from prose |
| `60ae1910..60ae1944` | Earlier placement probe executes the destructor prefix and observes two 40-byte and three 1024-byte buffer releases | Execution deliberately stops before base cleanup; no HLS stop acknowledgement is demonstrated |
| `60ae1a4d..60ae1aac` | Singleton getter/root `6239790c`, lock 2, allocation and publication recorded | A nonnull or cleared root alone does not account for already-held pointers; reported new NULL behavior is unavailable |
| `60ae1bb2..60ae1c12` | Task creation adapter recorded; manager +172 stores the returned task ID | Creation argument 54 and fixture task ID 54 do not establish a runtime task ID or stop operation |
| `60ae1c12..60ae1d19` | Known prefix of HLS_EVENT, included in the earlier `hls_init` window | The complete loop/exit and all later dispatch branches are not covered by that recorded prefix |
| `60ae1c6e -> 60ae2073`, continuation `60ae1c73` | Existing event-get adapter and SD hook point | Receiving an event or returning zero is not proof of task exit, queue drain or no future callbacks |
| `60ae2099..60ae226f` | Earlier `manager_vectors` audit window | Neither exact identities of all five lists nor complete external users can be recovered from the window's name |
| `60ada380..60ada3e2` | One recorded `root_users` window | It is not the complete set of users; the earlier raw scan's 65 getter candidates also do not establish all direct/indirect users |

The five observed buffer releases must not be equated with five fully
classified subscriber lists. Buffer sizes do not identify element types,
registration/removal semantics, outstanding callbacks or retained owners.
The existing [lifetime negative control](epl9-sd-placement-lifetime.md)
demonstrates that a deliberately freed manager can remain reachable through
the stock singleton getter; it does not demonstrate the camera's normal
shutdown sequence or reproduce the later fix.

## Independent stock-only inventory, ready to run after input transfer

[`epl9_hls_cloud_inventory.py`](../scripts/epl9_hls_cloud_inventory.py) needs
only the exact downloaded E-PL9 build 1101 main and the qualified GNU reader.
Unlike the old full state discovery, it does not require frozen candidate
packages, local recipe exports or the missing shutdown implementation.

It verifies the input size/SHA, privately snapshots it while decoding the
eight already-recorded HLS/root/event windows, byte-checks every listing, and
records raw CALL candidates for six known entry addresses and raw root-word
matches. These are triage candidates: encoded patterns may occur inside data
or another instruction. The report leaves full-loop coverage, stop
acknowledgement, complete five-list users, draining and installation false.
It neither invents function boundaries nor assigns termination semantics.
The temporary firmware copy is removed on success or failure; native listings
and reports remain ignored under `local/`.

```sh
python3 -m unittest discover -s scripts -p 'test_epl9_hls_cloud_inventory.py'
python3 scripts/epl9_hls_cloud_inventory.py \
  --out local/new-hls-cloud-inventory
```

Six new synthetic guard tests pass: raw pattern matching, exact offsets,
missing/wrong input rejection before output or decoder use, snapshot cleanup,
altered listing rejection and conservative result flags. They are separate from the 48 SD tests and
from the handoff's 53 shutdown tests. A real invocation was attempted here
and stopped with missing file
`local/epl9-1101-analysis/decoded/00_0100_406e0020.decoded.bin`; no native
inventory report was produced. This is tool preparation and a confirmed input
blocker, not a completed HLS native investigation.

Expected main: 26214336 bytes, SHA-256
`8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
An authorized private transfer of this one file is enough to start the
inventory; the full shutdown review additionally needs the actual later
sources and retained reports.

## Evidence still required to close the question

The next native investigation must identify the actual loop's termination and
acknowledgement path, using its runtime task/manager instance, and all ways
that can enter or re-enter dispatch after that point. A destructor prefix,
an empty queue or an event-get return is insufficient by itself.

For each of the five lists, establish its manager-relative layout, actual
element type, registration/removal sites, iteration/callback paths and retained
references. Then account for borrowers outside the lists: pending file RPCs,
processing requests, live configuration/cache pointers, executor activity and
any queued callback that can still access the manager or recipe storage.
The handoff's BUSY/NULL rules must be checked against the actual missing code;
NULL for new lookups does not prove that prior borrowers have released data.

No native stop API, task termination number, list offsets, user count or safe
release sequence is guessed here. Existing stock/v3 candidates and packages
remain unchanged. Camera, SD hardware, full RTOS scheduling, cache/DMA lifetime
and physical restart/removal are still unqualified. Original firmware is not
published and no camera operation is performed.
