# E-PL9: WB math, early-load placement and callback consistency

## Outcome — 2026-11-04 follow-up

The two replacement slots now run in the offline model at **`604a1300`**, inside
a traced early-main load. The previous WB stop is traversed with explicit,
inferred scalar-float contracts while executing the stock power/log/exp bodies.
An independent numeric comparison checks that interpretation. This does **not**
establish the camera CPU's undocumented instruction semantics.

The synchronization investigation found and fixed a concrete inconsistency:
the owner callback could receive the original matrix while the final ISP output
received our later adjustment. The adjustment now precedes the stock callback
and native matrix packing. It does not add or suppress owner notifications.

No camera, SD card or updater was accessed. No update container was produced.
Gold/Portra photographic calibration and hardware pixels remain unfinished.
The existing G200/P400 icon copy and unchanged example photographs from the
[previous pass](epl9-film-deployment-color.md) remain the accepted UI scope.

## Exact input and final local artifacts

Olympus E-PL9, displayed body **1.1** reported by the owner; downloaded main
build **1101**, not an installed-camera dump. Stock package: 104552480 bytes,
SHA-256 `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`.
Decoded main: 26214336 bytes,
SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
The existing pinned GNU reader validates emitted code; its identity remains
`e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae`.

Final diagnostic configuration, with early gain bias, matrix/six-axis inputs
and distinct RGB test curves:

| Artifact | Size / identity |
| --- | --- |
| Native module | 2179 code bytes, 15360 total bytes; base `604a1300` |
| Module SHA-256 | `b592a42857ea8e45dd1eff98e6a6adad1e5be08dc72dbcf027dc2fa394020df6` |
| Private decoded-main copy SHA-256 | `a3fea34f7d147ef8d83f4055dd81ae26a793e7cccb1fd747d1150bc09910b1c2` |
| Full configuration/grid results | `local/epl9-integration-placement-final-20261104/validation.json` |
| Native load-argument and byte-identity check | `local/epl9-placement-final-audit-20261104/placement.json` |
| Wider WB math cases | `local/epl9-wb-math-final-20261104/math-contract.json` |
| Callback, restoration and stack results | `local/epl9-lifecycle-owner-final-20261104/lifecycle.json` |

The decoded-main copy is explicitly named `main-with-module-OFFLINE-ONLY.decoded.bin`.
Its complete byte sequence is reconstructed from stock plus the declared module
and five hook replacements; unrelated modifications cause the placement audit
to fail. Original firmware files remain unchanged and all binary artifacts are
ignored by Git.

## WB branch: what the math now establishes

At `607a46cc..607a470b`, the selected branch converts a bounded integer
difference, divides by the IEEE-shaped constant `43800000` (256), computes a
power with base `40000000` (2), multiplies by a converted coefficient and
converts the result back to an integer. The following native code shifts by
four and applies its byte limit. This is a parameter-interpolation branch,
not a new film algorithm.

Short wrapper addresses and the inferred operations are:

| Wrapper | Inferred operation |
| --- | --- |
| `604bbbeb`, `604bbbf4`, `604bbc33` | Signed 32 / unsigned 16 / unsigned 32 to scalar float |
| `604bbaba`, `604bbac1` | Scalar float to signed integer / low unsigned halfword |
| `604bbb1d`, `604bbb16` | Addition / subtraction |
| `604bbb42`, `604bbb30` | Multiplication / division |
| `604bbb24`, `604bbb29` | Comparison / comparison with zero |
| `604bbb37` | Sign change |

The generic reader labels `f9 e0 40` and `fb e0 80 00` as AM33 floating-register
instructions. That interpretation does not explain these wrappers' D0/D1 ABI.
The pinned GNU opcode table also assigns overlapping encodings to user-defined
instructions; generic labels alone do not identify this camera's extensions.
The scalar contracts above are inferred from the exact firmware callers,
wrapper bodies and bit-pattern constants, not borrowed E-P7/PEN-F opcodes.

`epl9_float_contract.py` supplies **opt-in function-boundary models**, with an
explicit inferred-contract flag in every logged call. It does not change the
shared instruction interpreter or install a float opcode implementation.
Finite normal values use rational arithmetic with round-to-nearest-even at
binary32 boundaries; exceptional/subnormal inputs and out-of-range conversions
fail. Hardware rounding, exceptional behavior, signed-zero corner cases and
all PSW effects remain unqualified.

The stock body at **`604b860e`**, including its native logarithm/exponential
calculation, executes as instructions. There is no host `pow()` replacement.
For 129 exponents from -4 through +4 in steps of 1/16, base 2 results differ
from an independent 80-digit Decimal reference rounded to binary32 by at most
**2 ULP**. The resulting 36 job cases cover both slots, three request kinds,
two selectors and three coefficient records, including both previously blocked
records. They all reach the existing first TruePic write. This supports the
functional interpretation under the declared contracts; it does not prove the
hardware leaves or complete the pixel pipeline.

## Placement in an actual declared load

Earlier analysis considered only the later section loader. Early startup has
another read: native `604001a4..604001cb` requests
`406f0000 -> a0410000`, length **`a0800`** (657408 bytes), through `604014c6`.
The cached destination interval is `60410000..604b0800`.

The selected module interval **`604a1300..604a4f00`** fits wholly inside that
read and the original FF run `604a1300..604a8000`. The audit executes the native
argument-building instructions and compares the module bytes against the
corresponding slice of a modeled storage read. No loader endpoint, file length
or section-table entry needs to change.

The builder accepts this one reviewed in-main slot only, verifies its exact
stock FF content, and rejects any other overlapping placement. The interpreter
maps it once as part of the private main image. The independent original-code
oracle receives only the same private table bytes; its original hook sites
remain unmodified. All emitted calls/branches are freshly checked at the new
base by the pinned reader.

No direct FC-form 32-bit reference to the candidate or its uncached alias was
found. This is a bounded reference check, not an exclusion of computed pointers,
runtime overlays or every instruction/data encoding. Physical storage loading,
cache/execution attributes and runtime ownership of the interval remain to be
qualified. The large un-loaded tail remains unsuitable as previously described.

## Fix: one matrix for the owner and ISP

The stock matrix helper normalizes nine halfwords at `6079bedb`, calls owner
event 2 at `6079c026`, and then packs those same words. The previous late output
overlay changed only the packed ISP copy. That could leave the owner's saved
representation inconsistent.

The new fifth hook replaces the five-byte call at **`6079c017`**. It replays
that normalization call with its original save mask/frame, then changes its
local 18-byte matrix **before** event 2. Qualification checks the native caller
return `6079fbc6`, our outer return identity, the exact stack-owned control
pointer, magic and accepted recipe key. It adds no stack allocation, uses no
global recipe state, retains the original bounded/atomic overflow rule, and
resumes at `6079c01c`. The old post-callback matrix overlay is removed; six-axis
packing remains at the late site.

The connected runner now requires the owner-notified words to equal the final
ISP matrix for every checked job. Two selected native callback tails were also
executed: `607d0acf..607d0b22` and `609a83c5..609a841e` copy nine supplied words,
scaled by two, to owner state `+4114..+4130`, leaving other bytes unchanged.
These fragment tests start after readiness gates, logging and state acquisition;
the full callbacks have not been executed.

## Stack and synchronization: stronger evidence, remaining limits

The widened WB cases retain a measured peak of **2268 bytes** from the explicit
job entry. Task descriptor 31 at table `60418cc4` declares entry `607ce1b5` and
**14080 bytes** of stack. Its verified path to `607ce63f -> 6074e6eb` adds 16
bytes of saved registers, 356 local bytes and a 20-byte child frame. The executor
frame is already included in the measurement. Thus this scoped configuration
path totals **2660 bytes**. This is not a whole-task worst case, an interrupt
budget, or proof for every other executor caller.

The lifecycle observer compares all **1876 request bytes** at color entry and
return. Six connected cases restore the whole request before owner event 4,
the modeled ISP-lock acquisition and native hardware start. Its declared
request is the embedded job `+10440`; tables are permanently read-only in the
placed module.

**Correction to the broad notification wording:** event 2 happens during the
temporary configuration. It first passes through request callback `607504f6`,
then the job's owner callback; the two observed dispatcher events are forwarding
of the same matrix notification, not two separate matrices. Those callbacks
must remain. Ordinary event 4 and hardware start follow restoration, but this
does not prove that all owner callbacks are non-reentrant or cannot yield.
Same-job concurrent entry, every owner implementation, IRQ behavior and the
complete pending-request lifecycle remain unqualified. No new global lock or
interrupt-disable workaround has been introduced.

## Verification and continuation

The relocated code passes the existing 32 frame cases, 24 original-key pairs,
9 warm/exit frames, 12 passthrough cases, 120 whole-job routes, 1050 effect-flag
cases, 36 matrix-boundary cases, 220 early-gain cases and 12 connected jobs.
The wider arithmetic run adds 36 connected cases and 129 independent power
comparisons. Six lifecycle cases and two owner-copy tails pass. The workspace
suite passes **225 tests**.

Readiness remains **offline candidate, not install-qualified**. Concrete next
work is owner callback/reentrancy coverage across the remaining callers,
qualification of the inferred scalar leaves and runtime placement attributes,
then the agreed hardware validation and photographic fitting. The installer
and recovery decisions made in the separate investigation are retained; this
pass neither changes them nor establishes a new recovery mechanism.

```powershell
.\.venv\Scripts\python.exe scripts/epl9_film_late_probe.py --out local/new-placed-film --base 0x604a1300 --diagnostic-rgb --color-controls local/epl9-color-controls-diagnostic-20261104.json --wb-controls recipes/epl9-native-wb-trial-v1.json
.\.venv\Scripts\python.exe scripts/epl9_placement_probe.py --candidate-main local/new-placed-film/main-with-module-OFFLINE-ONLY.decoded.bin --out local/new-load-check
.\.venv\Scripts\python.exe scripts/epl9_wb_math_probe.py --out local/new-wb-math --base 0x604a1300 --color-controls local/epl9-color-controls-diagnostic-20261104.json
.\.venv\Scripts\python.exe scripts/epl9_lifecycle_probe.py --out local/new-lifecycle --color-controls local/epl9-color-controls-diagnostic-20261104.json
```
