# E-PL9: late native integration of the two film slots

## Outcome, 2026-11-04

The two accepted replacements now have an independently emitted **late native configuration hook**. It runs after the firmware has selected the request's existing parameter object. It keeps the original job identity, retains the existing owner object and reference-count contract, merges the recipe's tone controls in temporary stack storage, and installs persistent HSL and three-channel curve pointers. On return it restores every changed request field and the caller's identity, dirty flags and scaled tone controls.

This supersedes the early `film_commit_job` / `film_prepare_frame` integration strategy in the [first native module](epl9-native-film-module.md). The old implementation remains as a historical experiment. The late module does not call those interfaces, allocate another parameter object, or repurpose its comparison token `+20`.

**This is still configuration execution, not a completed image-processing cycle or an installable update.** All twelve connected job cases stop at the unmodeled TruePic register write at `0x6073eafa`, address `0x9880014c`. They do not produce pixels or signal completion. Placement at `0x68000000` remains synthetic, and concurrent camera callers have not been qualified. The owner's final color tables will be supplied later; no calibrated film rendering is claimed.

Implementation: [late assembly](../firmware_src/epl9_films_late.s.in), [builder](../scripts/epl9_film_late_module.py), [native validation](../scripts/epl9_film_late_probe.py).

Scope clarification from the owner, 2026-11-04: replace exactly the two Watercolor recipes and their icons. **Keep the existing large example photographs unchanged.** This supersedes the earlier plan to replace those photographs for this integration. Final color tables will be supplied later.

## Retrieved findings and independent checks

The owner requested retrieval of the other chats' findings. Relevant evidence came from the Codex chat **«Оценить исследование прошивки»**, reviewed on 2026-11-04, and the local deeper color audit (`docs/epl9-deep-color-controls.md`, maintained by a separate chat). The retrieved chat's unpublished source was not copied into this project. The assembly and checks here are an independent implementation against this project's pinned E-PL9 input.

The source chat identified why attaching an object early is unreliable:

| Native location | Observed operation |
| --- | --- |
| `0x6076392d` | Long worker acquires the owner's selected object through `0x6074b41f`. |
| `0x60763934` | Stores the acquired pointer at job `+12320`. |
| `0x60763943` | Submits native processing through `0x60761b6a`. |
| `0x6076394f`, `0x60763957` | Releases the reference and clears job `+12320`. |
| `0x6074f264` | Ordinary request construction calls the common header helper. |
| `0x6074f280`, `0x6074f286` | Subsequently copies job `+12320` into request `+1524`, overwriting an earlier attachment. |

The native acquire/release wrappers are decoded locally; they call `0x6074b4da` / `0x6074b4eb`. The existing service findings still apply: pending requests, owner callbacks, event 31 and reference counts must be retained. An early pointer store is not an adequate owner binding.

The other chat also found an equivalence between original Watercolor keys and effective COLOR key 11 **with a particular attached parameter object**. An independent **24-pair** check here reproduces complete 5200-byte equality across two recipes, three formats, active/inactive H/S/M and independent gamma enabled/disabled. The final runner includes this check, so it is reproducible rather than just a reported result.

That equivalence is **not general**. An exploratory late hook that retained Watercolor keys throughout the color builder differed from the COLOR oracle with no attached object: six-axis/chroma fields and the tone result were affected. The negative result is retained locally in `local/epl9-film-late-20261104-probe-v1/`. Therefore the final late wrapper temporarily selects key 11 inside its synchronous calculation and restores the original request/context identity before returning. It never rewrites the job header or cached job key.

## Exact input and output

| Item | Identity |
| --- | --- |
| Camera | Olympus E-PL9; displayed body 1.1 reported by owner; downloaded build 1101, not an installed-camera dump |
| Stock container | `OLY_E_133_1101_0000_0000.BIN`, 104552480 bytes; SHA-256 `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Decoded main | 26214336 bytes; SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`; mapping base `0x60400020` |
| GNU reader | SHA-256 `e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae` |
| Default late module | 1171 code bytes, 15360 total bytes; SHA-256 `938e2b72a65e0d953c9a50500779aeebfd1e5e679ac4a418634a7bf1027e4ebb` |

The generated module, derived tables, listing, patch spans and detailed results stay ignored under `local/epl9-film-late-20261104-validated/`. A separately validated diagnostic build is under `local/epl9-film-late-20261104-diagnostic-validated/`. No stock file, installed application or camera is modified.

## Input for the later color tables

Both the builder and the native probe accept `--rgb-tables path.json`. The strict `epl9-native-rgb-tables-v1` document has only `schema` and `recipes`; `recipes` contains exactly two entries with `watercolor_key` (`0x01010078` or `0x01020078`) and `curves`. Each `curves` array contains three native-order arrays of exactly **256 integers in 0..4095**, nondecreasing. Nonzero endpoints are allowed, as in some stock ART curves. Unknown fields, additional or duplicate recipe slots, booleans, folded curves and wrong lengths are rejected. Diagnostic generation and supplied tables are mutually exclusive.

The builder embeds those six arrays in persistent module data and records the canonical input-document hash in the manifest. They replace data only; the late hook does not need rewriting. The array order is native slot 0/1/2: physical channel order, transfer domain and photographic meaning are not yet camera-verified, so the file does not misleadingly label them R/G/B. This input is for native gamma arrays; it is not a general 3D LUT or a replacement for the separate tone/HSL definitions.

Reimporting the six diagnostic arrays through this interface produces a byte-identical module, SHA-256 `9b61a2972a2b443fab623bca4ae2d25fb46cfbeb15880c4df3f3b33f3164f639`. The input remains ignored in `local/epl9-film-late-diagnostic-rgb-input-20261104.json`; its full native validation is in `local/epl9-film-late-20261104-rgb-input-validated/`. This verifies the future data-loading path without inventing final film tables.

## Late wrapper contract

The hook replaces the first five bytes of common color builder `0x6079fb88`. Its trampoline replays `mov a0,d3; mov d3,a3; inc4 a3` and enters the unchanged continuation `0x6079fb8d` using the original native `[d2,d3,a2,a3],40` frame.

Recipe entry requires coherent original request/context keys for exactly `0x01010078` or `0x01020078`, format `+14` in `0x200/0x100/0x40`, secondary format `+28` in `0x100/0x200`, variant byte `+48=0` and selector halfword `+1832=0`. Secondary `0x200` is included because the actual native long-job producer emits it; a fixture default of `0x100` alone missed those requests. Format numbers are retained as numbers, not assigned unverified preview/capture names.

The recipe wrapper adds **88 stack bytes** to the original 40-byte frame. It:

1. Saves request `+8`, `+1512`, `+1524`, `+1795` and context `+52`, `+60`, `+64..79`.
2. Temporarily uses request/context COLOR key 11, merges contrast into the signed range -2..2, and copies the five original control halfwords into stack storage. Null source controls become zero. The first two halfwords are preserved; H/S/M biases are added to indices 2/3/4 and clamped to -7..7.
3. Runs native scaler `0x6074a061`. Native rebuilding receives the caller's flags OR `0x10000002`; this prevents a retained owner token from hiding a per-request recipe change.
4. Runs the native common color chain with its selected owner object still attached. The gamma hook supplies persistent module curves through the normal native setter/cache path.
5. Packs the selected HSL table using native `0x6079e50e`. It temporarily clears the request's owner pointer only while rerunning native tone builder `0x6079f309`, selecting the base for the merged contrast and applying merged H/S/M once. It never installs a pre-bent curve and then bends it a second time.
6. Restores all saved fields and the original native return value, then returns using the combined 128-byte frame convention.

The final tone pointer addresses the native output-owned tone buffer or stock ROM, never the temporary controls. The owner object is mapped read-only during the probes, including its gamma/tone/HSL companion fields and `+20` token. No new heap or owner control buffer is retained.

The gamma hook calls the original selector first. Before accessing its extra stack record it verifies the exact native return site, matching context/request pointers, temporary effective header/key, the return address of the late wrapper's inner call, and the expected stack control pointer. Only then does it read the original recipe key and magic marker stored beyond the five control halfwords. Ordinary callers' ten-byte controls are not treated as extended records. The displaced result-byte store and native variant return are preserved.

This is per-invocation state; there is no global “last recipe” variable. A synchronous probe does not establish that another camera task cannot observe the temporary request fields. Actual caller synchronization and camera stack headroom remain requirements for deployment.

## Cache exit and unchanged routes

Persistent output gamma pointers identify a prior configuration from this module. When the next request is outside the accepted recipe state, the late wrapper forces a native HSL/tone rebuild. The stock gamma cache path then replaces the film pointers. Other cold ordinary requests go directly through the original trampoline without the additional frame.

The worklist gate remains narrowly scoped to the historical ordinary-path fix. Earlier compatible short schedules are retained. Original job header `+12` and cached key `+10384` stay unchanged. There is no host PC redirection, Python recipe injection or post-constructor key normalization when the connected probe's `native_module` option is enabled. Mixing that option with host table attachment is rejected. Default behavior of the historical job probe is preserved.

Candidate spans for the synthetic base are:

| Address | Original | Replacement |
| --- | --- | --- |
| `0x60752202` | `88 1c f9 14 0c` | `dc fe dd 8a 07` |
| `0x6079d7f4` | `cd 34 fb f0 1c f8 92 3d` | `dd 4c 2b 86 07 f0 1c cb` |
| `0x6079fb88` | `f1 d3 f1 ef 53` | `dc a7 04 86 07` |

The pinned GNU reader checks every emitted instruction boundary, operand, branch and call. These bytes are applied only to a private in-memory copy for the probes. They are not a qualified patch set for an update container: incoming references, actual executable/data placement, relocation and camera synchronization are still open.

## Validation

| Check | Result and scope |
| --- | --- |
| Attached-object original-key comparison | 24 pairs, whole 5200-byte configurations equal; narrower fixture result, not a reason to omit temporary COLOR selection |
| Native recipe frames | 32 cases: both slots, three primary formats, both secondary formats, owner present/absent, extrema, null controls, cancellation to zero; whole 5200-byte oracle equality |
| Whole request restoration | 1876 bytes per checked recipe frame; context identity, dirty flags and scaled tone restored; native saved registers/stack and return checked |
| Warm cache and exit | 9 sequential frames with retained native output/cache: Gold → Gold → Portra → Portra → Gold → ordinary 11 → 11 → 1 → 1; subsequent caller flags zero; all full configuration comparisons pass |
| Cold passthrough / excluded states | 12 full configuration comparisons: three ordinary/non-target keys × three formats, plus three excluded request states |
| Owner references | Native acquire/acquire/release/release counts 1 → 2 → 1 → 0, balanced original owner bytes; same read-only object used by both recipes; sequential fixture, no RTOS concurrency claim |
| Worklist regression | 120 whole-job comparisons against the historical scoped fix; original job identity preserved |
| Effect flags | 1050 cases preserve the historical flag-grid oracle, including its four original schedule regressions |
| Connected construction/start/execution | 12 jobs: two keys × three kinds × two selectors; kind `0x40` uses explicit owner slot and input format `0x100`; all reach native recipe packing and retain selected three pointers |
| Diagnostic RGB build | Same emitted code; distinct diagnostic channel arrays pass the frame, cache-exit and connected-job checks; no photographic effect inferred |
| Workspace tests | 211 tests passed, including strict RGB input guards and other chats' existing tests; no camera access |

The historical `epl9_job_probe.py` runner was also rerun without `native_module` in `local/epl9-job-late-compatibility-20261104/`; its existing construction, error-cleanup, packing and resource assertions still pass. Its expected hardware and missing-fixture boundaries remain expected boundaries, not successful pixel cycles.

The connected probe adds the exact native short-path parameter-selection window `0x607902b0..0x607909c0`, rather than replacing the formerly missing call with a success model. Consequently all twelve jobs reach the same first TruePic MMIO boundary. Their source-read count is zero, output pixels are unchanged, pending records are still live, and no completion event is signaled. Native construction and CPU configuration are proven only under the existing explicit host-resource models. The probe does not fabricate ISP output, interrupts or request cleanup after successful processing.

```powershell
.\.venv\Scripts\python.exe scripts/epl9_film_late_probe.py --out local/new-late-film-validation
.\.venv\Scripts\python.exe scripts/epl9_film_late_probe.py --diagnostic-rgb --out local/new-late-film-rgb-validation
# When the owner's native-order tables are available:
.\.venv\Scripts\python.exe scripts/epl9_film_late_probe.py --rgb-tables local/owner-rgb-tables.json --out local/new-owner-table-validation
```

Each output path must be new and inside ignored `local/`. The stock main is hash-checked before and compared after execution.

## Remaining implementation boundary

The integration now has concrete native hook sites and avoids the earlier custom-owner allocation/binding problem. It retains the v0 HSL and v2 tone directions. Default RGB data are stock; the optional different curves are deliberately diagnostic. The [deployment and extended-color follow-up](epl9-film-deployment-color.md) adds optional early gain bias, bounded native matrix deltas and the separate six-axis packer, and embeds ten icon resources in an offline OSD copy. Final photographic calibration, deployment qualification and runtime screen/palette mapping remain unfinished; the accepted replacements remain exactly the two Watercolor slots. Existing example photographs are retained by the owner's latest instruction.

To make this deployable still requires qualified module storage and references, caller/stack/synchronization review, update-container integration, and eventual camera-side ISP/pixel/completion checks in the agreed installation phase. The present software model cannot turn an unmapped hardware write into a real Gold/Portra image. The latest actual photographic results remain the [Workspace v2 trials](epl9-tonal-neutral-trials.md).
