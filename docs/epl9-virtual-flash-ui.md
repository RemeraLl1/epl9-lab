# E-PL9 persisted virtual updater writes to fresh UI sessions

## Scope

This bridge consumes completed `epl9-virtual-install-components-v1` results for
`install-candidate` and `restore-stock`, generation `native-source-v1`. It does
not install firmware on a camera, prepare a card, connect USB, perform a hardware
reset, or claim recovery. Firmware bytes, overlays, runtime reports and PNGs stay
private in ignored local directories. Original recipes and all existing
builders, runners, observers and qualification sources remain unchanged.

The producer executes the native updater, write selector, program/readback
wrapper and checksum instructions with explicitly modeled storage leaves. The
consumer starts separate OM-Emu UI sessions. Those are normal loader sessions,
not execution of a full NAND reset/boot chain. Upstream E133 `loadNand()` returns
null; it is not a complete stock NAND image. The logical component store is not
a full NAND/OOB/controller, bad-block, cache/DMA, ISP or physical power-loss
model. A stock-looking frame is not proof of physical restoration or recovery
after a failed boot. Install readiness remains false.

## Source and replay chain

`scripts/epl9_virtual_flash_ui.py` rejects specimen, incomplete, faulted, mixed
or historical-generation results. It requires the exact successful schema,
both component identities and explicit virtual-only flags. Paths are bounded,
normalized and direct; missing files and symlinks are rejected.

Before creating a screenshot, the bridge independently verifies:

- The complete pinned encoded source package and both decoded component
  envelopes, including native destination, model, header/trailer and checksum.
- Reopened persistent component file size, full envelope SHA-256 and complete
  payload SHA-256. A payload is taken only from the persisted file's
  `bytes[32:-32]`, never substituted from a retained candidate or an old overlay.
- The flash manifest's canonical checksum, logical layout/geometry and both
  current and original envelope hashes. Original hashes must equal the exact
  initial component bytes required for that scenario.
- Native OSD program/readback followed by main program/readback. Every operation
  must return success, use the full component, reopen persistence and report
  the exact requested/current/readback bytes. The outer updater returning zero
  alone is insufficient.
- The native report's execution-time hashes of nine producer/dependency files
  and the pinned MN103 reader. Its instruction-map hash is reconstructed from
  byte-checked native listings against the actual executing main. Source drift
  before or during later qualification is rejected.
- Restoration's predecessor hash names the actual candidate installation
  result. Both pre-program hashes and flash initialization metadata must match
  that candidate generation.

The bridge builds the exact audited 15-span candidate overlay from these
persisted payloads. Its icons-only control uses the virtually written OSD. A
fourth restore overlay contains the same fifteen audited spans with zero byte
changes, derived from the actual restored stock payloads. Complete overlay
reconstruction must equal the persisted payloads, including bytes beyond the
resource prefix loaded by OM-Emu.

Four fresh sessions use the existing 41-frame action route: stock baseline,
icons-only control, installed candidate and restored stock. The unchanged
native-source qualifier verifies the first three sessions independently. The
bridge also checks the fourth session's actual loaded component hashes,
zero-change overlay, action/state/diagnostic history and exact stock pixels.
All PNG/RGB files and all loaded upstream modules are checked before and after
comparison. Source, package, flash, overlay, session and runtime inputs are
rechecked across the full qualification.

Processing-site counters being zero establishes only that this UI route did
not execute recipe processing after bring-up. It does not demonstrate rendering
of Gold/Portra recipes, photograph pixels or TruePic completion. The preserved
stock BMP_LUT diagnostics, unobserved icon resources, ART example compositor
and palette-dump limits remain visible in the original qualifier's report.

## Reproduction

With the exact private producer results and previously qualified inputs present:

```sh
python scripts/epl9_virtual_flash_ui.py run \
  --out local/NEW-virtual-write-ui \
  --candidate-result /absolute/path/to/PRODUCER/install-candidate/result-components.json \
  --restore-result /absolute/path/to/PRODUCER/restore-stock/result-components.json \
  --node /absolute/path/to/node-v26.13.0-linux-x64/bin/node

python -m unittest discover -s scripts -p 'test_epl9_virtual_flash_ui.py' -v
python -m unittest discover -s scripts -p 'test_epl9_native_source_ui_qualification.py' -v
```

Use an actual ignored local checkout at the pinned OM-Emu commit, not a symlink
to the checkout root: the unchanged observer's module URL scope must match the
actual loaded paths. Private firmware fixtures may remain read-only source
links. No upstream source is modified or published.

The official Node v26.13.0 executable SHA-256 is
`0adde40d1b7dfa57c8bc83cbc319758c3ec6ebba21363bb2fa752ea6b267ad1b`.
The pinned unchanged OM-Emu commit is
`147ca89c60b24774f3145c2813d79714e0f0b7b7`.

## Current evidence

The final run consumes producer `run-v4`, including its read-only reopen fix and
execution-time source receipts. All four fresh sessions and both qualification
layers pass under the revised input/source-byte binding below. The bridge's
first attempted launch rejected a changed preliminary
producer source before creating any session or frame; that failed log is not
qualification evidence.

Private evidence is under `local/virtual-write-ui-run-v2/`:

- `qualification-bound-inputs-v3/manifest.json`, the current qualification,
  SHA-256 `c5ab7fc1d4e8da446d2861edb3ad8ce2f36cf465507ce3a9e4a87c5f70460ddd`.
- `qualification-bound-inputs-v3/candidate-qualification/manifest.json`, from
  the unchanged original three-session qualifier.
- `qualification-bound-inputs-v3/frame-bindings.json`, binding all 164 PNG/native-RGB pairs,
  SHA-256 `59f6412f85a550f5a8699cc3be73f38f63d12f7ea3fd1bdbadda90d8b3f84553`.
- `selected-frames.json`, identifying unedited candidate frames 31, 32, 33, 34,
  38 and 39, plus restored-stock frames 32, 34 and 39.

Each session binds exactly 120 loaded pinned upstream modules and 41 frames.
Candidate and icons-only images match exactly. Ten frames differ from stock
only inside accepted icon regions. The six observed resources are `4387`,
`4388`, `4556`, `4557`, `A076` and `A077`; the other four retain the previously
declared coverage limit. All 41 restored-stock frames match the baseline's
native pixels, GUI/control history and complete diagnostic history. All six
post-bring-up processing-site counters remain zero.

Fresh images were visually inspected without pixel editing: the Picture Mode
list shows G200/P400 badges with unchanged Watercolor I/II labels, shooting views
show the appropriate Gold/Portra badge, and restored stock returns to the
original ART 12 I/II marks. The stock diagnostic baseline is preserved, not
described as error-free. This is UI qualification only.

Nineteen focused bridge tests and all 28 unchanged native-source UI qualifier
tests pass. The bridge tests cover failed/specimen status, mixed/historical
components, paths/symlinks, full-envelope/payload integrity, hidden native
program/readback errors, initial-snapshot rebinding and restored-session
overlay/pixel binding. Python compilation, Node syntax and whitespace checks
also pass. No complete hardware/firmware-system suite or physical installation
is claimed.

### Input/source binding corrections and retained history

Independent review found that the first bridge qualifier parsed session JSON,
then recorded a later file read. A session changed between those operations
could be accepted against the earlier in-memory document. The revised code
captures each session's raw bytes once, immediately records those exact bytes,
parses that same capture and checks the files remain unchanged at the end.
Overlay/bridge JSON and final session report records follow the same binding.

Review also found an adjacent running-source race: the bridge source hash was
checked at entry but a later source read supplied its snapshot/report record.
The revised code captures raw source bytes and their record once at entry,
requires that hash to equal the loaded source hash and retains the same record
through the final unchanged-input checks and report. Helper source checks also
validate and record the same read.

Both new full-qualifier regressions fail against historical commit `ab2bea5`
and pass the revised source. An additional authentic-copy control changed restored
frame zero's native RGB hash to zeroes during the first four-session runtime
dependency check. The revised qualifier rejects the changed session at its
final unchanged-input check. A second authentic-data control returns original
bridge source bytes for its entry check, then changed bytes for every later
read; the revised qualifier rejects that source drift too. No real source,
original session or PNG file was edited by either control.
The unchanged authentic frames were then requalified successfully, without
replaying the UI. Current bridge source SHA-256 is
`93513d2617d32d81b332e0642dc8ef09864b9a4b98ceef7a8d7d18118b6107ab`.

The earlier `qualification/` directory and report SHA-256
`dc600d14a8fc444e1359f03c1f3d2b053d8318b6755139a6e5dfa6bd3acb72cf`
are retained unchanged as historical evidence, not the current bridge
qualification. Intermediate `qualification-session-bound-v2/` is preliminary
because it preceded the running-source correction. The original source handoff
and mirror index are also retained;
revised source and qualification artifacts have separate names and indexes.
