# Caduceus atlas: actionable E-PL9 crosswalk
Date: 2026-11-12. Documentation-only study; no firmware or patch generation.

## Result
Caduceus's E-P7 atlas is useful as a search vocabulary and a map of subsystem contracts, not an E-PL9 address table. No new E-PL9 symbol correspondence was binary-qualified in this study. The E-PL9 locations below are **previously established in this repository**, compared by role, not outputs of a fresh signature run. The frozen Gold/Portra candidate is unchanged.

Sources:
- [E-P7 atlas](https://github.com/cakelesscoder/caduceus-ep7/blob/main/docs/ATLAS.md), reviewed on the date above; see repository history for evolving content.
- [Mapping workflow](https://github.com/cakelesscoder/caduceus-ep7/blob/main/docs/RE_HANDOFF.md).
- [Body status](https://github.com/cakelesscoder/caduceus-ep7/blob/main/docs/BODIES.md): E-PL9/E-M10 III are not analysed by that project.
- [Licence](https://github.com/cakelesscoder/caduceus-ep7/blob/main/LICENSE) and [NOTICE](https://github.com/cakelesscoder/caduceus-ep7/blob/main/NOTICE).

## Useful role correspondences

| Area | E-P7 atlas evidence | Existing E-PL9 evidence | Consequence |
|---|---|---|---|
| SD trigger | HLS_EVENT 0x6076fdb6, trigger tracker 0x602c818c, event manager task ID at +172 | HLS_EVENT 0x60ae1c12, event-get call 0x60ae1c6e -> 0x60ae2073; manager +172 | Use an ordinary task/event adapter, not file I/O inside a pixel hook or IRQ. Does not identify the Delete event. |
| SD services | File calls are synchronous RPC to FILECLBK; FILEFGND must not block waiting on it | E-PL9 native wrappers/classifier reach RPC 0x60434a21; modeled service, not physical card | Trace task ownership and callback dependencies before expanding the bank loader. |
| Mount readiness | E-P7 media status at 0x61fa8fb8 | E-PL9 SD-specific status 0x6239914c, setter 0x60aef921; expected 0xf000 | Do not import the E-P7 status address or confuse another medium's readiness with SD. |
| Updater client/service | 0x60c95bab / 0x60c96030, E142 pattern | 0x610039fd / 0x61003e85, E133/S133 patterns | Model identity and routing are distinct. Similar code does not prove physical button entry. |
| Update write | E-P7 main written last, no rollback; flash_write 0x600c4f35 | Shared updater 0x6100440a, selector 0x604a0f8b, readback wrapper 0x6043a0d9 | Continue independent persisted-data verification; final return code is not installation proof. |
| ART/movie | E-P7 request +14 type, separate request_pack_movie 0x60355409, gamma selection depends on type | Our native-source gates depend on request/source/type/selector and are intentionally narrow | Trace each recording request into WB, COLOR and gamma; do not assume a visible ART icon means all hooks execute. |

Local evidence:
[SD loader](epl9-sd-loader-prototype.md), [SD lifetime](epl9-sd-placement-lifetime.md),
[recovery](epl9-installation-recovery.md), [native-source gates](epl9-native-source-gates.md),
[ART routing](epl9-art-routing.md).

## ART and video: the especially valuable distinction
E-P7's atlas describes a shared job constructor for stills, live view and movie, but also different request packers and type-dependent gamma columns. Its movie-stream colour route is explicitly only partly traced. Therefore even E-P7's atlas does not imply that every still effect runs on recorded video.

For our E-PL9, inspect native producers of request type and source, then the colour builder, gamma selection/upload, cache invalidation and eventual encoder input. Compare saved output eventually, not only preview. Heavy CPU grain/halation are distinct from ISP colour tables and should not be grouped together. Caduceus v0.31c disables Grain/Glow/Art/Halo in Movie/AP; this is a warning about those paths, not proof that all colour recipes cannot work in video.
[Release](https://github.com/cakelesscoder/caduceus-ep7/releases/tag/v0.31c).

## OpenGate
The atlas provides names for REC_START/REC_FREE, stream-job retrieval, exposure tasks, job buffers and queue/mailbox machinery. These are search leads for a full lifecycle, not a resolution-unlock recipe. E-PL9 already has a deeper, model-specific timing investigation:
[OpenGate](epl9-opengate-video.md), [timing](epl9-video-timing-sync.md).

The next comparison should follow source allocation, render ownership, encoder submission, output tags and drain/restart with the requested 1920x1440/60 parameters. A modeled allocation or successful UI selection does not demonstrate sensor full-field readout, valid pixels, physical memory throughput or 60 independent exposures. Do not replace these contracts with E-P7 offsets.

## Delete and SD bank
Use the E-PL9 key/event path to distinguish shooting idle, capture, review and playback. Preserve playback deletion and suppress key-repeat bank switching. The button event should request a task-context load; it should not synchronously invoke SD reads in an unknown callback. Retain the prior bank until a complete valid new bank can be published. The previous SD ownership and quiescence limits remain open; a host reference model is not an installed adapter.

## Gyro
The atlas is primarily a map of the main program. E-PL9 gyro research includes a separate stabilizer component, with a different CPU base and channels. Do not treat an orientation setting or exposure-task name as a raw gyro logger. Existing [gyro report](epl9-gyro-logging.md) identifies diagnostic CSV and controller leads but not a calibrated, synchronous timestamped XYZ stream. Match component identity, clock, channel units, sample provenance and exposure linkage separately. No new gyro capability is established by this atlas study.

## Reproducible mapping plan
1. Keep exact official E-P7 and E-PL9 inputs private; record sizes and SHA-256. Use exact decoded main components, not their container addresses as CPU bases.
2. Review a pinned Caduceus checkout and its dependencies/licences before running tools. Keep that checkout under ignored references; do not vendor it under our authorship.
3. Use the documented bootstrap on the E-PL9 input with --no-ghidra initially, explicit E-P7 input, and a private output directory. The E-PL9 main base currently established here is 0x60400020; E-P7's is 0x60020020.
4. Run sigfind map/check, then inspect candidates in the areas above with show and independent disassembly. Candidate scores are rankings, not proof.
5. Supply independently known pairs as truth only where exact role and boundaries have been checked. Do not construct a blanket shift mapping from this document's role table.
6. Check call graph, registers, stack convention, struct offsets, string anchors, task context and side effects. Verify hook bytes at each site before considering any change.
7. Promote only reviewed rows into an E-PL9 atlas with evidence and confidence tags. Keep candidates separate from verified symbols.
8. Re-run the existing model-specific probes against the exact image. A matched function alone says nothing about safe patching, full-system emulation or hardware recovery.

Upstream sigfind masks relocation-like operands, compares uniqueness on both images, and uses string anchors/call alignment. It retains MMIO and structure constants, which may differ across hardware. Results reported for E-M10 IV/E-M5 III/E-M1 III are not measured E-PL9 yield. Ghidra's AM33-2 decompiler is a reading aid; instruction semantics still require checks.

## Publication and attribution
This note contains original explanatory prose and factual addresses only. No firmware, decoded component, long disassembly, decompiler output, Ghidra project or signature cache is included.

Research informed by **Caduceus for the Olympus PEN E-P7 by cakelesscoder**, Apache-2.0, with credit also to upstream research contributors. If incorporating their code, names or documentation as a derivative, retain the applicable LICENSE/NOTICE and mark changes. The separate MN103 Ghidra module has its own GPL-3.0 licence; do not silently relicense or bundle it.

## Checks and boundaries
This was a documentation/source review. No fresh cross-body sigfind run, new native instruction execution, camera access or firmware write was performed. Existing model-specific findings are cited rather than rerun. This document does not supersede installation-readiness restrictions or authorize modification of the frozen candidate.
