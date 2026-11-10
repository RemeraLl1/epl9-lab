# Cloud migration checkpoint, 2026-11-10

This source checkpoint preserves unfinished offline firmware and recipe work
from the owner's Windows E-PL9 Lab workspace. It does not establish that
firmware is safe to install, that recovery works, or that OpenGate/SD prototypes
work on a camera. No camera operation or installation was performed for this
migration. The original checkout and its active work were not reset, cleaned,
switched or overwritten.

## Scope

The checkpoint includes the main research `scripts/`, `firmware_src/`,
`recipes/`, `assets/` and `docs/`. It deliberately excludes separate host colour
rendering and Android application projects, personal photographs and all video.
The owner requested only the minimum needed to continue firmware and recipe
research in the cloud.

RAW, JPEG, TIFF, crops, contact sheets, rendered comparisons and generated
HTML/JavaScript embedding photos are not published. Packet captures, device
identifiers, credentials, machine settings, downloaded software and caches are
also excluded. Do not force-add ignored files to complete a cloud checkout.

Stock OMDS firmware, decoded components and candidate/stock-restoration package
binaries remain outside Git. The saved vendor licence prohibits public
redistribution/upload of the manufacturer's software. This repository contains
research and patch/build source, not a public firmware mirror.

## Required private inputs

The exact stock E-PL9 build 1101 input is `OLY_E_133_1101_0000_0000.BIN`,
104552480 bytes, SHA-256
`aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`.
Use only an authorized private backup or the manufacturer's official download.
An expired signed catalog URL is not a permanent download link.

The owner's separate minimal private backup preserves this one stock copy,
frozen RGB/recipe data, metadata/listing evidence and compact deltas for both
v3 generations. Its offline restore helper verifies every stock/candidate and
decoded-component hash, reconstructs stock/candidate packages and refuses to
overwrite different existing files. Restored `firmware/` and `local/` must stay
ignored. Historical absolute Windows paths inside evidence JSON remain
historical and require deliberate adaptation for Linux operations.

## Restoring cloud execution

1. Clone the published checkpoint and use Python 3.12 or newer.
2. Install `requirements.txt`. Optional RAW/desktop-rendering dependencies are
   unnecessary for continuing firmware-only work without personal images.
3. Restore the authorized private backup into ignored paths, preserving file
   identities. Do not publish the backup or its restored firmware.
4. Restore independent upstream references at the recorded revisions below.
5. Build and validate the MN103 reader from pinned source for the target
   operating system, following [MN103 tooling](mn103-tooling.md). The separate
   [Linux portability follow-up](cloud-portability-20261110.md) provides
   host-specific defaults and source/validation provenance; a Linux binary
   must be built locally, not assumed present in the checkpoint.
6. Run complete tests and the relevant native/offline probes after restoring
   inputs. A source checkout by itself omits required test fixtures.

Recorded independent upstream revisions:

- https://github.com/fishcu/oly_fw_analysis.git,
  `539fcf1fa9eda5fdef8ede4deeab94a4691d94c3`.
- https://github.com/cakelesscoder/caduceus-ep7.git,
  `7d42c1f258737b7196c6b17cec5d643b5080ece6`.
- MN103 reader provenance is in `scripts/mn103_reader/upstream.json`.

## Verification and limits

The isolated Windows snapshot passed Python AST/JSON parsing and all 304 main
unit tests when provided with the ignored private firmware fixtures and pinned
upstream decoder. No personal photograph or video was needed. A source-only
checkout without those fixtures had 2 missing-input errors and 11 skips; that
was not a full pass.

The original local chats remained active, so this commit is a checkpoint, not a
claim that every later unfinished edit is already synchronized. Windows OM
Workspace and physical USB/SD/camera access do not become available just by
moving source to Linux. Native integration, camera tests and recovery remain
subject to the detailed research limitations in the project reports.
