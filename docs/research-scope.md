# Research scope

## Accepted goals

The owner wants to investigate an Olympus PEN E-PL9 on a Windows computer:

- Wi-Fi protocol coverage, direct browser browsing/downloads and better transfer behavior.
- Named film recipes applied by the camera, followed by investigation of replacing ART presets with custom looks and labels.
- Gyro measurements saved with video, initially as a separate Gyroflow-compatible file if feasible.
- Full-field 4:3 video at reduced resolution, with 1440x1080 and 1920x1440 as candidate outputs, not proven modes.
- Additional video modes such as 4K60 only if hardware and firmware evidence supports them.

## Evidence carried forward

The owner previously supplied an OI.Share capability XML advertising `get_camprop`, `set_camprop`, ART-related properties, and 4:3 live-view sizes up to 1280x960. This is historical evidence; save a fresh response from the camera before deriving an implementation from it. Preview dimensions alone do not prove full sensor field of view or video encoder support.

The referenced firmware projects target other models and contain useful methods. Their working functions and offsets must not be treated as E-PL9 compatibility evidence.

## First session

1. Record the camera and lens firmware versions and any prior modifications.
2. Record USB descriptors in Storage and MTP modes.
3. Read a small set of test files and record sizes/hashes as transfer references.
4. Observe official client recognition/version reading if OM Workspace is available.
5. In a separate Wi-Fi session, save capabilities, property descriptions and read responses. Compare transfer time and file identity against USB originals.
6. Obtain an exact E-PL9 stock update input for offline identification and decoding.
7. Inspect original MOV metadata and compare photo/video fields of view.

Live camera testing and firmware identification are pending. Setup work must not be reported as proof that a camera feature works.
