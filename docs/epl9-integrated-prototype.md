# Revised offline prototype: preserved schedules and native call chains

## Result, 2026-11-02

The revised host experiment removes the four schedule regressions found in the first prototype. It also runs the worklist builder from its actual entry, preserving earlier optimized paths that the original branch-only experiment did not reach. Both recipe slots execute native COLOR selection, table packing and returns with a complete 5200-byte output comparison.

**The complete image-processing cycle has not passed.** Constructor and executor attempts stop at identified software dependencies outside the loaded code. No pixel image, JPEG, live view or calibrated Gold/Portra rendering was produced. This is an improvement to offline analysis, not a firmware patch.

## Inputs and execution boundary

Exact input: Olympus E-PL9, owner-reported displayed version **1.1**, downloaded main build **1101**. The installed firmware has not been dumped.

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| `OLY_E_133_1101_0000_0000.BIN` | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Decoded main | 26214336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |

Candidate main mapping is `0x60400020`, not measured RAM. Runners read and hash-check the decoded main and record the container identity from the prior audit. They verify 43 GNU decode anchors, and the integrated runner rejects conflicting overlapping listings. Reader SHA-256 is `e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae`.

The opt-in `mn103_calls.py` extends the existing interpreter with CALL, CALLS, RET, RETF and MOVM for the d2/d3/a2/a3 save masks. Stack behavior follows the pinned [GNU instruction semantics](https://gnu.googlesource.com/binutils-gdb/+/87ffb882e0f4d73401a0746177ffabb8e8bbe4ac/sim/mn10300/mn10300.igen), SHA-256 `355754c61879dc24bf6128bbba5a7931355731000e8cb213082b9b9cd4df0129`. CALL saves below the original SP but adjusts SP by the encoded frame size; CALLS leaves SP unchanged; RET reads the stack return address and RETF uses MDR. Unsupported masks, instructions, memory and absent callees stop execution. No missing function is replaced by a success return.

Synthetic caller frames, job RAM, descriptors and parameter objects are supplied by the harness. This is not a complete MN103/AM33, RTOS or ISP emulator. The old `Machine` still stops at call/return boundaries unless the new opt-in engine is used.

## Routing change and preserved services

The original key remains intact while the native worklist builder evaluates early paths and Watercolor type checks. Only exact keys `0x01010078` and `0x01020078` are eligible for replacement.

If execution reaches `0x60752202`, the host redirects it to `0x607523a5`, the ordinary branch. The current list index and registers remain intact; subsequent native effect-flag logic still runs. If the Watercolor-pass branch is never reached, no redirection occurs. After worklist construction, the harness changes both the job header at +12 and cached key at +10384 to 11, retaining the original recipe identity in host state.

This deliberately separates scheduling from the effective color key. It is not a proposed binary edit, an installed hook, or proof that each optimized path consumes COLOR. The consistent key handoff and eventual attachment of a recipe object still need a native implementation and real caller evidence.

At the old branch-entry boundary, the four already-ordinary cases retain their exact original worklists. The historical blanket key substitution is still reproduced as a negative regression check and still changes four cases. Effect flags matter: the retained short branch and default branch can use different intermediate flags that decide whether a callback is attached or another entry appended. Comparing only function addresses would miss this; all three words of each entry are compared.

From the complete builder entry `0x607519b8`, zero-flag target cases produce these schedules after initialization `0x6075199d`:

| Type | Selector | Revised schedule after initialization |
| --- | ---: | --- |
| `0x0200` | 0 | `0x60751319` |
| `0x0200` | 2 | `0x607518c5 → 0x607511db → 0x607518d3 → 0x60751930` |
| `0x0100` or `0x0040` | 0 | Original early path: `0x607511e9` |
| `0x0100` or `0x0040` | 2 | Original early path: `0x6075124b → 0x607511db → 0x60751259` |

The last two rows are newly executed early paths, not contradictions of the previous experiment entered later at `0x60751eb2`. They retain completion/event-31 handling and pending-handle forwarding. Every nonredirected job is compared byte-for-byte against stock, except the two explicit mode-key fields. Redirected lists match the corresponding ordinary reference in the tested states.

The existing [service contract](epl9-service-dependencies.md) remains in force: pending-request completion, owner callbacks including event 31, status/cancellation handling, buffer ownership, balanced parameter-object references, and table lifetime must survive the replacement. Passing worklist comparisons does not prove completion or DMA behavior. All 11 bounded service checks are rerun without expanding their stated scope.

## What passed and where the full cycle stopped

| Check | Result and scope |
| --- | --- |
| Original branch-entry grid | 30 stock/proposed pairs; zero short-schedule regressions |
| Effect-flag grid at that boundary | 1050 cases: five keys × three types × two selectors × 35 flag values (zero, each single bit, two combinations) |
| Complete native worklist builder | 120 stock/proposed pairs, including calls and returns: same key/type/selector grid × flags 0, `0x10000`, `0x20000`, `0x30000` |
| COLOR integration for each target | `0x6079ebcc → 0x6079e50e → selector return → synthetic caller`, 1155 instructions per slot; full output and restored SP/saved registers checked |
| Existing numerical coefficient tests | 180 saturation cases and two full-table packing cases pass |
| Existing service components | 11 bounded checks pass; still separate from full processing |
| Seeded job execution | 12 attempts, both targets × three types × two selectors; initialization entry completes, then each stops at the unmodeled helper `0x4700111e` |
| Pre-cancelled job | All 12 return error `0x9e01`, mark cancellation, and execute no worklist entries |
| Native job constructor | Stops at allocator call `0x6074df0c → 0x60402373`, before allocation |

Executor stop sites are `0x60751346` (ordinary short worker), `0x6076390c` (long/early worker) and `0x60750b30` (early short processing), all calling `0x4700111e`. Its observed arguments are consistent with a memory-fill helper, but its body is not in the loaded main window. These are currently software/coverage boundaries, not measured hardware failures. The complete constructor was not connected to the separately seeded executor or COLOR tests. Successfully simulating the allocator/fill would not by itself establish the remaining pipeline or ISP behavior.

The COLOR checks use two different synthetic table markers, +50 and -50 in one field. The object, enabling flag and table are supplied by the harness, with the table kept alive through the call chain. This verifies neither native object attachment/refcount integration nor hardware consumption of the LUT pointers. It does not define the Gold 200 or Portra 400 recipes.

The grid does not exhaust every job field, mode or combination of effect flags. Preview/capture caller mapping, optimized-path color consumption, actual pixel processing, error recovery after submitted requests and on-camera execution remain unverified.

## Reproduction and next concrete work

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p 'test_mn103*.py' -v
.\.venv\Scripts\python.exe scripts/epl9_offline_prototype.py --out local/new-bounded-prototype
.\.venv\Scripts\python.exe scripts/epl9_integrated_probe.py --out local/new-integrated-probe
```

Use a new ignored output directory and keep assertions enabled. Retained runs are `local/offline-prototype-20261102-v4/results.json` and `local/integrated-probe-20261102-v2/results.json`. Six new ABI tests plus the ten existing subset tests pass; they validate the implemented conventions against synthetic inputs, not the hardware CPU.

Next: resolve the allocator/fill dependencies or add explicitly labeled, independently checked software models; continue native request creation/submission until the actual external processing boundary is understood. Then trace where each retained optimized path obtains color, connect a recipe table with its native ownership/flag contract, and test pixels. Do not bypass errors or report a mocked success as a complete cycle.

## Follow-up: explicit software contracts and deeper native execution

The subsequent `--software-models` run advances beyond the earlier memory dependencies. It does **not** complete image processing. `mn103_calls.py` still stops at absent code by default. Opt-in models cannot shadow decoded native code; every use has a separate `modeled_call` event rather than appearing as a native instruction execution.

The actual allocator front at `0x60402373..0x604023b2` is now executed. Its 14552-byte request selects pool ID `0x10004` (16384-byte size class), then calls `0x60402595`. The host model supplies exactly one predeclared 16 KiB block, initially filled with `0xa5`, or an explicit null allocation. It rejects a second allocation, another pool ID and an ABI mismatch; it is not a simulated heap or RTOS pool implementation.

The assumed byte-fill helper at `0x4700111e` validates its entire destination before changing memory and rejects writes outside a writable region or into its pending call frame. It records each address, count and byte. Its assumed volatile effects advance a0 by count, zero d1 and preserve d0/a1/flags; the missing E-PL9 implementation's actual clobbers are not established. The allocation model sets a0 and otherwise retains volatile registers/flags. These explicit assumptions limit the conclusions even when caller stacks and memory checks pass.

Both keys, with synthetic task-byte values 0 and 7 at the read-only cell `0x8050`, now execute the constructor through **11 fills**, 32-byte parameter copying, mode-key caching and task-byte assignment. All expected cleared spans, copied parameters and the unused allocation tail are checked. Execution stops at `0x6074e066 → 0x6073e562`. Separate disassembly identifies that callee as another constructor requesting **5764 bytes** and calling an initializer at `0x6073e588`; this second object and its lifetime are not yet modeled or integrated. The forced first-allocation failure returns zero, writes error `0x9ec3`, restores SP and touches neither the job block nor the fill helper.

The executor additionally runs native buffer-slot lookup (`0x6074acf9`), dimension selection (`0x6075088e` / `0x607509b0`) and type classification (`0x607a3c9e`). Current exact stopping points, identical for Gold and Portra in the synthetic grid:

| Type / selector | Stop at call site → absent callee | Executed instructions |
| --- | --- | ---: |
| `0x0200` / 0 | `0x607508bd → 0x60749187` | 214 |
| `0x0100` / 0 | `0x607508bd → 0x60749187` | 231 |
| `0x0040` / 0 | `0x60750942 → 0x607491d5` | 238 |
| All three / 2 | `0x6074f2ab → 0x60750498` | 1434 |

These are **software coverage boundaries**, not identified ISP/DMA boundaries. Only initialization completes as a worklist entry. The executor still starts from a separately seeded job with mostly zero fields; buffer descriptors and owner state are not measured camera state. More executed instructions do not demonstrate a valid submitted request, a connected constructor/executor, optimized-path COLOR consumption, a finished pixel frame or a JPEG.

Revalidated: 120 complete-builder pairs, both 5200-byte COLOR results, 12 pre-cancellation paths and all 11 bounded service checks. Five additional synthetic model tests check range rejection before mutation, zero-length fill, canaries, preserved saved registers/stack, allocation failure/exhaustion and ABI rejection. No unknown image-processing call returns automatic success.

```powershell
.\.venv\Scripts\python.exe scripts/epl9_integrated_probe.py --software-models --out local/new-modeled-probe
```

Retained final follow-up run: `local/integrated-probe-20261102-v5/results.json`. Next connect the real descriptor/dimension/owner inputs and the second object's lifetime, then continue to the request consumer. Keep `full_pixel_cycle_passed` false until there is actual pixel output with independently checked behavior.
