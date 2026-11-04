# E-PL9: MULQIU resolution and first native film module

The later [late native integration](epl9-late-film-integration.md) supersedes this page's early owner attachment and commit/prepare strategy. This page retains the original instruction investigation and module experiment; its unresolved early-owner binding is not the current implementation approach.

## Outcome, 2026-11-04

The active-H/S/M instruction boundary is resolved from Panasonic's instruction specification. The complete color-configuration chain now returns with active controls for both accepted slots. An **original native machine-code module** has also been emitted and executed with the exact downloaded E-PL9 code, replacing the former Python interventions for routing, job key handoff, recipe parameter preparation and three-pointer gamma selection.

This is an **integration module**, not an installable firmware or calibrated film simulation. Actual owner call sites, buffer ownership/synchronization and executable placement are not yet bound on the camera. The two embedded recipe directions use the existing v0 HSL and v2 tone biases. Default RGB contents remain stock; native WB bias and a new color matrix are not implemented. No new photographic result or hardware pixel completion is claimed.

Source: [epl9_films.s.in](../firmware_src/epl9_films.s.in). Build: [epl9_film_module.py](../scripts/epl9_film_module.py). Native validation: [epl9_film_module_probe.py](../scripts/epl9_film_module_probe.py).

## Exact inputs and emitted artifact

Olympus E-PL9, owner-reported displayed body **1.1**, downloaded build **1101**, not a dump of the installed body. Stock container identity carried from the previous audit: `OLY_E_133_1101_0000_0000.BIN`, **104552480 bytes**, SHA-256 `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`.

The emitter and probe read the decoded main: **26214336 bytes**, SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`, base **`0x60400020`**. Reader SHA-256: `e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae`.

Validated default module: **760 code bytes**, **15360 total bytes** including two HSL tables, six stock curve copies and alignment/padding. Module SHA-256: `a1d44e99cbadf817c10cd2cb23a52d14ab58c6faf68e031eebc4c973e2fe072d`.

The load base **`0x68000000` is synthetic**, outside the stock mapping solely to allow a separate read-only region in the offline machine. It is not an identified camera ROM/RAM area. Generated binaries, derived firmware tables, listings and manifests remain ignored in `local/epl9-native-module-20261104-guard-validated/`. No stock file or installed application is changed. The output is not a firmware container and must not be treated as an update file.

## Why the instruction was blocked, and what changed

At E-PL9 address **`0x60749f80`**, bytes **`f9 16 b6`** decode as unsigned immediate multiply by **182** into D2. The pinned GNU simulator revision `87ffb882e0f4d73401a0746177ffabb8e8bbe4ac` says zero extension in its comment but uses `EXTEND8`/`EXTEND16` in the executable formulas. The old bounded interpreter rejected high-bit immediates rather than choose between them.

Panasonic's **MN103001G/F01K Extension Instruction Specifications, MULQIU, printed page 3-14**, explicitly describes zero-extending the short immediate, multiplying two unsigned 32-bit values, and splitting the result into Dn/MDRQ. The manufacturer's manual is available as a [reproduction at ManualsLib, page 70](https://www.manualslib.com/manual/119167/Panasonic-Mn103001g-F01k.html?page=70). This is a family instruction specification, not a measurement of this camera's processor.

[mn103_subset.py](../scripts/mn103_subset.py) now accepts only the exact `f9 14..17 imm8`, `fb 14..17 imm16`, and `fd 14..17 imm32` encodings with matching decoded operands. The immediate is zero-extended; the 64-bit product is split into low/high halves, and N/Z follow the low 32 bits. Bad widths, opcodes, destination registers or literal/byte mismatches still stop before modifying registers. Other unsupported instructions remain unsupported.

The manual leaves C/V undefined. The subset retains its existing deterministic GNU-style clearing policy for those flags; this is not a new hardware guarantee or cycle-accurate PSW model. The GNU source copies and their pinned hashes are unchanged. This is a documented narrow semantic correction, not a success stub or a patch to the camera instruction.

New arithmetic checks cover 8/16/32-bit boundaries, 182, all four Dn destinations, high-bit operands, both product halves and malformed encodings. The previous host handoff runner also completes all **six** active-H/S/M format/recipe cases in `local/epl9-film-handoff-20261104-active-validated/`.

## Native module interfaces

The reviewed source is assembled by the project's small original [emitter](../scripts/mn103_emit.py), which implements only the instruction forms in this template. It is not a general GNU assembler. The hash-pinned GNU reader independently checks every emitted instruction boundary, mnemonic, operand and branch/call target before execution. No external project's assembly source is republished.

| Entry | Supplied state / behavior |
| --- | --- |
| `film_route_gate` | Inline worklist frame and registers. Only original cached keys `0x01010078` / `0x01020078` jump to ordinary branch `0x607523a5`. Non-targets replay the displaced five bytes and continue at `0x60752207`. Earlier optimized/short paths never enter this gate. |
| `film_commit_job` | A0 = idle job, A1 = caller-owned parameter object. Stores original identity in object `+20`, sets its recipe HSL pointer, attaches it at job `+12320`, then normalizes job header `+12` and cached key `+10384` to 11. The owner must synchronize this operation; no atomicity or lock is fabricated. |
| `film_prepare_frame` | A0 = request, A1 = writable native 4184-byte object, D0 = retained original key, D1 = retained writable 10-byte control buffer; call frame `[d2,d3,a2,a3],44`. Normalizes the request, merges contrast, executes native constructor `0x6078ab39`, selects HSL/token and merges H/S/M into the supplied control buffer. |
| `film_gamma_hook` | Original selector ABI and frame `[d2,d3,a2,a3],28`. Calls native selector `0x6079d328` first, recognizes the module's exact HSL table pointers, then supplies its three persistent curve pointers only for qualified format/state combinations. Preserves the native variant return and reproduces the displaced caller-local store. |

The route fallback displaces **five bytes**, comprising `mov`, `exthu`, `udfu01`. Calls use the tested native save/return conventions. Request and owner buffers are explicit fixtures, not discovered camera allocations. Caller storage must be valid, disjoint except for the supported exact control-buffer alias, stable until completion, and protected from reuse while referenced. These interfaces do not perform hidden allocation or acquire/release an existing owner reference.

## Controls and lifetime

The native constructor runs after recipe contrast is combined with the original signed value and clamped to **-2..2**. It therefore chooses the correct base curve for the merged contrast. The code restores the effective request header afterward and preserves request byte `+1797`, unrelated metadata and the calibration matrix source.

The owner's original five-halfword control block is copied into caller-owned storage, or initialized to zero when absent. The first two fields are preserved without assigning them new meanings. Recipe highlights/midtones/shadows are added to halfwords **2/3/4**, each clamped to **-7..7**. Current biases are:

| Slot | Contrast | Highlights | Midtones | Shadows |
| --- | ---: | ---: | ---: | ---: |
| Gold direction | +1 | -2 | +1 | -1 |
| Portra direction | -1 | -1 | +1 | +3 |

The native base tone remains attached to the object; the normal active-H/S/M path bends it **once**. Nothing substitutes a pre-bent tone and then bends it again. If user settings exactly cancel the biases, the zero-control/native-ROM case is accepted and checked. No permanent owner slider values are modified. Repeated preparation requires a fresh input snapshot or a separate original-control source; reusing already biased controls as the next frame's original input would accumulate corrections and is outside this ABI.

The parameter object retains all native companion data. Its HSL pointer is module-owned read-only data; `+20` holds the original recipe identity, preserving the previously established invalidation role. Tone-control memory remains owner-supplied. Native owner selection/refcount/lifetime and the timing of these calls still need binding to actual preview/capture callers. `film_commit_job` and `film_prepare_frame` cannot simply be inserted at arbitrary points without that work.

## Candidate hook spans

Only a private in-memory copy of the decoded main receives these changes during validation:

| Address | Exact original bytes | Replacement for the synthetic base |
| --- | --- | --- |
| `0x60752202` | `88 1c f9 14 0c` | `dc fe dd 8a 07` — long jump to route gate |
| `0x6079d7f4` | `cd 34 fb f0 1c f8 92 3d` | `dd 1a 2a 86 07 f0 1c cb` — long call to gamma hook, NOP |

The second span replaces both the old short call and its three-byte result store. The hook reproduces that store at callee SP+89, equivalent to caller SP+61, before returning to the unchanged continuation. This avoids pretending that an arbitrary module address fits the original short call. Branch boundaries and replacement operands are independently decoded.

These are **candidate hooks, not a complete patch set**: real placement and incoming-reference analysis, plus actual owner calls to the commit/prepare functions, remain unresolved. The builder emits their bytes and ABI for review, but neither applies them to a firmware container nor claims that installing just these two spans would replace ART correctly.

The gamma hook qualifies formats `0x200`, `0x100`, `0x40`, secondary format `0x100`, zero request variant byte `+48`, zero selector field `+1832` and effective key 11. Special states fall through to the original selector result. Other camera-produced formats have not been assigned new meanings.

## Validation and limits

The module's execution path uses no Python PC redirection or recipe-pointer insertion. The emitted route gate, commit/prepare functions and gamma hook execute as instructions alongside the native firmware. The historical Python routing oracle runs separately for comparison. Host code supplies the declared caller arguments/buffers and measures results.

| Check | Observed scope |
| --- | --- |
| Full worklist grid | **120** native cases against the historical scoped-fix oracle; whole 14552-byte job comparison with declared object attachment |
| Branch-entry effect flags | **1050** cases, including every single bit and original `0x30000` / `0x60000` combinations; scoped fix preserved |
| Native frame-configuration cases | **16**, covering both slots, three formats, extrema, absent input controls, exact in-place controls and cancellation to zero; no hardware pixels |
| Non-target/missing owner-buffer preparation | **6** cases leave every request/object/control payload byte unchanged |
| Ordinary-mode gamma compatibility | **6** full 5200-byte comparisons for keys 1/11 and three formats, identical to stock |
| Special gamma states | **4** comparisons: format, secondary format, variant byte and selector field. Output pointers/return match stock; displaced store is checked |
| Workspace test suite | **206 tests** passed; other chats contribute to the total |

The full color builder's resulting HSL triplets, tone contents, matrix and three pointers match independent configuration oracles. The constructor and parameter/control guards remain intact. Every native call returns with its expected stack/saved registers. This is **configuration execution**, not image processing, DMA completion or a camera test.

```powershell
.\.venv\Scripts\python.exe scripts/epl9_film_module_probe.py --out local/new-native-film-module
# Optional diagnostic RGB data; these are deliberately not calibrated recipes:
.\.venv\Scripts\python.exe scripts/epl9_film_module.py --diagnostic-rgb --out local/new-native-film-rgb-probe
```

Default RGB arrays copy the exact stock common curve. `--diagnostic-rgb` instead emits the previously bounded distinct test remaps. Native WB recipe bias, RGB channel-domain calibration, a film-specific matrix, icons/example pictures, camera owner integration, actual ISP output and image tuning are separate unfinished work. The [Workspace v2 images](epl9-tonal-neutral-trials.md) are still the latest real photographic trials; this module is not a claim to reproduce them in-camera yet.

The optional diagnostic build was also independently disassembled. Its code and HSL bytes are identical to the validated default; only the declared RGB-data region changes, with three distinct bounded monotone arrays per slot. This checks data isolation, not their photographic effect.
