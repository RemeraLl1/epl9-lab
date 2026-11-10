# E-PL9 active Workspace gamma, 2026-11-07

## Measured result

The owner currently has only computer access. Actual OM Workspace 2.5W exports identify **CMIO T+0xde6** as an effective shared gamma table for the tested ORF/settings. The earlier T+0xbe6 experiment selected an ineffective slot in this path. This is software-renderer evidence, not camera TruePic execution, a completed native frame, or an installable firmware patch.

Fresh Natural, Gold v2 and Portra v2 exports are pixel-identical to the previous exports (zero differing pixels for each pair). All are 4608 x 3456 RGB8 TIFFs with matching ICC profiles. Gold v2 versus Natural differs in 99.686981% of pixels, MAE 9.179635/255; Portra v2 differs in 100%, MAE 14.246149/255. These remain uncalibrated draft looks.

## Exact inputs

E-PL9, owner-reported body 1.1; downloaded main build 1101, not an installed-camera dump:

- Container `OLY_E_133_1101_0000_0000.BIN`: 104552480 bytes, SHA-256 `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`.
- Decoded main: 26214336 bytes, SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`, base `0x60400020`.
- Original E-PL9 ORF: 14149062 bytes, SHA-256 `9b45532e0935220701e8abd4e5d7c66b66c9e3ffc713885c82eb201e2d7a3b4a`.
- Installed OlyLoquat.dll: 2656440 bytes, SHA-256 `8bea01d0be6d5a5be9bf09407579ced7654831c0ce109864e1c23f092a822d06`.

## Runtime observation and isolation

`workspace_execution_sample.py` sampled executing instruction pointers during an ordinary export: 19 OlyLoquat samples in cmdBatch.exe and one in Workspace. OlyHydrangea and OlyImgProc2 also executed. This establishes actual participation, not a complete call trace. RVA 0x8d690 is a halfword copy loop; RVA 0x4a2cc lies inside output conversion routine 0x49e20..0x4a4d0, not a demonstrated film operator.

The sampler targets only Workspace executables in their installed directory, briefly suspends individual threads, reads the instruction pointer and resumes each successful suspension in finally. It does not inject code, write memory or set breakpoints. Idle sampling had no errors. Export sampling retained 65 failed thread opens, one failed suspension and two unmapped IPs during thread/process churn; these are misses, not successful evidence. All exports completed.

Each separate control replaces just one 512-byte decoded table with the existing linear table at T+0x9e6 / ROM 0x608c35e4 (SHA-256 `0f63c5ff71faf9fb002272de6fb38485eb45bb0abc761d2032b2ac0761297218`). Full decoded T, encoded boundaries including recurrence trailing byte, unchanged P, RAW layout and RAW bytes are checked.

| CMIO T | Exact firmware address | TIFF versus stock |
| --- | --- | --- |
| 0xbe6 | 0x608c37e4 | Zero different pixels |
| 0xde6 | 0x608c39e4 | All 15925248 pixels differ; MAE 77.210960/255, max 169 |
| 0xfe6 | 0x608c3be4 | Zero different pixels |
| 0x11e6 | 0x608c3de4 | Zero different pixels |

The fresh stock control also exactly matches the previous Natural pixels. Linear substitution is a strong diagnostic, not a film recipe. Original files and embedded previews remain unchanged.

Loquat VA 0x18003f299..0x18003f2ca selects these four offsets. Its version check at T+0x9d3 matches the actual decoded T bytes; it does not imply a shifted block base. Selection depends on interface methods +0x2e0 and +0x1d8. Their semantic interpretation and applicability to other settings remain open; do not label them color-space/output-depth flags without evidence.

## Owner-exported v3 pair: active curves confirmed

The owner requested manual GUI operation after the controls finished. No further GUI input was issued. `local/epl9-film-drafts-v3-20261107/` contains:

- `gold200-draft-v3-active-gamma.ORF`, SHA-256 `afa9d0c918839a801f48f6873a7baa5d2579c30b7c872b3fdbb3919ea50b02e4`.
- `portra400-draft-v3-active-gamma.ORF`, SHA-256 `81ee3c058914ecddb0089ec4b8e375129e4532ec1a0fa4ea34bf0417fd82cd03`.

Each inherits v2 HSL/WB/contrast/H/S/M unchanged and composes the existing v1 remap with active T+0xde6. Only that table changes. The owner exported both at full size on November 7. Geometry, RGB8 depth and embedded ICC match v2.

| v3 versus matching v2 | Gold | Portra |
| --- | ---: | ---: |
| Changed pixels | 15,769,841 / 15,925,248 (99.0241%) | 15,925,248 (100%) |
| Mean absolute channel difference, /255 | 5.090435 | 7.704762 |
| Maximum channel difference | 15 | 16 |
| Newly zero channel samples | 20,739 / 47,775,744 (0.0434%) | 0 |
| Newly 255 channel samples | 2 | 0 |

Gold lowers the weighted RGB code-value mean of the original 0..32 band from 19.32 to 15.98, and raises the 128..192 band from 154.03 to 161.83. Portra raises the same bands from 17.50 to 27.21 and 153.48 to 160.12. These are display-code proxies, not linear-light luminance or calibrated perceptual measurements. New zero channels do not necessarily mean fully black pixels. Neither source has pixels in the 224..256 weighted-code band, so this portrait does not qualify highlight roll-off.

Visual review confirms stronger contrast/warmth in Gold and lifted, flatter tones in Portra. The indoor portrait alone does not establish film accuracy; Gold's warmth and Portra's lifted appearance need review across scenes. Detailed evidence and the six-panel comparison are in `local/epl9-film-v3-review-20261107/`; Natural comparisons are in `local/epl9-film-v3-pixels-20261107/`. Gold TIFF SHA-256 is `731843a442a32a1451cbf1f90e60629c22faf67a69894cb60865f227e7158018`; full hashes for both are retained in `review.json`.

## Eight additional owner scenes and automatic Python workflow

The owner supplied `local/cloud-colour-v3/RAW-originals/` (eight E-PL9 ORFs). Existing neutral ORFs/TIFFs are available beside that directory. `scripts/epl9_film_scene_batch.py prepare` reproduces each neutral ORF byte-for-byte before accepting its exported TIFF as a control, then prepares both v3 recipes. All 16 results retain byte-identical RAW strips and LibRaw-decoded mosaics. Only qualified metadata/CMIO spans change, including normalization of the copied PictureMode to Natural; originals and embedded previews stay untouched.

One input has distinct captured/auto WB vectors: `[558,444,256,256]` and `[508,480,256,256]`. The old single-frame helper intentionally rejected this case. The opt-in batch path now scales each existing vector independently, preserving both green reference values. Gold produces `[603,391,256,256]` / `[549,422,256,256]`; Portra produces `[578,417,256,256]` / `[526,451,256,256]`. The legacy helper remains strict by default. This preserves the distinction; it does not prove which vector Workspace selects in every WB mode.

Prepared files and complete source hashes: `local/gold-portra-scenes-v3-20261107/manifest.json`, 16 ORFs totaling 229929448 bytes. All 16 owner exports were subsequently read successfully and compared automatically. Each matches its own control's 3456 x 4608 geometry, RGB8 depth and ICC. Seven neutral TIFFs are Adobe RGB (1998); the eighth is sRGB. Numeric comparisons retain each pair's common ICC space, without implicit conversion; only review panels convert to sRGB.

The measured batch and eight three-column review panels are in `local/gold-portra-scenes-v3-review-20261107/`. Changed-pixel fractions range from 99.789% to 100% for Gold and 99.883% to 100% for Portra versus the COLOR-neutral control. This establishes effects of the **complete recipes**, not the isolated contribution of gamma on every scene.

Visual review exposes Gold's yellow cast in nominally white clothing, excess warm skin under already warm illumination, and darker colored shadows. Portra is substantially flatter/lifted in foliage and stage scenes. The strongest measured endpoint effects are:

| Scene | Gold new zero channels | Gold new full-scale channels | Portra new zero channels | Portra new full-scale channels |
| --- | ---: | ---: | ---: | ---: |
| Outdoor white clothing / foliage | 0.2748% | 0.0830% | 0 | 0.0066% |
| Warm-lit couple / bright window | 0.6851% | 0.0715% | 0 | 0.0009% |
| Saturated stage lighting | 3.3098% | 0.0764% | 0.0007% | 0.2626% |

Percentages count newly clipped **channel samples**, not fully clipped pixels, relative to each neutral TIFF. They combine WB, HSL, contrast/H/S/M and gamma effects; they are not an isolated curve-loss measurement. Several scenes now contain substantial bright bands, but their inconsistent responses do not justify a blanket highlight-protection claim. v3 is retained as a measured baseline, not a final film calibration.

Four additional controls in `local/gold-portra-gamma-profile-controls-20261107/` restore only T+0xde6 in the existing v3 ORFs, for one Adobe RGB and one sRGB scene and both recipes. Applying the remap again exactly reproduces each source ORF byte-for-byte. The owner exported all four, and their measured comparisons in `pixel-results.json` confirm the slot is active in **both tested profiles/settings**:

| Isolated gamma versus matching stock-gamma control | Changed pixels | MAE /255 | New zero channels | New full-scale channels |
| --- | ---: | ---: | ---: | ---: |
| Adobe RGB, Gold | 99.7765% | 4.389912 | 71,633 | 12,476 |
| Adobe RGB, Portra | 99.6754% | 7.802867 | 0 | 759 |
| sRGB stage, Gold | 99.9674% | 4.100224 | 209,273 | 3,491 |
| sRGB stage, Portra | 99.9266% | 7.856915 | 122,361 | 6,201 |

The stage Portra curve introduces 15,381 red, 106,854 green and 126 blue zero-valued channel samples relative to its stock-gamma control, while neither image has fully black pixels. A raised monotone shared curve therefore does not by itself guarantee absence of channel clipping through the complete downstream color pipeline. The exact operator responsible for this interaction is not isolated here. In particular, the complete-recipe versus neutral clipping counts and the gamma-only counts have **different controls** and must not be conflated. No additional export is pending for this pass.

**Owner decision, later November 7:** retain the pronounced v3 character, including some additional Gold warmth; the two looks should remain distinct. Only modest defect correction is wanted. Freeze v3 for integration and make readiness for the first camera test the primary task. Broad color fitting and the other 29 recipes are outside this integration pass. The endpoint measurements remain valid observations, not an instruction to flatten the accepted looks. Independent RGB curves or matrix/six-axis recipes require their own transport and pixel tests; passing this shared-gamma test does not establish them.

The existing `local/cloud-colour-v3/run_scene_batch.py` and v4 `run_batch.py` consume already-developed neutral sRGB TIFFs, not RAWs. Their 29-profile catalogs explicitly exclude G200/P400. The newer kit identifies source commit `5aedd78e71a0747fa19edb9e2f848737201bb138`. Their postprocessing is useful for other looks but is not a TruePic emulator or an implementation of these two native recipes. No files in those snapshots or their existing outputs were modified.

## Native gamma adaptation and configuration checks

Fresh exact-image disassembly distinguishes the selected stock bases. Native selector `0x6079d328`, variant helper `0x607a3d87`, and index helper `0x6079d2d1` use normal pointer table `0x608ff65c`. Its eight words are:

```
608c37e4 608c39e4 608c37e4 608c97e4
608c37e4 608c39e4 608c37e4 608c97e4
```

All four zero-variant entries are `0x608c37e4`; the tested Workspace export uses `0x608c39e4`. Native variant selection uses request byte +48 with the format-dependent bit selection shown by the helpers. The current film hook requires that byte to be zero. Semantic names for these flags and other selector states remain unqualified. Gradation and other special branches also exist; the table alone does not qualify those paths.

`epl9_workspace_gamma_probe.py --native-curves` now composes the same authored output remap with the native `0x608c37e4` base. It does **not** copy the Workspace `0xde6` table into the native module. All three native slots receive the same curve, so this trial does not depend on a physical RGB channel-order assignment. Gamma records and provenance are in `local/epl9-native-film-curves-v3-20261107/`.

The adapted curves passed `epl9_film_late_probe.py` at module base `0x604a1300`: 40 frame configurations, 24 original-key crosschecks, nine cache transitions, 15 passthrough cases, 275 WB boundary cases, 120 worklist routes, 1050 flag routes and 12 connected jobs. Requests are restored and other tested modes leave film configuration correctly. Connected jobs still stop before hardware completion; host resource contracts remain explicit. No output pixels are invented.

This is a separate **gamma/WB configuration experiment**, using existing HSL/tone recipes and stock matrix/six-axis data, not a replacement for the prior diagnostic matrix/owner qualification candidate or a finished calibration. In `local/epl9-native-film-curves-probe-20261107/`, the 15360-byte module (1646 code bytes) has SHA-256 `18f17217c96d0ef7b6cd767f9738825ed9913a0df32435358237304f3f6a73a9`; the 26214336-byte offline decoded main has SHA-256 `501707d09a0eb648e46196752b7ece17cd5368f6d54dbabce7c73e9806f65686`. No updater container was created. Independent RGB curves, calibrated matrix/six-axis controls, hardware pixel equivalence, concurrent runtime behavior and installation readiness remain open.

The new batch/WB unit checks pass (14 tests); real batch preparation also checks each final mosaic, both WB fields and the untouched source hash. The native probe passed using the pinned reader outside the Windows DLL sandbox restriction.

## Evidence and checks

- `local/workspace-engine-probe-20261107/`: baseline exports, runtime samples, repeat-pixels.json.
- `local/workspace-engine-pixels-20261107/`: baseline metrics/contact sheet.
- `local/workspace-gamma-slots-20261107/`: four isolated ORFs/TIFFs, stock control and manifest.
- `local/workspace-gamma-pixels-20261107/`: all-pairs metrics/contact sheet.
- `scripts/epl9_workspace_gamma_probe.py`: bounded control and film-trial generation.

All 15 existing workspace transport/pixel tests pass with temporary files under the writable local project directory. An initial run failed two tests on sandbox temporary-directory permissions; rerouting the temporary directory resolved them. Control generation assertions and actual exports passed.

The [official E-PL9 manual](https://download.omsystem.com/pages/inst/epl9/manual_epl9_ENU.pdf), page 115, documents RAW Data Edit using Current settings or ART BKT; it does not promise that altered CMIO supplies camera settings. E-PL9 is absent from the [Workspace USB RAW support list](https://software.omsystem.com/omworkspace/en/). The pinned OMEmu work still has no qualified ISP pixel executor. Real camera output and native end-to-end completion remain unverified.
