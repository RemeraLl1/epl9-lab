# E-PL9: native matrix owners and early load sequence

## Outcome — 2026-11-05

The Gold 200 / Portra 400 integration now has **18 connected checks with three
stock event-2 owner handlers**, including their native readiness, state lookup,
logging gates and returns. These replace the previous coefficient-copy-only
tests for the selected states. No function inside these callbacks is replaced
by a successful host return. The connected job still uses the existing explicit
host resource contracts and inferred WB arithmetic outside the callbacks.

The early reader's native alignment/chunk arithmetic also reproduces the entire
657408-byte load containing the module. Known subsequent startup loads, two
initialization ranges and the previously resolved section intervals do not
overlap its slot. Physical reads, cache behavior and all runtime writers remain
unverified. This is further offline qualification, **not installation readiness**.

The emitted integration code remains byte-identical to the
[preceding candidate](epl9-wb-math-placement.md). Recipe calibration, icons and
the accepted stock example photographs are unchanged by these validation tools.

## Exact inputs and retained runs

Olympus E-PL9, owner-reported displayed body version **1.1**, downloaded main
build **1101**; not an installed-camera dump.

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| Stock package `OLY_E_133_1101_0000_0000.BIN` | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Decoded main | 26214336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |
| Candidate module at `604a1300` | 15360 (2179 code) | `b592a42857ea8e45dd1eff98e6a6adad1e5be08dc72dbcf027dc2fa394020df6` |
| Private decoded-main candidate | 26214336 | `a3fea34f7d147ef8d83f4055dd81ae26a793e7cccb1fd747d1150bc09910b1c2` |

Pinned reader SHA-256:
`e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae`.

Runs began November 4; their existing local directory names are retained:

- `local/epl9-owner-native-final-20261104/owners.json`: 24 native state cases,
  three boundary/skip controls and 18 connected jobs; fresh owner listings.
- `local/epl9-load-sequence-final-20261104/load-sequence.json`: native read
  chunks, startup destination intervals, exact byte comparisons and source hashes.

All firmware, listings and detailed run data remain in ignored directories.
No camera or updater was accessed, and no update container was generated.

## Native owner coverage

| Handler | Verified event-2 behavior under declared state |
| --- | --- |
| `607cfe8d` | Native dispatch uses table `6090b550`, event index minus 2. A nonzero context `+195` enters `607d0aa7`; context `+24 == 16` permits the matrix copy. Return is context `+195`. |
| `607d16c7` | Logs and delegates to `607cfe92` with the correct native frame. Event 2 has the same copy/return behavior; its event-16-only branch is not taken. |
| `609a836f` | Requires a nonzero argument/context/handle, obtains the owner through `609a9390 -> 6068758f`, then copies the matrix. Its final cancellation check can clear context `+8` and change the return; this does not undo the copy. |

The matrix copy doubles each of the nine supplied halfwords into owner-object
offsets `4114..4130`, using native halfword arithmetic. Full object comparison
checks that other bytes remain unchanged. The source coefficient span stays
unchanged. Phase values 15/16, readiness values 0/1 and cancellation values 0/1
are varied for each of the three handlers (24 cases).

The secondary handler does **not** use the primary handler's phase/readiness
gate for copying. Its readiness byte contributes to the eventual return value.
A zero handle skips the copy and returns through native code; an inactive
registry entry stops at undeclared diagnostic call `605f9d64`. Enabling external
secondary log output stops at undeclared formatting call `609a608e`. These
stops are preserved rather than acknowledged as success.

### Logging and task-state assumptions

Primary logging executes `607cc266 -> 607cc3c8 -> 604117be`. The last routine
reads the declared processor index, current task links and task number 31.
The declared primary log mask is zero, so native code returns through its
disabled-output path. The task links are synthetic data, not a measured RTOS
snapshot or an emulated scheduler.

Secondary logging executes `609a5e9f -> 609a5fb1`. External output flags are
declared disabled, but its internal 1208-byte diagnostic ring is present and
the **native code actually updates it**. State lookup executes against a
declared active registry entry for handle 1 and a bounded owner object. Logging
is therefore neither omitted nor replaced with a no-op.

### Connected integration and reentry limits

The connected test uses a host adapter at its existing owner boundary to bind
event 2 to each selected stock handler and the declared context. This adapter
is not emitted into firmware and does not establish the real creator-to-owner
binding. Other events retain their previously declared fixture contracts.

Both film slots and request kinds `0200`, `0100`, `0040` pass with all three
owners (18 jobs). Each job checks:

- the owner saves the same coefficients that reach the final ISP configuration;
- all 1876 request bytes are restored on color return;
- the callback returns with a balanced stack, with no modeled calls inside it;
- neither executor `6074e6eb` nor color entry `6079fb88` is reentered from that
  callback in the tested state;
- execution reaches the declared TruePic write boundary `6073eafa`, with no
  changed output pixels or fabricated completion event.

Recorded callback call targets are limited to the native logging/lookup/copy
functions above. Peak observed job stack remains **2268 bytes**; the preceding
task-31 path accounting remains **2660 of 14080 bytes** for this scoped path.
This does not measure interrupt stack use, enabled external logging, other
callbacks, all caller stacks or concurrent task access to the same job.

## Native load chunks and competing startup ranges

The native fragment `60401561..6040168b` plans the early read as follows:

| Storage source | Uncached destination | Bytes |
| --- | --- | ---: |
| `406f0000` | `a0410000` | 65536 |
| `40700000` | `a0420000` | 524288 |
| `40780000` | `a04a0000` | 67584 |

The selected module interval `604a1300..604a4f00` is entirely within the third
chunk after alias conversion. The low read leaves `604009bf` and `60400d2f`
receive explicit successful local-storage models: they copy exact bytes from
the identified private candidate and validate ABI, alignment, source bounds
and destination bounds. Native NAND/DMA operations are not executed.

All 657408 destination bytes match the candidate slice; both destination guards
remain intact. Argument-building instructions for the other five early reads
execute separately and show no overlap with the module. The two initialization
arguments are `62419900..6242c7a4` and `629fc800..62b21288`, also disjoint.
Nine known later section intervals from the existing deployment audit are
checked for overlap; that section loader is not newly executed here.

Three synthetic unit tests exercise correct source-offset copying, unchanged
guards, rejection of invalid/unaligned/truncated requests and rejection of the
wrong call ABI. They pass. Neither the successful local read nor these interval
checks establishes runtime heap/overlay exclusion or cache execution behavior.

## Next boundary

The selected event-2 branches now have stronger native execution coverage.
Remaining integration work includes actual owner bindings and other event
paths, concurrent/interrupt behavior, runtime ownership/cache qualification of
the code slot and hardware qualification of the inferred WB leaves. TruePic
pixel output and photographic fitting remain separate unfinished requirements.
The separate installation/recovery investigation is not replaced by these tests.

```powershell
.\.venv\Scripts\python.exe scripts/epl9_owner_callback_probe.py --out local/new-native-owners --color-controls local/epl9-color-controls-diagnostic-20261104.json
.\.venv\Scripts\python.exe scripts/epl9_load_sequence_probe.py --candidate-main local/epl9-integration-placement-final-20261104/main-with-module-OFFLINE-ONLY.decoded.bin --out local/new-load-sequence
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_epl9_load_sequence_probe.py -v
```
