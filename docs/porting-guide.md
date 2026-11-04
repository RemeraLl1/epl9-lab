# Handoff and research on other cameras

The project is intended to remain useful if its original author stops working on it. Start from the evidence in this repository; private chat history is not a prerequisite. Read the [risks and limitations](risks-and-limitations.md) and [contribution rules](../CONTRIBUTING.md) first.

This is a guide to continuing research, not a firmware-installation procedure. No other model or build is supported by the E-PL9 probes merely because it shares a processor, table, mode name or manufacturer.

## Reading order and current handoff

This snapshot incorporates published completion, hardware/RAW and desktop Workspace findings available on 2026-11-04. Start with [current project status](project-status.md) and [the full directory index](README.md); newer chat-reported results are kept separate until their source/evidence is published. Detailed dated reports remain authoritative for their own experiment boundaries.

| Read | Purpose / current result |
| --- | --- |
| [Research scope](research-scope.md) | Accepted goals and the boundary excluding camera writes |
| [Input and initial findings](epl9-1.1-initial-findings.md) | Exact E-PL9 1.1/build 1101 identity; shared COLOR table; USB observations |
| [Recipe targets](watercolor-gold200.md) | Separate Gold 200 / Portra 400 goals, not calibrated recipes |
| [Routing](epl9-art-routing.md) | Mode propagation, worklists, ordinary versus late COLOR paths |
| [Service dependencies](epl9-service-dependencies.md) | Completion, callbacks, ownership and reference counts that must survive |
| [First offline prototype](epl9-offline-prototype.md), then [revised integration](epl9-integrated-prototype.md) | Historical schedule regressions, scoped correction, native call chains and explicit execution stops |
| [Completion contracts](epl9-completion-contracts.md) and [hardware/descriptor audit](epl9-hardware-completion.md) | Native notification/cleanup checks, corrected destination offsets and finite status replay |
| [Real RAW boundary](epl9-real-raw-boundary.md) | Actual input samples reach configuration; the missing pixel executor is a hardware boundary |
| [Workspace CMIO bridge](epl9-workspace-cmio-bridge.md) and [draft image trials](epl9-film-draft-trials.md) | Actual desktop TIFF controls and public v0 color-only recipes, separate from modified native jobs |
| [Tonal / neutral trials](epl9-tonal-neutral-trials.md) | Current v2 tone/WB definitions and actual exports, plus the preserved negative v1 gamma experiment |
| [Icons](epl9-watercolor-icons.md) and [example pictures](epl9-art-example-pictures.md) | Draft G200/P400 artwork round-trips; runtime rendering and example-picture bindings remain open |
| [Tooling](mn103-tooling.md) and [sources](sources.md) | Build prerequisites, pinned dependencies, licenses and upstream research |

The connected native probe now runs beyond the earlier missing-callee stops through object/table attachment, Bayer arithmetic and hardware configuration. Actual-mosaic cases stop at `0x6073eafa → 0x9880014c` with zero CPU source-pixel reads and poisoned output; independent native completion/status checks do not supply ISP pixels. Separately, real Workspace TIFF exports confirm color transport and v2's joint tone/WB route. The isolated v1 gamma remap had zero observed pixel effect. There is still no completed modified-camera pixel cycle or installable package. The next native work concerns real input/crop/CFA/packing, ISP execution/coherence and actual completion; desktop drafts need neutral/highlight/illuminant calibration and owner review. Keep both paths and their evidence separate.

The [illustrated change plan](planned-changes.md) explains processing and UI integration; the [future installation plan](firmware-installation-plan.md) separates stock USB updates from the unverified E-PL9 SD route. Track subsequent findings in [CHANGELOG.md](../CHANGELOG.md).

## What can be reused

- The method: identify exact inputs, verify container round trips, locate candidate data, trace consumers and mode routing, then test bounded behavior against controls.
- Public Python/C source under its applicable license, synthetic test strategies, report structure and upstream provenance. The generic `firmware_info.py` can identify a local file; it does not interpret arbitrary firmware.
- Search leads from shared tables and mode encodings, with their model/build provenance attached.

Addresses, image hashes, RAM mapping, structure offsets, mode identities, object contracts and patch ideas are specific findings to rediscover. The E-PL9 probes deliberately contain exact-image checks and Windows/local-path assumptions. There is no generic multi-camera patch framework or complete hardware emulator here.

## Establish another model or build independently

1. **Open a separate report.** Record model, hardware revision if known, displayed version and modifications. Separate an official downloaded update from the image actually installed on the device; do not assume they are identical.
2. **Identify the input.** Obtain it from an authorized source, record URL/date, byte size, SHA-256 and internal build. Keep payloads ignored. Identify container components and their hashes before comparing code. A round trip checks container consistency only.
3. **Establish architecture and mapping.** Validate decoder/tool suitability, instruction boundaries and a candidate address mapping from that image. Do not subtract the E-PL9 base or paste PEN-F/E-P7/E-PL9 addresses into another build.
4. **Rediscover semantics.** Treat matching tables/strings/keys as leads. Follow consumers, dispatch, request layouts, flag conditions, callbacks and buffer/object lifetimes. Record every inferred link separately from observed bytes and measured runtime behavior.
5. **Build a separate read-only probe.** Gate it on the new exact size/hash, reject unknown inputs before analysis/output, use new ignored output directories and retain the E-PL9 checks. Separate shared parsing logic only after equivalence is demonstrated.
6. **Validate locally.** Use synthetic instruction/ABI cases, bounds failures, wrong-image rejection, target/non-target comparisons and regressions. Label synthetic state and missing services. Success on a modeled worklist is not image processing, bootability or a safe camera modification.
7. **Publish the handoff.** Record prerequisites, reproducible commands, minimal reviewed results, limitations and the next offline question. A new investigation adds no camera support claim until the claimed behavior has been demonstrated under recorded conditions.

Flashing, factory reset, erasure and experimental vendor writes remain outside the current phase. A porting investigation does not change that boundary or establish recovery.

## Reproduce without the original workstation

A clone contains public source and notes. It does not include the firmware, decoded images, reference checkouts, compiler, private reports or samples. Start with Python 3.12+, the commands in each report and [Windows setup](windows-setup.md). Obtain dependencies separately, preserving provenance and licenses; do not expect `D:\EPL9Lab` or an existing `.venv` on your computer.

The [MN103 build](mn103-tooling.md) is validated for the pinned Windows/TinyCC setup and checks its source/compiler hashes; it does not download inputs. Linux/macOS native builds require their own validation. The [setup follow-up](windows-setup.md#clean-checkout-and-cloud-reproduction-2026-11-04) explains the OSD decoder's exact CRLF pin, optional RAW dependencies and which checks a clean cloud checkout can run. Workspace's inspected DLL invocation and manual TIFF exports require the qualified Windows installation and owner inputs. Existing report hashes/assertions are not a public archive of ignored runs: regenerate them from identified inputs before relying on them. If unavailable, report reproduction as blocked.

## New-model or build report template

```text
Question and target behavior:
Camera model / hardware revision / displayed firmware / prior modifications:
Input source URL and acquisition date:
Downloaded versus installed-image evidence:
Container name / internal build / byte size / SHA-256:
Decoded component sizes and SHA-256:
Repository revision / upstream commits / host OS / tool versions:
Prerequisites and exact commands:
External reports and hypotheses:
Static observations (with file offsets and mapping assumptions):
Bounded execution (synthetic state, supported semantics, stop boundaries):
On-camera observations (or explicitly unverified):
Target and unaffected-control comparisons:
Failures, regressions, contradictions and unavailable evidence:
Public results versus ignored local artifacts:
Unresolved questions and next concrete offline experiment:
```
