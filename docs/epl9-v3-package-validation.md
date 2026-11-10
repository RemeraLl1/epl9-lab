# E-PL9 Gold/Portra v3 package pair — 2026-11-07

## Result and scope

**Follow-up:** [component readback, synchronization and memory](epl9-v3-readback-sync-memory.md)
adds the full-size comparator, interleaving controls, corrected stack accounting
and native pool exclusion checks. The packages below remain byte-identical.

The owner explicitly requested construction and verification of the v3 installation candidate and its stock-restoration package, with recipes unchanged. Both encoded files now exist and pass host container checks and full-size native-validator control-flow checks under the declared local model. **They are not yet qualified for physical installation.** No camera, SD media or physical flash API was accessed.

| File under `local/epl9-v3-packages-20261107/` | Bytes | SHA-256 |
| --- | ---: | --- |
| `Gold-Portra-v3-candidate.bin` | 52428800 (50 MiB) | `8d606a028f4b533db6431f1a0271a92d8f3f1c71e08833b481dcb2310d79ef8f` |
| `Stock-1101-main-osd-restore.bin` | 52428800 (50 MiB) | `10a7b949d1509ce627cb3c098c0a01a8ae5758fb2ce84b6c887e34b46e349387` |

Each is a selective package containing exactly **main `0100` and OSD `0101`**, in that container order. Each component occupies 26214400 bytes including its 64-byte envelope. Restore contains the exact original encoded component bytes, not an approximation or a downgrade to a different downloaded version. It covers every component modified by this candidate. Other components, including picture `0102`, are omitted from both files and consequently are not requested for writing in the tested updater path. This is not a backup of device-specific settings/calibration.

The filenames are research artifact names, not confirmed camera SD-loader names. `README.txt`, `SHA256SUMS.txt`, `manifest.json` and `qualification.json` accompany them. Files and firmware remain Git-ignored; none was published.

## Exact inputs and frozen recipe identity

Olympus E-PL9, model bytes `1330`, displayed body **1.1** reported by the owner; downloaded main build **1101**, not an installed-body dump.

- Original package: `firmware/OLY_E_133_1101_0000_0000.BIN`, 104552480 bytes, SHA-256 `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`.
- Stock main: 26214336 bytes, SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
- Stock OSD: 26214336 bytes, SHA-256 `ee9a9c3ad1974dd212483ca7d012e51ae23083ce0119589a3b42996aa13ccf1e`.
- Candidate main: 26214336 bytes, SHA-256 `501707d09a0eb648e46196752b7ece17cd5368f6d54dbabce7c73e9806f65686`.
- Candidate OSD: 26214336 bytes, SHA-256 `50141904c211fd16bc4c26b35cd52955f96a9e611ca062d84fe0169eeda21b3b`.

These are exactly the components in the [unified v3 integration report](epl9-v3-integration-status.md). The builder pins that integration manifest and all its evidence files, verifies the existing fifteen overlay spans (module/four hooks/ten icon resources), and rejects any other decoded change. The declared spans contain 23303 changed decoded bytes in total; this does **not** reduce the updater's full-component write lengths or quantify failure risk.

Five recipe-input files, including the emitted native RGB tables, are hash-recorded and rechecked unchanged. No tone, WB, HSL, gamma, matrix or six-axis recipe change was made while packaging. All 17 audited updater/startup ranges checked by the builder remain byte-identical to stock. This range audit is not exhaustive proof of every startup dependency or runtime writer.

## Host checks and independent implementation

`scripts/epl9_v3_package.py` uses a bounded inverse of the measured 16-byte permutation/inversion and recalculates only the four-byte trailer checksum for changed payloads. Every other header/trailer byte, model/build field, destination and component length is preserved. Restoring an unchanged payload reproduces the original entire component byte-for-byte.

The strict host parser rejects duplicate kinds, unexpected model/kinds, invalid lengths, truncation, trailing bytes, header/trailer mismatches and bad checksums. The builder requires both and only the two accepted target components, preserves their stock order, and validates written file hashes after disk readback.

An independent implementation is loaded from the ignored [fishcu/oly_fw_analysis](https://github.com/fishcu/oly_fw_analysis/tree/539fcf1fa9eda5fdef8ede4deeab94a4691d94c3) checkout at commit `539fcf1fa9eda5fdef8ede4deeab94a4691d94c3`. `tools/oly_container.py` SHA-256 is pinned to `2b72243f7af4735f5e341ce8f04ec4527dcf40ccfcf9ae3741efe7146657dce2`. Its source was not copied into this project. It independently parses and re-encodes the complete original five-component file and both new two-component files, reproducing all three bit-for-bit and recovering the exact expected decoded payloads.

Six new package tests and nine existing strict-host-parser tests pass. They cover round-trip identity, changed checksum with preserved envelope metadata, exact stock restoration coverage, forbidden extra/missing/reordered/duplicate components, wrong lengths/models and corruption.

## Full-size native control flow, with explicit loop acceleration

`scripts/epl9_package_native_probe.py` executes the original E-PL9 outer updater/validator and selectors on the actual 52428800-byte files. It does **not** interpret every iteration of the large byte loops. Three byte-checked loops are algebraically accelerated, with their final iteration executed natively:

| Loop | Action |
| --- | --- |
| `6100397e..610039e7` | Permute each 16-byte block |
| `610039ef..610039f9` | Invert each payload word |
| `604d54c5..604d54cd` | Sum little-endian words modulo 2^32 |

Ten small controls (payload sizes 16, 32, 80, 256 and 4096, each intact/corrupted) compare accelerated and unaccelerated execution. **All registers, flags, loop state, stack, caller result, package bytes and non-acceleration events match.** Bulk operations are bounded to mapped package memory. The final iteration preserves native register/flag effects; no checker is replaced by an unconditional successful return. Fresh listings are checked against exact stock bytes using reader SHA-256 `e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae`.

Diagnostics/progress notifications retain the existing explicit host boundaries. The write selector `604a0f8b` is trapped: it records arguments and hashes of the complete decoded envelope, without executing physical program/readback code. Thus the result establishes local validator/selection behavior, not camera acceptance, flash programming, bootability or recoverability.

Sixteen full-size cases complete:

- Candidate validation runs using stock main; restore validation runs using the exact modified main. All loaded validator instructions are identical between those images.
- For each file, mode 0 validates/decodes and requests two trapped writes; mode 2 validates/decodes with zero write requests; mode 1 consumes that checked decoded buffer and requests the two intended components. All six positive paths return zero, balance the stack, preserve package guards and recover exact host-decoded bytes.
- Corrupting the first or second component's encoded payload is rejected with `3211` **before any write request**, for both candidate and restore (four cases).
- Three per-file injected backend-error cases record the native multi-component status behavior described below (six cases). These are evidence of an error-handling limitation, not successful error recovery.

Native write order differs from container order:

| Order | Component | Destination at the trapped selector | Bytes |
| --- | --- | --- | ---: |
| 1 | OSD `0101` | `421e0000` | 26214400 |
| 2 | main `0100` | `806e0000` | 26214400 |

Translator `60445069` maps the main's `406e0000` address to `806e0000`, while OSD `421e0000` remains unchanged. An initial checker incorrectly assumed container order and uniform address translation. A second checker assumed immediate termination on the first backend error. These **test-oracle assumptions** were corrected against fresh native traces; neither required any change to the packages. The first two incomplete runs are retained locally; only `local/epl9-v3-package-native-final-20261107/validation.json` is the complete report.

## New finding: an earlier component error can be hidden

At the trapped write-selector return boundary:

| Injected OSD result | Injected main result | Requests made | Final result |
| --- | --- | --- | --- |
| `3105` | `3105` | OSD, then main | `3105` |
| `3105` | `0` | OSD, then main | **`0`** |
| `0` | `3105` | OSD, then main | `3105` |

This occurs for both package directions in the tested original native control flow. It is additional to the [previous lower-writer error propagation finding](epl9-installation-recovery.md): even an error exposed at this higher boundary can be lost when a later component succeeds. It is a simulated error injection, not an observed physical write failure. The update code was kept stock. A final zero result alone cannot establish that both components were written correctly, and the process is not demonstrated to be transactional.

## What remains before the first camera test

The requested **package construction and offline checking are complete**. Remaining pre-installation work is separate:

1. Confirm the E-PL9-specific entry/delivery procedure and ability to reach stock restoration on this body. A prepared restore file does not establish recovery after failed startup; the unresolved independent-loader/OK-power findings still apply.
2. Establish an independent way to verify both written components. The newly observed multi-component error masking means the updater's success indication alone is inadequate. No physical readback method is newly qualified by this pass.
3. Review the remaining same-job concurrency/IRQ and code-slot-lifetime uncertainty for the selected first-test path. The previous native owner/load tests are scoped evidence, not proof covering every caller or interrupt.

Actual TruePic pixels, normal hardware completion, preview/capture behavior and switching between recipes are **objectives of the later camera test**, not a prerequisite expected from the incomplete emulator. Hardware tests have not occurred. Existing risk/recovery research was not restarted, and no instruction to flash or copy these files to a camera card is given here.

## Reproduction

```powershell
.\.venv\Scripts\python.exe scripts/epl9_v3_package.py --out local/new-v3-package-pair
.\.venv\Scripts\python.exe scripts/epl9_package_native_probe.py --packages local/new-v3-package-pair --out local/new-v3-package-validation
```

Output directories must be new and inside ignored `local/`. Source firmware and recipes are read-only inputs. Native disassembly used the established outside-sandbox DLL workaround; it did not grant the probe any camera interface.
