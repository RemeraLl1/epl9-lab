# Source-only emulator publication check, 2026-11-12

This publication is based on `feat/native-source-v1-package` at
`b0f9ebb1b178106eec95137dfc3d558c68e9a291`. It adds only authored source,
tests, dependency declarations and documentation. It is a separate research
branch, not a change to the frozen ART-only candidate or a firmware release.

## What was freshly checked

Publication checks used Python 3.12.14, NumPy 2.3.5 and Pillow 13.0.0.
`requirements-emulator.txt` pins this source-test/image-comparison environment;
it does not replace the historical RAW/toolchain requirements or attest a new
full firmware replay.

A clean source worktree received the preserved producer and final UI bridge
patches. Their source bytes remain identical to the recorded runs:

| Source | SHA-256 |
| --- | --- |
| `epl9_virtual_flash.py` | `575e236a8dfdce13345118c3e5b32577fddc50f23d089d091168ca3d5fdce85b` |
| `epl9_virtual_install.py` | `ee071b44645bdc73e2dd2b27eb3f80e2177bcec7ff2feb385cce48514d0b181f` |
| `epl9_virtual_flash_ui.py` | `93513d2617d32d81b332e0642dc8ef09864b9a4b98ceef7a8d7d18118b6107ab` |

- All 51 new virtual-store/updater/UI contract tests pass without firmware.
- All 28 unchanged native-source UI qualifier tests pass without firmware.
- The six newly published Python implementation/test files compile.
- No manufacturer firmware, decoded components, private RGB inputs, persisted
  flash images, overlays, screenshots or upstream implementation is included.

The broader discovery attempted 473 tests. It is **not a complete pass**:
15 tests skipped their unavailable inputs, and two pre-existing test scopes
reported missing prerequisites:

1. `test_epl9_osd_audit.OSDTests.setUpClass` requires the ignored independently
   sourced `references/caduceus-ep7/tools/osd_extract.py`.
2. `test_epl9_page_collection.PageCollectionTests.test_both_full_components_twice_for_candidate_and_restore`
   requires the historical private-color-v3 package pair under ignored `local/`.

Those tests and their assertions were not weakened or edited to make a source
checkout appear fully qualified. Use the explicit source-only commands in the
README for this publication's new scope. The private prerequisites must be
obtained from their documented authorized sources before invoking those other
scopes.

## Recorded exact-image results, not reruns in this checkout

The preserved originating run connected the real updater, selector and
program/readback wrapper to persistent logical storage. Thirteen full-size
scenarios and ten additional checksum-loop equivalence controls passed their
stated expected outcomes. Four fresh OM-Emu UI sessions subsequently consumed
actual stored payloads; all 41 restored-stock frames matched the baseline.
Exact private report and source hashes are recorded in the
[public summary](evidence/virtual-emulator-20261112.json).

The originating full-size firmware inputs and replay directories are not in
this source-only publication checkout. Consequently no fresh full-size native
replay, reader build, OM-Emu session or camera test was performed for publication.
The current code does not make those inputs optional or replace them with
synthetic success. Private trace/report identity hashes permit comparison with
preserved reports but do not reproduce their contents.

## Limits that remain

The logical flash has assumed geometry and modeled program/read leaves. It
is not a full physical NAND/OOB/ECC/controller model. The updater receives an
explicit software entry and preloaded input bytes. OM-Emu later starts its own
kernel/UI harness; neither step executes a physical reset-to-recovery route.
UI frames do not demonstrate recipe pixel processing or TruePic completion.
`install_ready` remains false, including for other camera models.
