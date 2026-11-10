# Research scope

## Accepted goals

The owner wants to investigate an Olympus PEN E-PL9 on a Windows computer:

- Named film recipes applied by the camera, followed by investigation of replacing ART presets with custom looks and labels.
- Future recipe storage, chosen on 2026-11-07: embed most of the recipe library in firmware and reserve a few slots for replaceable recipes loaded from SD. The owner subsequently requested active offline study now, including behavior without files and convenient recipe addition. Select the built-in recipes and the number of SD slots after reviewing the planned library of 29; the split is not fixed. The [hybrid design](epl9-hybrid-recipe-slots.md) and [first technical results](epl9-sd-slot-study.md) distinguish the design, local prototype and remaining native integration.
- The owner then explicitly authorized a separate loader prototype, confirmed that a missing file retains the embedded recipe and required the current Watercolor v3 to stay unchanged. The [native loader follow-up](epl9-sd-loader-prototype.md) records the candidate event point, readiness gate, fallback and scoped offline validation; the prototype is not installed in the camera or in the frozen candidate.
- Selected replacements: **Watercolor I (Акварель I) → Kodak Gold 200-inspired look** and **Watercolor II (Акварель II) → Kodak Portra 400-inspired look**, chosen by the owner on 2026-11-02. The later addition of type II supersedes the initial requirement to preserve it. Preserve other ART modes. First establish the native processing route, then tune the looks. A menu-name change alone does not satisfy this goal.
- UI requirement added on 2026-11-02: each accepted film recipe should have its own icon embedded in the firmware, replacing the corresponding old ART artwork. Start with Gold 200 and Portra 400. Keep the existing menu structure, navigation and unrelated camera behavior; the owner is satisfied with the rest of the system. The [icon audit](epl9-watercolor-icons.md) identifies distinct I/II resources and their format; complete screen/palette mapping and resource replacement remain to be established.
- The owner also includes the large example photographs in ART selection. Replace the examples for the two accepted slots while preserving other modes. On 2026-11-02 the owner chose **internet photographs made with digital film-simulation recipes**, rather than actual film scans, for the initial shortlist. These are visual references from other cameras, not outputs of our uncalibrated E-PL9 recipes. Later owner photographs remain an option. See [picture resources and shortlist](epl9-art-example-pictures.md).
- Wi-Fi protocol coverage, direct browser browsing/downloads, an interface cached for offline use, and better transfer behavior.
- Gyro measurements saved during video recording, initially as a separate Gyroflow-compatible file if feasible. The owner reaffirmed firmware-side logging on 2026-11-02; [diagnostic-code findings and implementation gates](epl9-gyro-logging.md) do not yet establish a usable raw stream.
- Full-field 4:3 video at reduced resolution. On 2026-11-02 the owner clarified the primary target to **1920x1440 at 60 fps**, retaining the full usable sensor field. This supersedes 1440x1080 as the primary candidate; a lower frame rate is not an accepted substitute. [Offline video findings](epl9-opengate-video.md) do not establish a working mode.
- Additional video modes such as 4K60 only if hardware and firmware evidence supports them.

## Current film recipe priority

The owner's next offline request is covered by [in-image SD placement and memory checks](epl9-sd-placement-lifetime.md). Both modules fit separate early-loaded stock padding spans and pass placed native controls with embedded fallback. Normal session retention is checked; forced free/getter and native destructor-prefix controls keep full teardown explicitly unqualified. The new decoded main is separate from both frozen v3 generations and is not an installation package.

On 2026-11-10 the owner authorized connecting T1/T2 to image processing in a separate offline prototype, preserving v3 and embedded fallback. The [native consumer](epl9-sd-processing-prototype.md) now exercises persistent recipe descriptors, native configuration and connected jobs up to the existing TruePic hardware boundary. It does not qualify output pixels, physical SD or native menu assignment.

The next authorized SD step now has a separate [owned-state/two-slot prototype](epl9-sd-state-slots.md): a larger HLS manager allocation holds session state and logical T1/T2 load fixed files independently. Missing files retain embedded records. These test aliases do not assign ART menu entries or change the Watercolor candidate; real module placement, lifecycle and SD I/O remain unqualified.

The owner keeps the first functionality test of **Watercolor I → Gold 200 v3** and **Watercolor II → Portra 400 v3** as the camera integration priority. The later instruction on 2026-11-07 authorizes active offline SD recipe study now alongside that work. Preserve the accepted v3 character and the [current integration candidate](epl9-v3-integration-status.md). The storage study does not add a prerequisite to this test. Existing large ART example photographs remain stock, following the owner's November 4 scope reduction.

The 29-recipe work is a candidate library, not evidence that 29 independent selectable firmware slots already exist. Its desktop rendering results remain separate from native E-PL9 processing. The eventual library selection and binding to camera menu entries require their own investigation.

## Evidence carried forward

The owner previously supplied an OI.Share capability XML advertising `get_camprop`, `set_camprop`, ART-related properties, and 4:3 live-view sizes up to 1280x960. This is historical evidence; save a fresh response from the camera before deriving an implementation from it. Preview dimensions alone do not prove full sensor field of view or video encoder support.

The referenced firmware projects target other models and contain useful methods. Their working functions and offsets must not be treated as E-PL9 compatibility evidence.

## Accepted file-transfer workflow

On 2026-11-02 the owner confirmed they can copy files from the SD card separately, without using the camera's USB Storage connection. Use this route to obtain original research samples when needed; troubleshooting USB Storage is not a prerequisite for the film-look investigation. This is an accepted workflow, not a measured successful transfer or a resolution of the earlier volume error. It does not establish a firmware installation or recovery method.

## First session

1. Record the camera and lens firmware versions and any prior modifications.
2. Record USB descriptors in Storage and MTP modes.
3. Read a small set of test files and record sizes/hashes as transfer references.
4. Observe official client recognition/version reading if OM Workspace is available.
5. In a separate Wi-Fi session, save capabilities, property descriptions and read responses. Compare transfer time and file identity against USB originals.
6. Obtain an exact E-PL9 stock update input for offline identification and decoding.
7. Inspect original MOV metadata and compare photo/video fields of view.

The owner confirms displayed body version 1.1. Exact stock input identification, a shared COLOR table match and MTP enumeration are recorded in `epl9-1.1-initial-findings.md`. Runtime color changes and reliable original-file transfers remain unverified. Setup or offline matches must not be reported as proof that a camera feature works.
