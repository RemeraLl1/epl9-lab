# First bounded offline prototype: E-PL9 ART replacement

Historical experiment and negative regression baseline. Its failures remain useful evidence; [integration](epl9-integrated-prototype.md) and the [2026-11-04 status](project-status.md) describe subsequent fixes, real-input configuration and separate desktop TIFF results. Do not treat this first runner's missing-callee stops or test totals as the current whole-project state.

**Historical baseline and current follow-up:** the first run below is retained as evidence. The revised runner now fixes the four schedule regressions in its tested states and adds 1050 flag cases. The [integrated follow-up](epl9-integrated-prototype.md) executes 120 complete worklist comparisons and both COLOR call chains, including returns. It also records failed full-job attempts; no complete pixel pipeline has passed. The v3 results below must not be confused with the current v4 runner.

The later [native film module](epl9-native-film-module.md) resolves the unsigned-immediate multiply ambiguity using Panasonic's instruction specification. It also executes emitted routing/parameter/gamma code against the same 120/1050 worklist oracles. Historical rejected-immediate descriptions below refer to the earlier subset; no hardware pixel cycle or camera installation is newly established.

## Result, 2026-11-02

The first component-level prototype passes its scoped checks. For synthetic states entering the main ART lookup, converting either Watercolor candidate key to native COLOR key `11` removes the selected Watercolor worklist entries and matches the corresponding stock key-11 worklist. The original I/II choice remains available to the host harness as separate Gold 200 / Portra 400 recipe IDs.

**It is not ready for a firmware patch.** Four target cases already used ordinary development before substitution; the key change gives them a different auxiliary worklist. Their caller context and preview/capture role must be understood before selecting a hook strategy. No Gold/Portra film rendering has been calibrated or rendered by this prototype.

| Check | Observed result |
| --- | --- |
| 30 original/proposed worklist pairs | Pass under the explicitly seeded state: 12 target pairs, 18 control pairs |
| Original I/II mode header copying | Both variants and key 11 copy correctly into request header |
| Ordinary COLOR selector | Reaches call boundary for `0x6079e9e2` |
| Late selector with key 11 | Reaches the color-disable helper; negative control confirms this is the wrong insertion point |
| Custom-table selector | Reaches `0x6079e50e` only with object pointer and flag `0x10000000`; missing flag does not select it |
| Neutral sector coefficient builder | 1550 interpreted instructions reach the return boundary; full output matches field-layout oracle |
| 180 saturation inputs | Every sector, values -7 through +7: output matches independent pinned coefficient predictions, including unchanged bytes elsewhere |
| Full-table builder | Neutral and combined H/S/L marker table both pass full-output comparison; 1132 interpreted instructions each |
| Separate slot markers | Different synthetic input arrays produce different output fingerprints; these are not film recipes |
| Interpreter self-tests | 10 tests pass, including arithmetic boundaries, loop/flag behavior, memory faults, instruction limits and stopping at call/return boundaries |

The successful color tests make full-table attachment a concrete next candidate: synthetic H/S/L fields survive packing into the output configuration. They do not establish pixel appearance, sensor processing or correct integration with every other stage.

## What is actually executed

`scripts/mn103_subset.py` is a small interpreter of the **fresh GNU-decoded instructions**, with each listing's bytes checked against the exact image. It follows the original branches and arithmetic, reads the image's actual dispatch and color tables, and writes into bounded synthetic memory. It is not a hand-coded list of expected Watercolor functions.

It is also **not GNU libsim, a complete MN103 implementation, a boot emulator or a TruePic pixel model**. A full GNU core is not built locally; WSL is not installed. CALL/CALLS and RET/RETF stop before execution. The caller-supplied frame and registers are synthetic; stack save/restore and call ABI are not validated. Isolated sections are exercised separately, rather than pretending to execute an integrated capture pipeline.

The subset supports only the operations needed by these sections. Unknown commands, unmapped instructions/accesses, read-only writes, unaligned half-word/word accesses and instruction-limit exhaustion stop the experiment. Division by zero/overflow and out-of-range shifts also stop. Data alignment checks are a harness constraint, not silicon behavior measured here.

GNU names the relevant multiply encodings `mulq`/`mulqu`; the existing disassembler prints `udf00`/`udfu01`. The subset follows the pinned GNU arithmetic for the used operands. High-bit unsigned immediate variants are rejected because the pinned GNU implementation's sign extension conflicts with its own zero-extension comment. This ambiguity is not silently resolved by guessing. No hardware service, MMIO reply or external call is automatically stubbed.

## Exact inputs and dependencies

- Olympus E-PL9; displayed body version reported by owner: `1.1`; downloaded main internal build `1101`.
- Stock container `OLY_E_133_1101_0000_0000.BIN`: `104552480` bytes, SHA-256 `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`. Container identity is carried from the initial audit; the prototype reads the decoded main.
- Decoded main: `26214336` bytes, SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`; analysis base `0x60400020`. This is not a dump of the owner's installed firmware.
- Reader SHA-256 `e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae`; its existing 43 instruction anchors are checked again.
- Independent numerical fixture: [color-builder-reference.json](https://github.com/fishcu/oly_fw_analysis/blob/539fcf1fa9eda5fdef8ede4deeab94a4691d94c3/tests/fixtures/color-builder-reference.json), SHA-256 `00f5a3f8b95c24da4699e781ab73dc5eab3c84a3e606f558c93879e6618b447f`. The prototype rejects a different fixture. These are predictions/reference observations from another-model/Workspace investigation, not measurements on this E-PL9. Agreement is tested, not assumed from shared table bytes.
- Instruction-semantics reference: GNU revision `87ffb882e0f4d73401a0746177ffabb8e8bbe4ac`, [mn10300.igen](https://gnu.googlesource.com/binutils-gdb/+/87ffb882e0f4d73401a0746177ffabb8e8bbe4ac/sim/mn10300/mn10300.igen), SHA-256 `355754c61879dc24bf6128bbba5a7931355731000e8cb213082b9b9cd4df0129`, and [op_utils.c](https://gnu.googlesource.com/binutils-gdb/+/87ffb882e0f4d73401a0746177ffabb8e8bbe4ac/sim/mn10300/op_utils.c), SHA-256 `4c4c73f71a2961b4e34a8277a75d2565937b849963f5143c96b7e0d75d1a590d`. Read-only reference copies stay in ignored `references/mn103-semantics/`; their source is not republished in this project.

The result file records input, reader, fixture and prototype-source hashes. Firmware files remain unchanged; only synthetic RAM receives proposed mode/parameter changes.

## Worklist boundary and the uncovered difference

Entry is `0x60751eb2`, after the builder's early optimized paths. The harness provides a 14552-byte job, zero effect flags, cached key/header, type word, selector, a 12-byte worklist entry for `0x6075199d`, index 1 and the established stack pointers. It runs to the return boundary at `0x60752912`.

The grid uses keys `0x01010078`, `0x01020078`, `1`, `11` and `0x01030078`; type words `0x0200`, `0x0100`, `0x0040`; selectors `0` and `2`. Control key `1` is intentionally not assigned a user-facing mode name here. The invalid/unsupported variant `0x01030078` checks exact matching rather than matching only low ID `0x78`.

For type `0x0200`, selector `0`, either Watercolor key selects:

`0x6075199d → 0x60754834 → 0x60754944 → 0x60754ba6`

The proposed effective key 11 selects:

`0x6075199d → 0x60751319`

With selector `2`, the original includes `0x60754a4b` and completion entries; the proposed list uses the stock key-11 sequence `0x607518c5 → 0x607511db → 0x607518d3 → 0x60751930` after the initial entry.

For type `0x0100` or `0x0040`, selector `2`, the original uses the single ordinary `0x60751319` entry after initialization, while key 11 uses that longer sequence. These are the **four already-ordinary schedule changes** (two types × two target keys). Matching stock COLOR behavior is not proof that its longer sequence is appropriate in the original Watercolor callers. The 18 control pairs remain byte-identical in their selected worklist entries.

Early conditions, nonzero inherited flags, complete job initialization, buffer lifetimes and all other ART modes remain outside this grid. These type/selector values have not been mapped to real preview/capture contexts.

### Static follow-up: what the longer sequence contains

Direct decoding of the same exact E-PL9 image clarifies the four entry functions. Calling them "extra/unnecessary operations" would overstate the finding: they belong to a different stock scheduling path and may be required in its original context.

| Entry | Observed code | Interpretation and limit |
| --- | --- | --- |
| `0x607518c5` → `0x607638cf` | Builds an auxiliary descriptor pointing to `job+4264`, moves a previous entry's `+8` value, and calls `0x60761b6a`. When a source handle at `job+3980` exists, it temporarily obtains a value through `0x6074b41f`, writes `job+12320`, then calls `0x6074b429` and clears that field. | Submission through the previously identified ordinary request builder, with intermediate data and optional parameter-object handling. The acquire/release semantics of the two handle functions still need confirmation. |
| `0x607511db` → `0x60763978` | Calls `0x6074ee9c`, submits service code `31` through `0x6073eab3`, handles failure, and clears the current entry's `+8` value on success. | A service/control step; its exact purpose, synchronization behavior and pixel effect remain unknown. |
| `0x607518d3` | Uses descriptor `job+4264`, computes a byte-count candidate as two 16-bit dimensions multiplied by 2, calls buffer helper `0x6074a8e4` with ID `0x1000`, and passes two addresses and that count to `0x6074bae2`. The latter submits a kind-14 request through `0x6074ef3a`. | Buffer preparation and a data-transfer request candidate. Physical copying/DMA completion is not executed or proven by this static inspection. |
| `0x60751930` | Takes and clears the previous entry's `+8` value, passes it by reference with descriptor `job+4264` to `0x60750c2e`, and stores the returned value in the current entry on success. | Chaining intermediate state/results to another processing helper; the complete helper and ownership contract remain untraced. |

This is evidence about request/buffer orchestration, not additional visible ART effects or a measured slowdown. The original single-entry path also calls other routines internally; four worklist entries versus one does not directly measure work or runtime. Both the lone path and the longer sequence require caller-context analysis before changing their scheduling.

Local evidence: `local/art-routing/extra-ops-prefix.tsv` (`0x607511db..0x60751319`), `extra-ops-tail.tsv` (`0x607518c5..0x6075199d`), `extra-ops-workers.tsv` (`0x607638cf..0x60763a80`), and `extra-ops-copy.tsv` (`0x6074bae2..0x6074bb75`). This follow-up is static only and does not extend the prototype's execution coverage.

Further [service analysis and 11 bounded component checks](epl9-service-dependencies.md) now resolve the handle functions to balanced reference-count operations and service 31 to an owner callback. The latter returns owner state in one inspected handler; other callers can provide different handlers. This refines the unknown meanings above, without executing the integrated job or solving every caller context. The next routing design must retain the four compatible short schedules.

## Recipe and image limits

The harness retains the original mode key and selects `gold200` or `portra400` in Python, then changes the simulated job's header and cached key to 11. No native hook implements this yet. Request-header copying, color selection and coefficient construction are separately checked components; the actual processing requests and callbacks are not run as an integrated job.

The two recipe-slot markers use `[1,0,...]` and `[0,-1,0,...]` solely to prove distinguishable numerical inputs. The combined full-table test uses synthetic H/S/L values. None are proposed photographic settings or claims of film equivalence. There is no pixel output, JPEG, preview, calibrated LUT, grain test, firmware installation or camera access.

The next experiment should trace the four changed caller contexts, qualify a consistent ordinary route and execute native request construction/call ABI with a fuller engine. It should then connect a per-job recipe table with verified flags/lifetime. Original RAW/JPEG samples copied separately from SD become useful for tuning after that route exists.

## Reproduce

With the existing reader, exact local main and pinned ignored reference checkout:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_mn103_subset.py -v
.\.venv\Scripts\python.exe scripts/epl9_offline_prototype.py --out local/new-offline-prototype
```

Do not use Python `-O`; the runner rejects disabled assertions. Output must be a new ignored `local/` directory. The final retained run is `local/offline-prototype-20261102-v3/results.json`. Earlier exploratory runs are retained locally but superseded by this one.
