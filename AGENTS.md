# E-PL9 Lab guidance

- Read `docs/research-scope.md` before camera work. Preserve accepted goals and distinguish hypotheses, source reports and measurements on this exact E-PL9.
- Prioritize film looks and replacing ART. Wi-Fi and the offline browser client are second; video extensions are later. Read `docs/epl9-1.1-initial-findings.md` before repeating firmware discovery.
- Identify every firmware input with model, displayed version, internal build when known, byte size and SHA-256. Patches for PEN-F or E-P7 are reference material, not E-PL9 patches.
- The current phase is workstation setup, read-only camera diagnostics and offline firmware analysis. Firmware flashing, factory reset, erasing files and experimental vendor write commands are outside this phase.
- Keep firmware, captures, original media, serial numbers, Wi-Fi credentials and machine-specific configuration in ignored local directories. Review staged files before every public push.
- Keep external projects as ignored checkouts under `references/`. Record upstream URLs and commit IDs. Do not republish their source under this project's name.
- Validate diagnostic scripts with synthetic/local inputs. Camera-dependent behavior must remain explicitly unverified until tested on the camera.
- Do not assume 4K60, open-gate recording, raw gyro access, complete USB tethering or full firmware recovery are available.
