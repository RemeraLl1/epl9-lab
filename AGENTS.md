# E-PL9 Lab guidance

## Current documentation and attribution (2026-11-12)

- Start with `docs/PROJECT-STATUS.md` and `docs/START-HERE.md` for current workstream/branch state. Older reports below retain their historical scope; public-source building and virtual updater/UI work have since advanced, without physical flashing or hardware recovery qualification.
- Keep the native-source-v1 Gold/Portra candidate frozen; SD/Delete/31-recipe, OpenGate and gyro work remain separate. Do not present UI, parameter or host-model tests as a physical camera result.
- Prominently credit Caduceus E-P7 by cakelesscoder and contributors, fishcu/oly_fw_analysis and flatpanda/om-emu where relevant. Read `docs/CREDITS.md`; retain applicable licences/NOTICE and recipe attribution when adapting material. Do not claim every E-PL9 change is a direct E-P7 port or transfer E-P7 hardware validation to E-PL9.
- Main is currently the public navigation/historical branch, not a combined runtime release. Check the branch map before using Download ZIP or integrating work. A code publication or merge does not qualify installation.

- Read `docs/research-scope.md` before camera work. Preserve accepted goals and distinguish hypotheses, source reports and measurements on this exact E-PL9.
- Prioritize film looks and replacing ART. Wi-Fi and the offline browser client are second; video extensions are later. Read `docs/epl9-1.1-initial-findings.md` before repeating firmware discovery.
- Accepted ART replacements: Watercolor I → Kodak Gold 200-inspired look; Watercolor II → Kodak Portra 400-inspired look. The owner explicitly added type II on 2026-11-02, superseding its earlier preservation requirement. Preserve other modes; read `docs/watercolor-gold200.md` and `docs/epl9-art-routing.md` for this investigation.
- Replace the accepted recipes' old ART icons with recipe-specific icons embedded in firmware. Preserve existing menu structure, navigation and unrelated behavior. Read `docs/epl9-watercolor-icons.md`: distinct I/II bitmap and inline-symbol resources have been extracted; shared Roman numeral symbols must stay unchanged. Complete screen/palette mapping is still open.
- Also replace the large example pictures in ART selection. Artwork choice remains open: film cards/icons, later owner photographs rendered with the recipes, or suitable existing photographs. Read `docs/epl9-art-example-pictures.md`; visual candidates are not yet verified runtime bindings.
- Identify every firmware input with model, displayed version, internal build when known, byte size and SHA-256. Patches for PEN-F or E-P7 are reference material, not E-PL9 patches.
- The current phase is offline firmware development, reproducible file building, emulation and read-only camera diagnostics. Firmware flashing, factory reset, erasing files and experimental vendor write commands remain outside this phase.
- Keep firmware, captures, original media, serial numbers, Wi-Fi credentials and machine-specific configuration in ignored local directories. Review staged files before every public push.
- Keep external projects as ignored checkouts under `references/`. Record upstream URLs and commit IDs. Do not republish their source under this project's name.
- Validate diagnostic scripts with synthetic/local inputs. Camera-dependent behavior must remain explicitly unverified until tested on the camera.
- Before continuing the offline ART prototype, read `docs/epl9-offline-prototype.md` and `docs/epl9-integrated-prototype.md`. The original subset stops at CALL/RET; the opt-in call engine now executes selected native chains. Preserve the historical four schedule regressions and their scoped fix. Full processing remains blocked at unmodeled software dependencies; passing worklist/COLOR checks are not a pixel cycle or a validated patch.
- The connected `epl9_job_probe.py` completes native job/cache construction and frame start with explicit host resources. Constructor cursor 16 produces a no-op if frame start is omitted. Preserve the native cursor semantics, descriptor contracts, and parameter-object comparison field +20; changing table pointer +16 alone does not dirty the tested cache bit. Read the connected-job follow-up before extending its models; full pixel output and request completion remain unverified.
- Read `docs/epl9-service-dependencies.md` before revising routing. Retain compatible short schedules, pending-request completion, owner callbacks and parameter-object reference counts; event 31 is caller-dependent, not a proven disposable filter.
- Do not assume 4K60, open-gate recording, raw gyro access, complete USB tethering or full firmware recovery are available.

