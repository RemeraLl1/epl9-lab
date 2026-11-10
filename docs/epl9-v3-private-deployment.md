# E-PL9 v3: packaged private-COLOR candidate and read-service follow-up

2026-11-07. The private-COLOR variant now has its own checked load/UI evidence,
encoded main+OSD package and generation-specific readback references. Gold 200
v3 and Portra 400 v3 are unchanged. The stock-restoration package remains
byte-identical to the original two-component stock selection.

This completes the **offline load, UI, packaging and comparison stages** for
the new variant. No camera command, card preparation, physical write, physical
readback or recovery was performed. `install_ready` remains false. The previous
[private-COLOR report](epl9-v3-private-color-readback.md) retains the native
reentry/owner evidence and stack limits; its statement that packaging was
pending describes that earlier pass.

## Exact files

Olympus E-PL9 / IM008 / model 1330, body 1.1 reported by the owner, downloaded
main build 1101. The stock source is not a dump of the installed camera:
`firmware/OLY_E_133_1101_0000_0000.BIN`, 104552480 bytes, SHA-256
`aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`.

New output directory: `local/epl9-v3-private-packages-20261107/`.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `Gold-Portra-v3-private-color-candidate.bin` | 52428800 | `230c4853b41d069da2a4fb22ace1eb043b28b71c9fa5b634cdc8baa037170256` |
| `Stock-1101-main-osd-restore.bin` | 52428800 | `10a7b949d1509ce627cb3c098c0a01a8ae5758fb2ce84b6c887e34b46e349387` |

These are research filenames, not qualified SD-loader names. The frozen
earlier package directory is preserved. Both generations use the same OSD
and recipes; their main code and encoded candidate hashes differ.

Decoded component identities, each 26214336 bytes:

| Component | SHA-256 |
| --- | --- |
| New private-COLOR main | `72cc1e48e6b42ab02b9911bdb841fe2c5b0cb34f2c08893f6b78be8a6871beee` |
| Unchanged icon OSD | `50141904c211fd16bc4c26b35cd52955f96a9e611ca062d84fe0169eeda21b3b` |
| Stock main | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |
| Stock OSD | `ee9a9c3ad1974dd212483ca7d012e51ae23083ce0119589a3b42996aa13ccf1e` |

## Completed checks for this exact generation

`scripts/epl9_private_integration.py` joins the sealed native/owner results
with new load and UI results, requiring the same candidate hash throughout.
It verifies the actual patched main/resource hashes recorded by OM-Emu, not
only the overlay filename. The baseline and candidate use the same runner,
Node version and pinned upstream commit.

- **Load:** native planning copies all 657408 early-load bytes, including the
  full module, in the same three declared read chunks. Exact bytes and guards
  match; known later load/initialization ranges do not overlap the module.
  Physical NAND/cache and all runtime writers remain outside this test.
- **UI:** 41 frames match the icons-only reference pixel-for-pixel. GUI states,
  actions and the complete stock diagnostic history agree. Ten frames differ
  from stock only in the accepted icon areas; six resources are observed.
  The other four resources and the ART-dial compositor gap remain as previously
  documented. The labels still say Watercolor I/II; the badges show G200/P400.
  Large example pictures remain stock. Processing-hook counters stay zero on
  this UI route; it is not a TruePic image test.
- **Package:** exact main `0100` and OSD `0101`, unchanged metadata, lengths and
  destinations, and repaired checksums. Fifteen declared spans contain all
  23297 changed decoded bytes. Seventeen audited updater/startup ranges match
  stock. All five frozen recipe inputs match the earlier package manifest.
  The independent pinned upstream parser reconstructs stock, candidate and
  restore exactly. These use full-component writes, not a small delta update.
- **Native validator:** 16 full-size cases and ten native/bulk-loop crosschecks
  pass. For stock return, the executing modified main is now extracted from
  the exact tested candidate package, preventing an old-generation main from
  being substituted. Writes stop at the declared trap. The existing OSD-first
  order and earlier-error masking are unchanged.
- **Readback comparator:** 16 full-size controls pass and decoded envelopes
  match native writer-boundary hashes. The extra two controls reject old v3
  as private-COLOR and private-COLOR as old v3. Mixed installs, corruption,
  unstable repeated reads, swapped/truncated data and encoded inputs remain
  rejected. These controls use local synthetic data, not camera acquisitions.

Twenty-one targeted unit tests pass (7 packaging, 7 readback, 3 load-boundary,
4 overlay). Changed Python sources compile and Git whitespace checks pass.

`--generation private-color-v3` explicitly selects the new build and readback
references. The default `frozen-v3` retains the earlier generation. Unknown
generations are rejected; neither path accepts arbitrary replacement hashes.

## Deeper read-path result: errors are lost below the selector

The preceding selector audit trapped `604014c6`. It correctly established
that its caller preserves an injected `310d` and maps another nonzero result
to `3105`. This follow-up executes **inside** `604014c6`, extending that scope.

`scripts/epl9_read_backend_probe.py` runs 24 cases: two logical components,
selectors `101`/`103`, lengths 16 KiB/full component and injected leaf results
0, 1, `310d`. Page/bulk reads, entry/exit helpers and the clock are explicitly
modeled boundaries; no data is supplied by the read model.

All 16 nonzero leaf results are overwritten: after its read calls and timing
bookkeeping, native `604016bf` clears d0 and `604016c0` returns zero. Thus the
outer selector's error mapping cannot recover those discarded results. This
is native control flow under error injection, not an observed camera failure.

For aligned 16 KiB chunks both selector flags use `604009bf`. Full envelopes
use `60400d2f` followed by a zero-length `604009bf` call. Both flags produce
identical leaf-call sequences in these cases. Flag 4 therefore does not avoid
the ordinary reader on the proposed chunked export. The previously identified
controller-dependent maintenance erase/program route remains reachable in
that reader. Neither flag is qualified as a general no-maintenance read mode.

Consequences: a zero read status is insufficient, including from the working
selector. Comparison must require actual, independently acquired bytes and
repeat agreement. A qualified transport and owned, bounded buffer are still
required. The known CLI global-buffer problem is unchanged.

## Diagnostic session: receiver and command identity resolved

The earlier note called the stack word 2 an application message. The native
queue envelope now resolves its role more precisely: **2 is a payload word;
the dispatch command is 0 for open and 1 for close.**

The generic wrapper `60434a21` puts the caller's d1 into packet `+8` and its
payload pointer into `+12`, then sends the 16-byte envelope. The open/close
handlers supply the queue ID at `6042102a`, equal to 98.

Exact E-PL9 name/descriptor tables identify:

| Receiver | Queue | Task | Native task entry |
| --- | ---: | ---: | --- |
| TAKE_FUNC | 98 | 115 | `605f9168` |
| TAKE_FUNC_CP | 99 | 116 | `605f94a7` |

The first task receives through `605f9e3c -> 604313e9`. Its dispatcher uses
packet `+8` and table `60600c00`, selecting `605f92d4` for command 0 and
`60678d88` for command 1. Passing the word 2 as the command would instead
select an unrelated error-return handler (`60678d7e`). Queue and task IDs
must not be interchanged.

Open sets a TAKE_FUNC context bit and forwards the envelope to TAKE_FUNC_CP
through the queue ID at `6042102c`. The second task uses the hash table at
`60600d00`: command 0 reaches `605f9604`; command 1 reaches `6067d52c`.
Under the explicit idle-state fixture, payload 2 moves RAM state `62615588`
from 0 to 4 and calls initializer `605f96c0` with d0=0. Closing from that state
resets it to 0 and calls teardown `6067d641` with d0=0.

Thirteen native fragment controls verify packet construction, task receive
arguments, both dispatch tables, forwarding and these state transitions.
They stop before queue I/O, handler calls or initialization as declared in
each case. They do not simulate a successful physical diagnostic session.

The initializer immediately includes `606817fa`, then proceeds to allocation,
additional module messages and completion waits. Teardown also dispatches
module work. Their complete effects, receiver state and synchronization remain
unqualified. The session is therefore not established as a harmless RAM gate
toggle. The retail-MTP filter still excludes direct `9021 READ_DATA`; no new
physical export is enabled merely by locating these routines.

## Remaining stages

The new encoded pair, native validation and comparison references are now
consistent. The remaining acquisition work is concrete: finish qualifying
the diagnostic initialization/teardown and downstream messages, establish an
owned export buffer/transport, and resolve read maintenance/error behavior.
The existing entry/recovery assessment is unchanged. The stock pair is
verified as a file and through native validation, not as an observed physical
return after installation or after failure to boot.

Same-job executor exclusion, physical code-slot/cache lifetime, untested
caller/IRQ states and real TruePic output remain scoped as in the earlier
reports. The private-copy fix does not claim a whole-job lock. Camera image
tests remain a later stage; the emulator is not required to invent them.

## Retained evidence and reproduction

- `local/epl9-v3-private-load-20261107/load-sequence.json`
- `local/epl9-v3-private-ui-20261107/session.json`
- `local/epl9-v3-private-integration-20261107/manifest.json` and `ui-comparison.json`
- `local/epl9-v3-private-packages-20261107/manifest.json` and `qualification.json`
- `local/epl9-v3-private-package-native-20261107/validation.json`
- `local/epl9-v3-private-readback-controls-20261107/readback-controls.json`
- `local/epl9-v3-readback-service-20261107/backend-results.json`,
  `session-results.json`, byte-checked native listings and final `manifest.json`

The final manifests pin evidence/source hashes, recheck unchanged recipe and
old-package identities, and retain the explicit remaining limitations. Raw
reference windows are exploratory cross-reference candidates, not a complete
call graph. Native probes verify the actual fragments used for conclusions.

After reproducing load/UI/integration evidence, use new ignored output paths:

```powershell
.\.venv\Scripts\python.exe scripts/epl9_v3_package.py --generation private-color-v3 --out local/new-private-packages
.\.venv\Scripts\python.exe scripts/epl9_package_native_probe.py --packages local/new-private-packages --out local/new-private-native
.\.venv\Scripts\python.exe scripts/epl9_read_backend_probe.py --out local/new-read-backend.json
.\.venv\Scripts\python.exe scripts/epl9_diagnostic_session_probe.py --out local/new-session-route.json
```

For **future qualified acquisitions only**, `epl9_component_readback.py` accepts
`--generation private-color-v3 --expected v3` or `--expected stock` plus both
component files and their separate repeats. It performs no acquisition or
camera operation and never certifies provenance from a file match alone.
