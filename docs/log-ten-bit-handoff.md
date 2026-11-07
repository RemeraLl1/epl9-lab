# Log, 10-bit and HEVC: paused research handoff

## Owner decision, 2026-11-04

**This development direction is on hold. Do not automatically resume Log, 10-bit or HEVC work.** Resume only after a new explicit request from the owner. A flatter image alone does not meet the owner's goal; a practical improvement in recording quality or dynamic range has not been demonstrated.

Ten-bit recording is **unproven**, not established as impossible. No working Log camera modification, genuine 10-bit recording, HEVC encoder or measured image-quality gain was delivered. Earlier optimistic descriptions of the findings must not be treated as a feature promise.

Film looks, the two ART replacements and their graphics, Wi-Fi, full-field 4:3 video and gyro logging are separate directions. This pause does not cancel them or establish any of their proposed features.

## Source and artifact availability

This English summary preserves the owner's uploaded handoff dated 2026-11-04. It describes bounded offline experiments and uncommitted files from another session. Those Log/video scripts, detailed reports, firmware and raw traces are **not present in this checkout** and were not rerun or independently reproduced for this update. The repeated `/workspace/epl9-lab` path in another session does not establish shared files.

Preserve the originating worktree and its ignored inputs/results. Do not reset or delete it because the branch is paused. The original handoff reports no camera access, experimental vendor writes, firmware installation or recovery test. Nothing here authorizes those operations.

## Exact firmware identity carried forward

Olympus PEN E-PL9, model ID 1330; displayed body version 1.1 is owner-reported. The inspected input is downloaded main build 1101, not a dump of the installed body.

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| `OLY_E_133_1101_0000_0000.BIN` | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Decoded main, candidate analysis base `0x60400020` | 26214336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |

The handoff reports all five component checksums passing and a byte-exact decode/re-encode round trip. Its original firmware remained unchanged. Check the actual local inputs before considering a future reproduction; absence in another environment does not erase the earlier result.

## Findings retained as reported offline evidence

| Area | Reported observation | Limit |
| --- | --- | --- |
| RGB/luma configuration | Selected native gamma/tone functions execute with declared synthetic state. RGB selector `0x6079d328`, gamma configuration `0x6079d7da`, luma selector `0x6079ed15`, tone configuration `0x6079f309`. | Configuration transport, not camera frames or an end-to-end recording job. |
| Mode path | Property `0x9361` maps through snapshot +141 and message +352 toward effect 2000 in bounded stages with explicit host bridges. Message +353 remains ordinary picture mode on E-PL9. | Full movie producer/normalizer/override behavior and live property writes are unverified. Do not copy the E-P7 254/255 convention into this field. |
| Curve transport | A 256-entry u16 LUT is expanded to u32 without narrowing its values to eight bits in the inspected copy routine. Device-address destinations were replaced by RAM. | LUT precision is not pixel-buffer or encoded-video precision. No ISP was run. |
| Cache | A custom RGB curve at object +0 uses comparison token +4. Rewriting values at the same pointer without updating the token leaves the old loaded bank in the tested case. | A bounded cache control, not a proven complete movie-only integration or measured image improvement. |
| Stock flat curve | Ordinary and special RGB curves first reach 4095 at node 237 and have 19 maximum nodes through 255. | A flatter table does not demonstrate extra retained highlight detail. A calculation from table-node indices is not measured camera dynamic range. |
| Candidate curves | Log-shaped mathematical families were generated and their complete bank values checked through eight passes. | No calibrated scene-input scale, exposure mapping or viewing transform; not OM-Log/S-Log or measured stops. |
| H.264 profiles | One driver branch selects profile IDs 66/77/100/128, with no High 10 ID 110 in that branch. A lower packer accepts 110 until a later stop. | Neither the absence in one selector nor passage of a number establishes the chip's full encoding capabilities. |
| Ten-bit evidence | Diagnostic still-capture strings and precise RAW/LUT values were found; a MOV auditor reads signaled SPS depth. An 8-to-10-bit transcode demonstrated misleading low-bit/value-count tests. | No genuine higher-precision source video. Signaled depth, nonzero low bits and more code values do not prove native ten-bit capture. |
| HEVC | Searches of five decoded components found no convincing HEVC/H.265 encoder; two `hev1` substrings belonged to Bluetooth names. The inspected factory selected H.264 progressive/interlace. | Scoped negative findings, not proof of hardware impossibility. Software HEVC performance was not measured. |

The reported original documents are `epl9-log-curve-transport.md`, `epl9-ten-bit-feasibility.md`, `epl9-hevc-feasibility.md` and `cloud-firmware-download.md`. Their associated tools include `epl9_log_scout.py`, `epl9_video_native_probe.py`, `epl9_movie_profile_probe.py`, `epl9_log_curve_probe.py` and `epl9_video_audit.py`. These names identify artifacts to recover from the originating session; they are not links or runnable commands for this checkout.

## Conditions for any later resumption

Keep the work dormant until the owner explicitly chooses to return. If that happens, recover the existing source, manifests and reports before repeating discovery. The useful next questions are:

1. Define the practical quality improvement to test. More executed instructions or a flatter look are not that outcome.
2. Trace the complete recording job, distinguishing preview/still/movie contexts and closing the declared host bridges.
3. Qualify input scale/linearity, stage order, clipping and precision loss before choosing a transfer function or claiming dynamic-range gain.
4. Preserve movie-only scope, cache invalidation, object/table lifetime, reference counts, exposure logic and unrelated modes.
5. Use original recording output and comparable scenes to measure retained highlight detail, shadow noise, gradients, color and stability. The handoff had no original E-PL9 MOV or modified-camera footage in its own cloud session.

Physical camera modification remains a separate, unpassed phase. See [research scope](research-scope.md), [current project status](project-status.md), [risks](risks-and-limitations.md) and [installation planning](firmware-installation-plan.md).
