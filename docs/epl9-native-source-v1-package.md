# E-PL9 native-source-v1 offline package qualification

## Result and boundaries

2026-11-11. The corrected native-source variant now has its **own encoded
main+OSD research pair**, strict container/source checks, native load/updater
checks and fresh offline UI evidence. It is generation `native-source-v1`, not
the earlier `frozen-v3` or `private-color-v3` package. All old defaults, packages,
recipe values and archived evidence remain unchanged.

No camera, card preparation, flash write, physical readback or restoration was
performed. The files remain private and Git-ignored. **Install readiness is
false.** This pass qualifies the stated offline boundaries; it does not require
or invent an ISP implementation that produces photographs.

Before source changes, clean `48bbe195f685941dd14e2c31693574c10388d56a` was
saved in a verified git bundle. New work is separate on
`feat/native-source-v1-package`. The published source-only ART/ISEQ branch is
preserved, and no original firmware or manufacturer binary is added to Git.

## Distinct files and retained identities

Files are under `local/cloud-native-source-package-20261111/package-final/`:

| Private research file | Bytes | SHA-256 |
| --- | ---: | --- |
| `Gold-Portra-v3-native-source-candidate.bin` | 52428800 | `10ac83e9beb9dd1bfd12aa6a021135706875d6ea245e58e20ec07fb917229421` |
| `Stock-1101-main-osd-restore.bin` | 52428800 | `10a7b949d1509ce627cb3c098c0a01a8ae5758fb2ce84b6c887e34b46e349387` |

These filenames are not qualified camera-card/loader delivery names. Each file
selects exactly main `0100` followed by OSD `0101`; each component is 26214400
bytes including its 64-byte envelope. The return file contains the exact original
encoded components. It covers the changed main/OSD, not device-specific settings,
calibration or every component of the downloaded update.

Olympus E-PL9/IM008, model bytes `1330`, owner-reported body 1.1, downloaded
build 1101. The source is not a readback of the installed body:

- Stock update: 104552480 bytes, SHA-256
  `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`.
- Stock main: `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
- Stock OSD: `ee9a9c3ad1974dd212483ca7d012e51ae23083ce0119589a3b42996aa13ccf1e`.
- Corrected native-source main:
  `2d003930675b47774e9ed3535ee49c64f56ff519bd6f1a33ddafd1a8c688b9b7`.
- Corrected 15360-byte module:
  `89803a465ae76a81ae6b10055f0b8ff67dc30a1f162785bd8ee4f97e1c70d6e3`.
- Unchanged accepted icon OSD:
  `50141904c211fd16bc4c26b35cd52955f96a9e611ca062d84fe0169eeda21b3b`.

Both decoded components are 26214336 bytes. The new main includes the relocated
WB hook at `60761c9e` and the consistent source allowlist described in
[native-source gates](epl9-native-source-gates.md). It is never silently accepted
as either historical v3 main. Frozen/private-COLOR mains remain
`501707d0…f65686` / `72cc1e48…71beee`; their encoded candidate packages also
retain their prior exact identities.

## Container and source reproduction

`scripts/epl9_native_source_package.py` is a separate builder. It does not
extend or weaken the historical generation selector. It requires the exact
stock, corrected main/module, accepted icon OSD, reconstruction manifests,
recipe files and private v3 RGB input.

It reassembles all three module/main generations from source and reproduces
their pinned hashes. Every module byte from offset 4096 onward is identical
between frozen/private/native-source variants. No numerical recipe was changed.
The exact private v3 RGB input is pinned to
`915f5cfd5d89d78a01b36b386bcab4e874ffc664b7de8017c9f0f9cf92c6a1cb`.

Fifteen disjoint, exhaustive spans account for every decoded difference from
stock: the module, four hooks and ten accepted icon resources. Original bytes
are guarded, and seventeen updater/startup ranges stay stock. The builder
preserves original header/trailer metadata, model/build, destinations and
lengths, changing only the encoded payloads and checksum fields as required.

The strict host parser and independently pinned
[oly_fw_analysis container parser](https://github.com/fishcu/oly_fw_analysis/tree/539fcf1fa9eda5fdef8ede4deeab94a4691d94c3)
recover the intended decoded payloads and reconstruct the complete stock,
new candidate and return files bit-for-bit. External implementation source
remains an ignored reference, not copied into this project. Changed/missing,
extra, reordered or old-generation inputs are rejected.

The package directory also retains decoded-overlay evidence, manifest,
qualification status, checksums, authored module assembly and a deterministic
private source/RGB archive. Preparatory `package` and `package-repeat` outputs
were reproduced identically and retained. The final archive is generated only
after all new deployment/UI sources and this report are staged. It contains
project sources, exact private RGB input, the two pinned reconstruction
metadata JSONs and authored module assembly, each byte-verified and hash-recorded.
Original firmware, decoded/encoded binary components, overlay vendor bytes,
Node, OM-Emu and other upstream implementations remain separate inputs.

## Native early load and updater boundaries

`scripts/epl9_native_source_deployment_probe.py` extracts the executing main
from this exact candidate package. Stock-return tests therefore execute the
corrected main, never an older frozen/private substitute.

- The native early planner copies all 657408 bytes in three declared local reads:
  65536, 524288 and 67584 bytes. The complete module and destination guards match.
- Native section 2 plans 2871296 bytes from `8094f800` to `a066f800`, containing
  all four exact hooks. Its destination interval is `6066f800..6092c800` in the
  cached mapping. Every hook's local loaded bytes match this generation.
- Dropping the final read, truncating source by one byte or shortening the
  destination is rejected. These are controlled local failures, not NAND faults.
- Twenty audited startup/section/updater source windows remain stock. Known
  later load/initialization intervals exclude the module; all runtime writers,
  physical cache/DMA and full boot remain unqualified.
- Sixteen full-size native validator cases pass their exact expected outcomes,
  with ten full-state accelerated/unaccelerated loop crosschecks. Permutation,
  inversion and checksum acceleration retains the final native iteration.

Native mode 2 validates with no write requests; mode 0 and the separate mode 1
consume the checked bytes and request the expected two components. Backend
calls stop at a RAM-only trap with declared return/error values. Corrupting
either encoded component is rejected with 3211 before any write request.
No physical programming/readback leaf is executed.

The unchanged native order is OSD first (`421e0000`), then main (`806e0000`).
The known error limitation remains: injected OSD 3105 followed by main 0 can
produce final 0. A success indication therefore does not verify that both
components were physically written. The return package is a verified file,
not demonstrated recovery after a failed boot.

## Fresh UI qualification for these exact bytes

New stock, icons-only and corrected-candidate runs each completed 41 frames.
They use unchanged pinned OM-Emu commit
`147ca89c60b24774f3145c2813d79714e0f0b7b7` and official Linux Node v26.13.0.
The Node executable SHA-256 is
`0adde40d1b7dfa57c8bc83cbc319758c3ec6ebba21363bb2fa752ea6b267ad1b`;
its release archive was checked against the official SHASUMS256 file.
System Node v24 was used only for a separate feasibility smoke, not qualification.

The host observer adapter pins the unchanged UI runner, parses the exact hashed
patch bytes with the upstream parser, binds written PNG/RGB bytes and runtime
dependencies to session metadata, and observes relocated WB site `60761c9e`.
It changes neither firmware nor CPU/device behavior and supplies no successful
return model. Current overlays are replayed against pinned stock and all frame
hashes are checked before and after comparison. Preparatory UI reports with
weaker artifact binding are retained but are not the final qualification.

Actual OM-Emu patch summaries bind the corrected main hash above and the icon
resource-prefix hash `e492fa2c…44bc`; the full OSD is independently rechecked.
Candidate frames match icons-only pixels exactly. GUI states, actions and
complete diagnostic histories match stock. Ten frames differ from stock only
inside accepted icon regions; six of ten resources are observed and visually
checked. G200/P400 badges appear while labels remain Watercolor I/II. Large
example images and unrelated modes remain stock.

All six processing-site counters, including `60761c9e`, stay zero after
bring-up. This route does **not** exercise recipe processing or TruePic output.
The three exact stock BMP_LUT diagnostics are retained and matched, not called
error-free. Four resources, the ART-dial large-example compositor and the E133
palette-dump gap remain outside the demonstrated UI coverage.

## Reproduce and interpret the separate reports

With the exact separately supplied private inputs restored into their recorded
paths, build to a new ignored directory:

```sh
python scripts/epl9_native_source_package.py --generation native-source-v1 --out local/NEW-native-source-pair
python scripts/epl9_native_source_deployment_probe.py --packages local/NEW-native-source-pair --out local/NEW-native-source-deployment
python scripts/epl9_native_source_ui_qualification.py prepare --out local/NEW-native-source-ui-overlays
```

For UI replays, use the pinned Node executable and passive adapter:

```sh
NODE=local/cloud-native-source-package-20261111/ui-toolchain/node-v26.13.0-linux-x64/bin/node
actions=(s1 menu right down ok)
for i in $(seq 1 27); do actions+=(down); done
actions+=(ok menu menu ok down ok menu menu)
$NODE --max-old-space-size=6144 --import ./scripts/epl9_native_source_ui_observer.mjs scripts/epl9_omemu_ui.mjs local/NEW-ui-stock - "${actions[@]}"
$NODE --max-old-space-size=6144 --import ./scripts/epl9_native_source_ui_observer.mjs scripts/epl9_omemu_ui.mjs local/NEW-ui-icons local/NEW-native-source-ui-overlays/icons.json "${actions[@]}"
$NODE --max-old-space-size=6144 --import ./scripts/epl9_native_source_ui_observer.mjs scripts/epl9_omemu_ui.mjs local/NEW-ui-candidate local/NEW-native-source-ui-overlays/combined.json "${actions[@]}"
python scripts/epl9_native_source_ui_qualification.py qualify --out local/NEW-ui-qualification --overlays local/NEW-native-source-ui-overlays --stock local/NEW-ui-stock --icons local/NEW-ui-icons --candidate local/NEW-ui-candidate --node "$NODE"
```

Authoritative evidence for this pass is:

- `local/cloud-native-source-package-20261111/package-final/manifest.json`.
- `local/cloud-native-source-package-20261111/deployment-package-final/manifest.json`.
- `local/cloud-native-source-package-20261111/ui-v4-qualification/manifest.json`,
  `ui-comparison.json` and `frame-bindings.json`.
- `local/cloud-native-source-package-20261111/final-qualification/summary.json`
  joins those exact generation/component/report identities without replacing
  their individual scope statements.

All 427 source tests pass. Compilation, Node syntax and whitespace checks pass.
The final UI evidence binds all 123 PNG/RGB files and 120 loaded upstream modules
per run; altered overlays, frames, runner or runtime source are rejected.
Earlier preparatory package/UI/native outputs remain intact and distinct.

The builder's manifest intentionally reports native/load/UI as pending **separate
evidence**; it is not overwritten to pretend the builder performed those stages.
Use the final deployment and UI reports alongside its exact hashes. Historical
frozen/private integration seals are not recreated or relabeled.

Remaining gates are generation-specific readback references and safe acquisition,
entry/delivery/recovery on this body, physical module/cache/DMA lifetime,
unqualified owners/IRQs and full processing/completion. Existing readback CLI
references still select the two old generations and must not accept this main
under either name. Camera rendering and switching are later hardware tests;
none has occurred here. No camera installation instructions or ready firmware
release are supplied by this work.
