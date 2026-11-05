# E-PL9: native ART producer binding and request-kind correction

## Outcome — 2026-11-05

Executing the stock parameter producers exposed a real integration defect:
they emit request kind **`0x1000`** for the declared ART operation, whereas the
film color, gamma and early-WB gates accepted only `0x0200`, `0x0100`, `0x0040`.
The old module bypassed Watercolor routing but skipped the recipe settings on
this input. All three gates now accept exactly `0x1000` as well; they still
require one of the two accepted ART identities. No mask-based type expansion
or change to unrelated mode keys was made.

Four connected native-producer cases now apply both recipes through the first
TruePic register boundary. Native continuation/cancellation and request-acceptance
handlers use the context actually copied by the constructor. Four pre-cancelled
cases return `0x9e01` without running a worklist entry, then release both modeled
job/cache allocations through the stock destructor. These are offline native-code
results under declared state, **not camera execution or successful pixel output**.

This extends the [previous owner/load validation](epl9-native-owner-load-validation.md).
The two recipe icons and unchanged example photographs retain the previously
accepted scope. Calibration and physical installation readiness remain open.

## Exact inputs and retained evidence

Olympus PEN E-PL9, owner-reported displayed body version **1.1**, downloaded
internal main build **1101**. This is not a dump of the installed camera.

| Input/artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Stock `OLY_E_133_1101_0000_0000.BIN` | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Decoded main | 26214336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |
| Corrected module at `604a1300` | 15360, including 2203 code bytes | `bf0883a46f5f1cae4a78c93f1a157974ef0a9dbf1811f9d9c1af1c864bb829cf` |
| Private decoded-main candidate | 26214336 | `29c6dceb4ecd14c0cf7ae5286aa595f48b9a548a2303986375d098fc34bb1585` |

Pinned reader SHA-256:
`e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae`.
All firmware, listings and run artifacts remain in ignored local directories:

- `local/epl9-owner-binding-v2-20261105/binding.json`: four negative comparisons
  using the preceding module (`b592a428...`). Routing was bypassed but
  `recipe_applied` was false and gains remained `[1024,1024,1024,1024]`.
- `local/epl9-owner-binding-v7-20261105/binding.json`: four successful-boundary
  cases, four native cancellation/destructor cases and 24 isolated control cases.
- `local/epl9-kind1000-integration-final-20261105/validation.json`: the expanded
  configuration, routing and flag grid.
- `local/epl9-kind1000-load-v2-20261105/load-sequence.json`: exact corrected
  candidate load and known startup interval comparisons.
- `local/epl9-job-regression-owner-kind-20261105/results.json`: the historical
  job, source-stride, negative-control and cleanup regression suite. The final
  candidate is byte-identical to the copy used by the load test above.

## Stock parameter production and constructor binding

| Producer | Callback installed in parameters +0 | Context installed at +4 |
| --- | --- | --- |
| `607ce515` | `607cfe8d` | Original producer owner argument |
| `607d0b25` | `607d16c7` | Original producer owner argument |

The stock producer calls, ART-header selection and disabled-output logging
execute without modeled calls. Declared inputs are operation `context+72 =
0x1003`, selector `+164 = 1`, `+272 = 0`, property byte `+22955 = 120`, variant
`+23688 = 1/2`, and zero values for the other selected options. The property
object is a bounded synthetic allocation; it is not a captured camera object.

The producer's kind helper `607d25a7` emits `0x1000` for this operation. Header
bytes are `01 01 78 00` / `01 02 78 00`, while parameter halfword `+16` is
`0x1000`. Native constructor `6074df04` copies the 32-byte parameter record to
job `+4`; callback/context therefore reach job `+4/+8` without replacement.
Cached ART identity remains `0x01010078` / `0x01020078`.

The corresponding native caller fragment invokes producer `607ce515` at
`607cf090`, constructor `6074df04` at `607cf09a`, then stores the job at owner
`+156`. That fragment is static evidence; the connected probe supplies the
returned parameter record to the constructor, rather than executing the entire
camera worker and its property acquisition.

`0x1000` is a request kind, **not a pixel layout**. These connected cases declare
source descriptor format `0x0200`, which reaches request `+28`; request `+14`
remains `0x1000`. Actual capture source provenance/packing is not established.
The general job probe accepts this new kind only with an explicit immutable
32-byte parameter fixture matching key, kind, selector and nonzero owner fields.

## Native control and matrix callbacks

The outer emulator has an explicit adapter at the constructor-bound callback.
For events **2, 13 and 21**, it executes the intact stock handler in a child
instruction map sharing RAM, registers and the actual context. The context is
not rewritten for these events; no function inside the handler is modeled.
Other resource events retain the existing finite host-buffer contracts and
are explicitly labeled as adapters. This is not a fully native owner lifecycle.

Both owners give the following results with logging output disabled and declared
RTOS state:

- Event 2 retains the nine coefficients passed to the ISP and copies twice their
  halfword values to owner properties `+4114..4130`, preserving other bytes.
- Event 13 reads cancellation state. State exactly 1 clears owner readiness
  `+195`; the returned readiness then causes native executor cancellation.
- Event 21 returns readiness without clearing it. A cancellation state alone
  does not make this handler return zero until the readiness state changes.
- Event 31 also returns readiness in these owners. Its 0/1 cases are isolated
  native callback checks, not a newly exercised connected event-31 route.

The isolated grid has 24 cases: two owners, three control events, readiness
0/1 and cancellation 0/1. Full context/object comparisons and balanced returns
are required. Connected successful cases execute three native event-13 calls,
one event 21 and one event 2 each. The native callback paths do not reenter
executor or color processing in these tested states.

For both recipes and both owners, pre-cancellation produces exactly one native
event-13 return of zero. The executor returns `0x9e01`, marks cancellation,
leaves the pending record empty and never reads source pixels or invokes a
worklist entry. The stock destructor then releases JOB and CACHE through the
existing bounded allocator contracts. Supporting that path required loading
the previously absent native cleanup window **`60752f56..60753040`**. Its effect
slots are empty in these runs; nonzero effect-object destructors, in-flight
hardware cancellation and normal completed-image teardown are not covered.

## Recipe data, stack and regression scope

On the successful boundary cases, an input gain record `[1024,1024,1024,1024]`
becomes Gold `[1106,901,1024,1024]` or Portra `[1060,963,1024,1024]`. The independent
curves and diagnostic matrix/six-axis settings are selected, owner and ISP
matrices agree, and all **1876 request bytes** are restored after the late hook.
The original ART job identity remains unchanged. Maximum observed stack depth
for these cases is **2248 bytes**; this is not a bound for concurrent tasks,
interrupts or all camera callers.

Expanded integration checks cover 40 frame configurations, 24 attached-object
crosschecks, 9 cache transitions, 15 passthrough/qualification cases, 36 matrix
boundary cases, 275 gain boundary cases, 12 historical connected jobs,
120 routing cases and 1050 flag cases. All 141 selected unit tests pass,
including fixture rejection and request-kind/source-format separation.
The standalone job regression also passes: 12 baseline jobs, 8 attached-color
cases, 4 owner-slot cases, 8 short-input cases, 4 destruction cases, 8 stride
cases, 2 invalid-offset controls and 10 other controls, plus its cache and
owned/borrowed-buffer audits. Expected hardware/unmodeled-resource stops in
that suite remain expected stops, not completed images.

The first broader run stopped because the shared synthetic request factory
still rejected `0x1000`; that fixture guard was updated only for this exact
native-produced kind. The first new cancellation teardown stopped at absent
code `60752f56`; it was resolved by executing the stock function, not a successful
return model. These failures are distinct from the corrected emitted gate bug.

The new module remains in the same early-load interval. The corrected candidate
matches all three native planned read chunks; destination guards and module
bytes remain intact. Known subsequent startup reads/initialization/section
intervals do not overlap it. Physical storage/cache behavior and all runtime
writers remain unverified.

## Remaining boundary and reproduction

The four positive jobs stop at native `6073eafa`, the first unmapped TruePic
write to `9880014c`. They produce no changed output pixels and no completion
signal. Values for matrix, six-axis and RGB curves remain diagnostic; WB/HSL/tone
are recipe trials, not fitted Kodak or Fuji-equivalent outputs. Actual source
buffers, the secondary owner's creator binding, remaining resource callbacks,
same-job concurrency and physical code-slot lifetime still need qualification.
No camera, updater or firmware container was used or produced by this pass.

```powershell
.\.venv\Scripts\python.exe scripts/epl9_owner_binding_probe.py --out local/new-owner-binding --color-controls local/epl9-color-controls-diagnostic-20261104.json
.\.venv\Scripts\python.exe scripts/epl9_film_late_probe.py --out local/new-kind-integration --base 0x604a1300 --diagnostic-rgb --color-controls local/epl9-color-controls-diagnostic-20261104.json --wb-controls recipes/epl9-native-wb-trial-v1.json
.\.venv\Scripts\python.exe scripts/epl9_load_sequence_probe.py --candidate-main local/new-kind-integration/main-with-module-OFFLINE-ONLY.decoded.bin --out local/new-kind-load
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_epl9_native_owner_parameters.py -v
```
