# Project status: 2026-11-08

Latest source progress: [explicit native v3 input binding](epl9-native-v3-input-binding.md)
removes the late builder's hard-coded v0/v2 data dependency when a complete
hash-pinned native bundle is provided. It also supports separate midtone
biases for both slots while preserving historical same-number emitted bytes.
No actual final v3 data, complete install/stock-return package or camera
result was supplied by this change.

**Native offline integration and partial native-menu UI integration now exist. The install/stock-restore package work is active; the first physical camera integration has not occurred.** No on-camera Gold/Portra image, complete modified-job ISP cycle or universal recovery path is established.

Start with [first-integration readiness](first-integration-readiness.md) for the concrete milestone and blocking checks. "Closer" means the work has advanced from isolated host experiments to emitted native hooks, owner binding, candidate loading and controlled emulator UI results. It does not support a percentage, ETA or claim that preparing a file makes installation safe.

![Evidence map separating desktop rendering, native configuration and physical installation](../assets/docs/research-progress.svg)

## Evidence reviewed

- Published baseline: main `1f4dc523fc8db1a61863da66a09413627d5eb8e8`, including native integration, WB/placement, producer/owner fixes and the November 7 OM-Emu icon validation.
- Active integration, recipe-review, SD-loading, video, Wi-Fi and recovery chats were checked on 2026-11-07. Unpublished reports or private recipe inputs remain explicitly reported evidence, not source delivered by this checkout.
- The November 7 synchronized cloud snapshot passed **147 Python unit tests**. The November 8 native-input and ART-gate changes pass **164 available tests**; full discovery currently fails at the absent pinned external OSD decoder's setup, leaving five OSD tests unrun. Historical Windows-wide totals and narrower selected suites belong to their recorded runs. No exact-image probe, OM-Emu session, private TIFF export, full-size package audit or physical-camera test was rerun for this update.
- All firmware-specific published work identifies E-PL9 1.1/build 1101, downloaded stock input rather than an installed-body dump. See [exact input identity](epl9-1.1-initial-findings.md#exact-stock-input).

## What has been established

| Area | Current evidence | Remaining limit |
| --- | --- | --- |
| Native recipe hooks | [Emitted module](epl9-native-film-module.md), followed by [late integration](epl9-late-film-integration.md), replaces earlier Python-only interventions in bounded checks. | Earlier early-object strategies are historical; machine-code execution is not physical-camera execution. |
| Stock ART producer and owners | [Producer/binding checks](epl9-native-owner-binding.md) found and fixed the missing exact `0x1000` request-kind gate. Tested positive and pre-cancelled paths preserve their contracts. | Remaining creator/resource callbacks, real task/interrupt behavior, concurrency and full output ownership are not exhausted. |
| WB, placement and loading | [Math/placement](epl9-wb-math-placement.md) and [owner/load](epl9-native-owner-load-validation.md) execute selected native logic and planned early load chunks around `0x604a1300`. | Inferred WB leaves, runtime writers, cache/coherence and physical storage behavior remain scoped assumptions. |
| Native pixel boundary | Connected positive cases reach `0x6073eafa → 0x9880014c`; the configuration prefix produces no finished pixels or completion signal. | Actual sensor/TruePic/DMA execution and preview/capture/save behavior are not supplied by the host models. |
| Desktop images | [CMIO controls](epl9-workspace-cmio-bridge.md), [v0 color](epl9-film-draft-trials.md) and [v2 tone/WB](epl9-tonal-neutral-trials.md) provide published full-size TIFF evidence. V1's isolated gamma edit has no observed effect. | Current v3 multi-scene review is reported separately; native camera/desktop equivalence and calibrated film fidelity are not established. |
| Icons and native GUI | [OM-Emu validation](epl9-omemu-ui-validation.md) corrected row-crossing RLE and compared three 41-frame routes. Six target resources appear in three screen contexts. | Two bitmap pairs and the ART/example-screen format gap remain untested; all five processing-hook counters are zero on the GUI route. |

## What is being worked on now

The integration chat is preparing an install candidate and exact stock-return package for the selected **Gold/Portra v3 direction**, with the recipes held fixed. Its stated write set is main plus OSD/icons; existing large ART example photographs remain unchanged. Full-size native-validator checks with writing intercepted are planned/in progress. A passing exact package report is not yet published in this baseline.

The latest recipe-review chat reports comparisons across eight scenes and prefers Gold/Portra's coherent color/tone character to much of the separate 29-recipe library. Gold can over-warm neutral/skin areas and Portra can create haze in dark foliage. This is reported desktop/visual review, not a license to retune those two frozen recipes or a claim of camera calibration. The public numerical files here remain v0/v1/v2; final v3 source/data bindings must be identified in the package manifest.

The owner prefers a possible later hybrid library: most recipes built in, with some SD-backed/open slots. Exact numbers and mapping are undecided. A 29-recipe workstream is not 29 implemented camera slots. The immediate priority is still the two Watercolor replacements, not an SD loader or broader menu redesign.

## Other reported work, separate from the first package

| Direction | Reported finding / current task | Boundary |
| --- | --- | --- |
| SD recipe loading | Investigate a model-specific loader, retained RAM tables and built-in fallback after the two-slot baseline works. | Not implemented on E-PL9; E-P7 formats/timing are reference material, not compatibility evidence. |
| Wi-Fi | Native rd trials preserve ORF/MOV bytes with much less copying; an ISC reuse model reduces resource creation while retaining waits. | Published source and real timing still needed. Sector-success and stale-response semantics remain unresolved; no measured speedup. |
| 4:3 video | Aspect handlers reportedly retain 1920×1440 in some paths, but fixed 1920×1080 branches and source-mode fields still need connection to normal FHD60 selection. | Full sensor field at 60 fps, hardware readout and video-buffer/MOV timing are unproven. |
| Gyro | Diagnostic access and timing/owner leads remain under investigation. | Raw rate, video synchronization, drops and recording-time logging are not established. |
| Recovery/USB | The native SD validator/service has reported intercepted-write checks; MTP filtering and a diagnostic-session entry have been investigated separately. | No verified full BOOT/flash dump tool, harmless service-session entry or independent rescue path after main corruption. |
| Broader color/library | Selected deeper controls now have independent native integration checks, while the separate library is being reviewed for character. | Diagnostic matrices/RGB/six-axis values are not final photographic recipes; changes to Gold/Portra are frozen during packaging. |

Expected originating-workspace reports include `epl9-v3-integration-status.md`, `epl9-installation-recovery.md`, `epl9-board-readout.md`, `epl9-wifi-offline-prototype.md`, `epl9-opengate-video.md` and `epl9-video-timing-sync.md`. Those filenames are not links to files supplied here. Preserve source provenance and pending-artifact status when integrating them.

## Decisions and next milestone

- **First scope:** the two Watercolor replacements and their small icons. Keep stock large example photographs, and do not claim renamed labels: the current native-GUI result retains Watercolor I/II text.
- **Next milestone:** bind the exact frozen v3 inputs, audit full candidate and matching stock-restore containers, and document remaining runtime/update-entry/recovery limits. See the [readiness gates](first-integration-readiness.md#before-calling-a-package-a-first-test-candidate).
- **First hardware test:** a future explicitly scoped session. Successful offline code, emulator menus and a stock BIN do not establish safe installation or universal recovery; risk probability is unknown.
- **Paused:** [Log, 10-bit and HEVC](log-ten-bit-handoff.md). Do not resume automatically.

The [directory index](README.md), [scope](research-scope.md), [installation plan](firmware-installation-plan.md) and [changelog](../CHANGELOG.md) carry these decisions forward. Older experiments remain dated history; their earlier next steps and test counts are not the present whole-project status.
