# Native parameter owner: why its release is not yet our descriptor release

Source-only investigation, 2026-11-13, following PR18. Exact decoded E-PL9
1101 main SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`,
load base `60400020`. No firmware, frozen tables, SD hook or camera changed.

## New qualified fragments

The native owner uses **three parameter slots, each 4184 bytes**, beginning
at owner+2400. Its initialization at `6074b20b..6074b22c` zeros fields
+4/+12/**+20** in all three slots and changes no other owner bytes in the
fixture. This identifies an actual native initializer for the comparison
fields. It does **not** identify a producer of changing recipe generations.
The native parameter builder `6078ab39` still leaves +20 untouched.

The slot selector loop `6074b441..6074b474` rejects candidates equal to any
of owner+15408/+15412/+15416. All eight occupied-slot combinations were run:
first free slot wins; with all three held, no candidate is published. The
fixture executes the loop between, not including, the native exclusion calls
`60449006`/`60449010`. It establishes neither their concurrency semantics nor
a new lock usable by a recipe loader.

A separate **16-bit borrow counter at owner+15428** is incremented by
`6074b4da`, which returns the current pointer owner+15408. `6074b4eb`
decrements it. In the actual caller fragment:

1. `60763913..6076392d` finds the owner at job+3980.
2. `6076392d -> 6074b41f -> 6074b4da` borrows the parameter object.
3. `60763934` publishes it at **job+12320**.
4. The real caller invokes `60761b6a` at `60763943` (not executed in this probe).
5. `60763948..6076395b` releases the borrow and clears job+12320.

Both borrow and release wrappers are executed natively in the probe. The
intervening processing call is explicitly skipped, not modeled as successful.
The independent publication fragment `6074b497..6074b4c5` takes the wait
branch while the counter is nonzero. With zero counter, the replacement
branch moves the source pointer into owner+15408 and clears the source.
We stop before scheduler sleep/critical-section exit. This is a local
publication protocol, not whole-program last-reader evidence.

## Exact cache destruction alias

Job destructor fragment `6074e323..6074e327` loads **job+12316**, then calls
cache destructor `6073e57a`. The cache destructor returns for null; for nonnull
it forwards that exact pointer to allocator free `604023b2`. The probe stops
at that external call, with the cache itself deliberately not mapped.
There is no table walk in this cache destructor. This supports the ownership
shape, but does not prove every alias is gone or that every job reaches it
only after successful drain/cancellation.

## Consequence for SD/Delete

Do not confuse three lifetimes:

* parameter-owner borrowing protects publication of the native parameter slot;
* job-owned cache can retain gamma/HSL pointers beyond configuration setup;
* descriptor storage must remain live for all caches/readers referencing it.

The new owner borrow/release pair is therefore **not yet a safe eviction hook**
for the two-slot descriptor experiment. A new recipe revision also needs native
invalidation: PR18's comparator experiment showed pointer-only changes do not
set the table rebuild bit, whereas changing +20 does. The native initializer
now explains its zero starting value, not an authorization to overwrite it or
proof that a token alone refreshes every downstream stage.

Keep the session-owned descriptor arena in the experimental design. Next
narrow target is to connect job/cache destruction and every request alias to a
specific recipe lease, then trace native comparison-token writes beyond this
initializer. Do not solve it by changing the frozen candidate or inventing a
global busy flag. No global last consumer or finite-cache release hook has yet
been qualified.

## Reproduce

```sh
python scripts/epl9_parameter_owner_probe.py \
  --main /private/main.bin --reader /path/to/mn103-reader \
  --output local/parameter-owner-result.json
```

The probe verifies exact stock and reader provenance, decodes original
instructions at runtime, and emits scalar results only. Native bytes/listings
remain private local inputs. It has no camera, SD, firmware-write or OEM
redistribution operation.

## Connected invalidation follow-up: reuse the existing private-context route

The existing SD processing prototype already avoids changing parameter-owner
+20: `sd_pipeline_color` forces COLOR/tone rebuilding in its private context
(`flags | 0x10000002`), then installs selected HSL/gamma. Ordinary-mode exit
recognizes the previous recipe gamma and forces a stock rebuild. Thus finding
a native token increment is **not a prerequisite for that existing design**.
It remains relevant to a future optimization that skips redundant rebuilds.

`scripts/epl9_sd_late_transition_probe.py` now connects this actual authored
hook to the later native reader, rather than merely comparing configuration
bytes. Six transitions **T1, T1, T2, T2, stock, stock** each match independently
configured output through the late gamma, **tone** and HSL copies. Each late
copy executes 11,497 native instructions. Repeats match; T1/T2 differ; exit
matches the forced-stock oracle. The parameter owner is read-only in the
fixture and its token is untouched. No hook code was changed.

The fixture uses two deliberately synthetic embedded descriptors with a null
HLS-manager root, not the 31 artistic V6 recipes and not physical SD loading.
The optional config+3164 branch is excluded explicitly. The existing hook,
state module and one COLOR jump are built only as private interpreter inputs;
no installable image is created. No modeled image-completion success is used.

This closes a useful **bounded invalidation-to-late-copy** check for the
session-resident design. It does not close cross-job leases, SD reload, all
optional consumers, or native descriptor eviction. Session retention is still
required; a changing host generation is not a substitute.

```sh
python scripts/epl9_sd_late_transition_probe.py \
  --main /private/main.bin --reader /path/to/mn103-reader \
  --output local/sd-late-transitions
```
