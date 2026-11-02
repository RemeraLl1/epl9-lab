# Research scope

## Accepted goals

The owner wants to investigate an Olympus PEN E-PL9 on a Windows computer:

- Named film recipes applied by the camera, followed by investigation of replacing ART presets with custom looks and labels.
- Selected replacements: **Watercolor I (Акварель I) → Kodak Gold 200-inspired look** and **Watercolor II (Акварель II) → Kodak Portra 400-inspired look**, chosen by the owner on 2026-11-02. The later addition of type II supersedes the initial requirement to preserve it. Preserve other ART modes. First establish the native processing route, then tune the looks. A menu-name change alone does not satisfy this goal.
- UI requirement added on 2026-11-02: each accepted film recipe should have its own icon embedded in the firmware, replacing the corresponding old ART artwork. Start with Gold 200 and Portra 400. Keep the existing menu structure, navigation and unrelated camera behavior; the owner is satisfied with the rest of the system. Resource format and variant-specific icon mapping remain to be investigated.
- Wi-Fi protocol coverage, direct browser browsing/downloads, an interface cached for offline use, and better transfer behavior.
- Gyro measurements saved with video, initially as a separate Gyroflow-compatible file if feasible.
- Full-field 4:3 video at reduced resolution, with 1440x1080 and 1920x1440 as candidate outputs, not proven modes.
- Additional video modes such as 4K60 only if hardware and firmware evidence supports them.

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
