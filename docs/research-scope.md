# Research scope

## Accepted goals

The owner wants to investigate an Olympus PEN E-PL9 on a Windows computer:

- Named film recipes applied by the camera, followed by investigation of replacing ART presets with custom looks and labels.
- Selected replacements: **Watercolor I → Kodak Gold 200-inspired look** and **Watercolor II → Kodak Portra 400-inspired look**, chosen by the owner on 2026-11-02. The later addition of type II supersedes the initial requirement to preserve it. Preserve other ART modes. First establish the native processing route, then tune the looks. A menu-name change alone does not satisfy this goal.
- UI requirement added on 2026-11-02: each accepted film recipe should have its own icon embedded in the firmware, replacing the corresponding old ART artwork. Start with Gold 200 and Portra 400. Keep the existing menu structure, navigation and unrelated camera behavior; the owner is satisfied with the rest of the system. The [icon audit](epl9-watercolor-icons.md) identifies distinct I/II resources and their format; complete screen/palette mapping and resource replacement remain to be established.
- The owner also includes the large example photographs in ART selection. Replace the examples for the two accepted slots while preserving other modes. On 2026-11-02 the owner chose **internet photographs made with digital film-simulation recipes**, rather than actual film scans, for the initial shortlist. These are visual references from other cameras, not outputs of our uncalibrated E-PL9 recipes. Later owner photographs remain an option. See [picture resources and shortlist](epl9-art-example-pictures.md).
- Wi-Fi protocol coverage, direct browser browsing/downloads, an interface cached for offline use, and better transfer behavior.
- Gyro measurements saved with video, initially as a separate Gyroflow-compatible file if feasible.
- Full-field 4:3 video, with the later video-chat target **1920×1440 at 60 fps**, plus synchronized gyro logging if feasible. Earlier 1440x1080/1920x1440 suggestions are candidate geometries, not proven modes; sensor readout, timing and encoder support remain unverified.
- Additional video modes such as 4K60 only if hardware and firmware evidence supports them.

## Evidence carried forward

The owner previously supplied an OI.Share capability XML advertising `get_camprop`, `set_camprop`, ART-related properties, and 4:3 live-view sizes up to 1280x960. This is historical evidence; save a fresh response from the camera before deriving an implementation from it. Preview dimensions alone do not prove full sensor field of view or video encoder support.

The referenced firmware projects target other models and contain useful methods. Their working functions and offsets must not be treated as E-PL9 compatibility evidence.

## Accepted file-transfer workflow

On 2026-11-02 the owner confirmed they can copy files from the SD card separately, without using the camera's USB Storage connection. Use this route to obtain original research samples when needed; troubleshooting USB Storage is not a prerequisite for the film-look investigation. This is an accepted workflow, not a measured successful transfer or a resolution of the earlier volume error. It does not establish a firmware installation or recovery method.

## Historical first-session checklist

1. Record the camera and lens firmware versions and any prior modifications.
2. Record USB descriptors in Storage and MTP modes.
3. Read a small set of test files and record sizes/hashes as transfer references.
4. Observe official client recognition/version reading if OM Workspace is available.
5. In a separate Wi-Fi session, save capabilities, property descriptions and read responses. Compare transfer time and file identity against USB originals.
6. Obtain an exact E-PL9 stock update input for offline identification and decoding.
7. Inspect original MOV metadata and compare photo/video fields of view.

The owner confirms displayed body version 1.1. Exact stock input identification, a shared COLOR table match and MTP enumeration are recorded in `epl9-1.1-initial-findings.md`. Owner RAW/JPEG data and actual full-size Workspace exports now exist; the desktop CMIO controls and color-only v0 drafts are documented in `epl9-workspace-cmio-bridge.md` and `epl9-film-draft-trials.md`. Modified-camera rendering and installation remain unverified. Later Wi-Fi transfer, timing and recovery findings are separated by source availability in `project-status.md`; setup, a chat summary or a synthetic test is not proof that a camera feature works.

## Broader design backlog and current evidence

The recipe-design chat now requests a broader **31-profile visual catalog** and recipe-specific icons. The initial two-slot implementation remains the measured baseline; a 31-entry firmware mapping, expanded slot capacity, final ordering and per-profile calibration are not established. Record the wider request without silently replacing every ART mode or importing copyrighted reference photos.

Use [project status](project-status.md) and the [documentation directory](README.md) to reconcile newer results. Preserve dated historical findings and negative controls; update current summaries when their old next step is superseded. Newer tone/WB, Wi-Fi, deep-color, video/gyro and installation/recovery work must retain its reported-versus-published status until its source and evidence are available.

## Public research and continuity

Maintain project documentation, research notes, code comments, commit messages, issues and pull requests in English, as requested by the owner.

The owner requests a publicly readable project with a prominent amateur, AI-assisted and at-your-own-risk explanation. Do not present the owner as a firmware expert or imply safety, support or a finished product. Preserve the [limitations](risks-and-limitations.md) and the README introduction as the research evolves.

Publish enough methods, input identities, source provenance, reproduction steps, negative results and open questions for someone else to continue without private chat history or the original author's involvement. The [handoff and porting guide](porting-guide.md) explains how to establish independent evidence for another model/build; shared offsets are not a compatibility promise. Original work is reusable under the [documented licenses](licensing.md), preserving the reader's GPL notices and third-party rights.

## Future installation documentation

The owner requests an English future installation/recovery explanation and illustrated plans for processing, labels, icons and menu examples. Maintain `firmware-installation-plan.md` and `planned-changes.md` as planning material with evidence status and sources. This documentation request does not expand the current phase to firmware writes or establish SD update/recovery compatibility. Integrate other chats' findings only after reviewing provenance, reproduction and their unresolved limitations; record meaningful updates in `../CHANGELOG.md`.
