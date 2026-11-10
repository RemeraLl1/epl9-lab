# E-PL9 v3: private COLOR parameters and logical readback

Follow-up, 2026-11-07. The film hook now has an **opt-in private-copy variant**
which removes the temporary recipe identity and controls from the caller's
shared request. Gold 200 v3 and Portra 400 v3, their complete table region, the
OSD icons and large example photographs are unchanged. This is a new decoded
main candidate, not a replacement of the previously frozen package files.

The stock executor itself has no entry lock in the tested dispatch path. The
new variant fixes the demonstrated COLOR overlap issue; it does **not** make
the whole job, hardware, output/cache or scheduler concurrently safe.
Physical installation, independent camera readback and restoration remain
unverified. No camera command, card preparation or flash write was performed.

## Exact input and candidate identity

Olympus E-PL9 / IM008 / model 1330; displayed body version 1.1 is the owner's
report. Downloaded main build 1101 is not a dump of the installed camera.

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| Stock update | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Stock decoded main | 26214336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |
| Frozen v3 decoded main | 26214336 | `501707d09a0eb648e46196752b7ece17cd5368f6d54dbabce7c73e9806f65686` |
| Private-COLOR v3 decoded main | 26214336 | `72cc1e48e6b42ab02b9911bdb841fe2c5b0cb34f2c08893f6b78be8a6871beee` |
| Private-COLOR module | 15360 | `8878c9c99d6ba28d996a86201ca0d4aef3ec6f0e37bac2af2140889025b6c685` |
| Unchanged icon OSD | 26214336 | `50141904c211fd16bc4c26b35cd52955f96a9e611ca062d84fe0169eeda21b3b` |

The new decoded main is
`local/epl9-v3-private-color-v2-20261107/private/main-with-module-OFFLINE-ONLY.decoded.bin`.
The native-owner run independently builds the identical main.
The module remains at `604a1300..604a4f00`; code grows from 1646 to 1781 bytes,
within the existing 4096-byte code allowance. All module bytes from offset
4096 onward match frozen v3. The old code prefix and the other three hooks also
match; only the appended private-copy code and COLOR branch target differ.

The original packages in `local/epl9-v3-packages-20261107` remain unchanged:
candidate SHA-256 `8d606a028f4b533db6431f1a0271a92d8f3f1c71e08833b481dcb2310d79ef8f`,
stock-return SHA-256 `10a7b949d1509ce627cb3c098c0a01a8ae5758fb2ce84b6c887e34b46e349387`,
52428800 bytes each. **The original candidate package does not contain this
new fix.** The existing readback comparator likewise recognizes the frozen
package pair, not the new decoded main. A future new package and its readback
references must be qualified together; do not mix their identities.

## What the native executor does on reentry

`scripts/epl9_job_reentry_probe.py` re-enters native executor `6074e6eb` at a
live film configuration checkpoint, using a cloned RAM/model snapshot. This
keeps the negative control from corrupting the outer run.

In six cases (two recipes, job kinds `200`, `100`, `40`), the second execution
reaches dispatch `6074e765` after 67 native instructions and selects the same
work callback `60751319`. Job cursor `+10388` remains 1. The native error field
`+10392` remains zero; it is not an acquired busy flag. The cursor advances
after the callback returns. Cancellation `+10394` is a separate mechanism.

These runs stop before duplicate work is invoked. An earlier exploratory run
went further and hit fixture slot-capacity/activation restrictions; those
restrictions are not a native lock. Neither run observes a real camera race.

The primary parent `607cf061` constructs the job via `6074df04`, stores it at
context `+156`, prepares it via `607ce6b8`, executes through `607ce5ae` and
cleans up via `607cefeb`. This local sequential path is compatible with single
ownership. It is not proof that every computed caller, task or interrupt
enforces exclusivity. No ad-hoc global lock, error-field lock or interrupt
disable was inserted into the stock executor.

## Private parameters fix the demonstrated COLOR overlap

`firmware_src/epl9_films_private_color.s.in` adds `film_private_entry`.
`build_late_module(..., private_color=True)` activates it; the default remains
the old generation and reproduces the exact frozen main bytes.

For either accepted recipe, or a transition out of a film curve already in the
output cache, the wrapper reserves 2048 stack bytes. It copies the 128-byte
context and 1876-byte request into that frame, redirects the private context's
request pointer, and calls the existing film routine with a normal 40-byte
native call frame. Temporary key 11, contrast and H/S/M changes then affect
only these private copies. Output/cache/owner references remain the original
ones. Ordinary unrelated modes take the stock path without this extra frame.

The underlying film code and tables are unchanged. The wrapper restores the
stack and preserves the return value; it adds no persistent allocation, global
mutable state, OS synchronization primitive or callback ownership change.
Compared with frozen v3, the selected path adds 2088 bytes of stack. The
metadata's complete extra-stack figure is 2176, including the existing
88-byte film frame. The MN103 emitter now supports signed 16-bit `ADD` to SP;
the existing imm8 encodings are unchanged. GNU disassembly independently
checks the emitted instructions against the candidate bytes.

The retained native runs cover:

- 40 configurations, each matching frozen v3's output and cache and the
  existing independent native expectations; nine warm-cache/exit transitions
  and 15 unrelated-mode passthrough controls also pass.
- 24 nested same-context COLOR calls: both recipes, four formats and three
  interruption checkpoints. At each checkpoint the caller's complete request
  and context remain unchanged. The inner 5200-byte configuration and resumed
  outer state match isolated execution. Stack restoration, adjacent guards
  and the writable shared main image pass their existing comparisons.
- Six connected jobs retain request restoration and reach exactly the prior
  unmapped TruePic register at `9880014c` (`6073eafa`). No output pixels,
  completion event or hardware success are manufactured.
- Four native producer/owner runs (two recipes, two owners), 24 owner controls
  and four pre-cancelled/destructor cases pass. Native event-2 matrix handling
  still agrees with the ISP configuration; complete requests are restored.

The observed native-owner job stack peak is 4336 bytes. Adding the previously
corrected primary task-31 prefix of 480 gives **4816 of 14080 bytes** for that
scoped path. The generic connected-job fixture peaks at 4356; it is a different
fixture, not a larger measured camera task. Enabled logging, interrupt frames,
other caller states, full-task high-water and physical stack behavior remain
unverified. An arbitrarily deep recursive job is not supported.

## A functioning logical read selector, and two rejected shortcuts

The new read-route probe executes byte-checked stock instructions and traps
the actual storage backend. It does not read a camera or synthesize read data.
The relevant chain is `604a0f03 -> 60439e72 -> 604014c6`.

| Selector | Observed behavior in the tested native fragment |
| --- | --- |
| `101` | Forwards logical source, destination and length; backend extra flag 1 |
| `103` | Same forwarding; backend extra flag 4 |
| `102`, `104`, `105`, `106` | Diagnostic stub for the checked input: returns zero without requesting a read |

The functioning selector preserves error `310d`; injected `3102` becomes
`3105`. Twenty-four cases cover both component addresses, 16 KiB and full
component sizes, both selectors and three backend statuses. Four non-reading
success controls prevent treating a zero return as acquired data.

The existing `oly fmem` read branch is not a ready export command. It takes
the destination from global `61f01124` without allocating or validating a
buffer there; three native fragment controls forward null and arbitrary
synthetic destinations. Separate debug code at `6043b934` allocates 16 KiB,
advances that global while printing and frees its original pointer at
`6043ba75` without clearing the advanced global. This is a potential stale
buffer issue in the static path, not an observed camera use-after-free.

The functional backend still connects to ordinary reader `604009bf`, whose
controller-result-dependent maintenance path can erase/program storage. Flag
4 has not been qualified as suppressing those operations. Thus neither the
CLI nor a selector name establishes a safe physical acquisition.

The [earlier USB audit](epl9-board-readout.md) also still applies: retail MTP
mode 4's admission filter excludes direct `9021 READ_DATA`. It admits the
diagnostic-shell operations, but their session gate must be opened first.
This pass narrows initialization helper `60f57363` to RAM flag handling; the
open handler additionally sends application message 2 to queue 98. The
receiver's complete effects remain unknown. A queue ID is not a task ID.
No diagnostic session was opened on hardware.

## Verification and restoration plan, with remaining boundary

The useful target is an **attributable logical-storage read** of each complete
decoded envelope: 26214400 bytes at main logical `406e0000` and OSD logical
`421e0000`. These are not CPU load addresses or raw NAND offsets. A proposed
16 KiB chunk size means 1600 chunks per component per pass; two separate passes
feed the existing comparator. Chunking is a plan, not a verified transport.

After a candidate install, both reads must match that exact candidate's main
and OSD envelopes and agree on repetition. After stock return, both must match
stock. This detects the known case where the updater hides an OSD error behind
a later successful main result. A version string, successful updater status,
visible icons or a running recipe alone cannot establish both complete writes.

Still needed before that physical check: a reachable qualified transport,
reviewed session-open effects, an owned bounded output buffer and a read route
whose maintenance behavior is understood. The downloaded stock pair covers
both changed components, but invoking it requires a working update entry.
The [existing installation/recovery assessment](epl9-installation-recovery.md)
is unchanged; return after arbitrary failure to boot is not demonstrated.
The new private-COLOR main also needs its own packaging/load/UI validation
before replacing the frozen installation candidate.

## Reproducible evidence

Ignored retained outputs:

- `local/epl9-v3-job-reentry-final-20261107/job-reentry.json`
- `local/epl9-v3-private-color-v2-20261107/private-color.json`
- `local/epl9-v3-private-owner-20261107/binding.json`
- `local/epl9-v3-readback-route-20261107/route.json` and native listings
- `local/epl9-v3-private-readback-seal-20261107/manifest.json`

The last manifest pins source/report hashes, confirms both frozen packages and
five recipe inputs, and checks the complete new main against the allowed
append-code/COLOR-target change. Read/updater and all other main bytes therefore
retain their old identities. Original evidence files are not rewritten.

Run the new probes with a **new** ignored output directory, using the project
Python and the pinned GNU reader. The private probe builds both generations:

```powershell
.\.venv\Scripts\python.exe scripts/epl9_private_color_probe.py --out local/new-private-check
.\.venv\Scripts\python.exe scripts/epl9_owner_binding_probe.py --private-color --rgb-tables local/epl9-native-film-curves-v3-20261107/native-rgb-tables.json --out local/new-private-owner-check
.\.venv\Scripts\python.exe scripts/epl9_job_reentry_probe.py --out local/new-job-reentry-check
.\.venv\Scripts\python.exe scripts/epl9_logical_read_route_probe.py --listings local/epl9-v3-readback-route-20261107 --out local/new-read-route-check.json
```

Seventeen targeted unit tests pass: four emitter, four RGB-input, three module
guard and six component-readback tests. Native probes, fixture controls and
byte identity checks qualify their stated software scopes only.
