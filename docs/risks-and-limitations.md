# Risks and limitations

## Project status

E-PL9 Lab is public amateur research by an owner learning camera firmware with AI assistance, without specialist firmware-development expertise. It is not an official Olympus/OM System project, a supported product or professional engineering advice. AI-generated code and explanations can contain plausible but serious mistakes. Every claim needs evidence and independent review.

All use, reproduction and modification is at your own risk. Material is provided as-is, without a promise of correctness, fitness, compatibility, maintenance or successful recovery. The applicable license contains the warranty and liability terms; this notice does not override mandatory law or third-party rights.

## Concrete risks

- Experimental firmware, incorrect addresses or vendor write commands can leave a camera unable to boot, permanently damage it or require paid repair. No complete recovery procedure has been validated here. An official updater or a stock update file is not proof of recoverability.
- Experiments can corrupt settings, SD cards, photos and video, or change unrelated modes. Preserve independent copies of irreplaceable media before any future hardware experiment; a backup does not make firmware changes safe.
- Wi-Fi captures, USB reports and original media can expose passwords, identifiers, location or personal content. Keep raw material local and publish only reviewed, minimal evidence.
- Modification may affect warranty or service eligibility. Access to firmware and permission to redistribute it depend on its terms and applicable law; a public repository does not grant those rights.

## Limits of the evidence

| Evidence | What it establishes | What it does not establish |
| --- | --- | --- |
| Matching SHA-256 and byte size | Identity of the inspected file | Identity of firmware installed on a camera, authenticity by signature, safety |
| Decode/re-encode round trip | Consistency of that container transformation | Bootability or acceptance of a modified update |
| Shared table or key in another model | A useful search lead | Equivalent control flow, structures or patch compatibility |
| Static disassembly | Selected instructions and candidate routes for one image | Runtime reachability, live-view/capture mapping or safe edit sites |
| Passing synthetic tests / bounded execution | Behavior covered by supplied inputs and implemented semantics | Complete CPU/RTOS/ISP emulation, real pixels or hardware safety |
| A successful hardware observation | That operation under the recorded conditions | Other modes, versions, long-term reliability or recovery |

Unsupported instructions, missing callees, synthetic objects, host redirections and unmodeled services must remain visible in reports. They cannot be replaced with assumed success. The current native job has not completed an image-processing cycle or produced recipe pixels. Separate actual full-size Workspace TIFF exports demonstrate desktop CMIO controls and v2 Gold/Portra color/tone/WB drafts; those are not modified-firmware pixels or on-camera behavior. See [current evidence and pending reports](project-status.md).

## Current boundary

The current phase permits workstation setup, offline analysis and read-only camera diagnostics. Flashing, factory reset, file erasure and experimental vendor write commands are outside this phase. There is no installable E-PL9 modification, calibrated Gold/Portra recipe or supported camera compatibility list.

Offsets and structure layouts apply only to the exact input identified in the associated report. A displayed version alone is insufficient. Do not remove a hash check to make a probe accept another file; establish and document a separate model/build investigation.

4K60, full-field video, gyro access, complete USB tethering and full recovery remain unproven goals. Public access and open-source licensing enable inspection and continuation; they are not safety certification. See the [handoff](porting-guide.md) before extending the work.

The [future installation and recovery plan](firmware-installation-plan.md) explains preparation and candidate routes. Newer native-code updater scenarios are reported, but their public audit is not yet present here; they do not establish physical E-PL9 entry, signals or recovery from damaged main. The [illustrations](planned-changes.md) remain concepts, not on-camera screenshots or rendered sample images.
