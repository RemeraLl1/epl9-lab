# Documentation directory

Start with [project status, 2026-11-04](project-status.md). It reconciles the latest published source with newer reported work and explains why real Workspace draft images do not imply a complete modified-camera pixel cycle. Older dates and test totals belong to their original runs, not to every later checkout.

The [evidence-map illustration](../assets/docs/research-progress.svg) separates those execution paths; it is a technical diagram, not a camera screenshot.

## Scope, risk and continuation

| Document | Purpose |
| --- | --- |
| [Research scope](research-scope.md) | Accepted goals, two-slot baseline, wider design requests and current write restrictions |
| [Risks and limitations](risks-and-limitations.md) | Amateur/AI-assisted status, concrete risks and evidence categories |
| [Future installation and recovery](firmware-installation-plan.md) | Official stock USB route, candidate SD route and recovery preconditions |
| [Illustrated changes](planned-changes.md) | Processing/name/icon/example integration and conceptual UI |
| [Porting and handoff](porting-guide.md) | Reading order, reproduction requirements and new-model/build template |
| [Licensing](licensing.md) | MIT/GPL scopes and third-party exclusions |
| [Sources](sources.md) | Upstream and manufacturer references |

## Film recipes and desktop image evidence

| Document | Scope |
| --- | --- |
| [Recipe targets](watercolor-gold200.md) | Accepted Watercolor I/II replacement goals and historical routing observations |
| [Workspace CMIO bridge](epl9-workspace-cmio-bridge.md) | Actual desktop controls qualify coefficient transport into Workspace |
| [Gold / Portra draft trials](epl9-film-draft-trials.md) | Versioned v0 coefficients, actual TIFF results and calibration limits |
| [Neutral balance and tonal v1/v2 trials](epl9-tonal-neutral-trials.md) | Current v2 desktop drafts, native curve checks and the negative v1 gamma control |
| [Icon resources](epl9-watercolor-icons.md) | Existing resources, draft G200/P400 encodings and screen/palette limits |
| [Menu example pictures](epl9-art-example-pictures.md) | Picture extraction, unresolved runtime bindings and photo provenance |

## Native processing and historical audits

| Document | Scope |
| --- | --- |
| [Initial E-PL9 1.1 findings](epl9-1.1-initial-findings.md) | Exact stock identity, shared COLOR data and first USB observations |
| [ART routing](epl9-art-routing.md) | Mode propagation, Watercolor worklist and ordinary/late color paths |
| [Service dependencies](epl9-service-dependencies.md) | Callbacks, pending/completion, buffers and reference counts |
| [First offline prototype](epl9-offline-prototype.md) | Historical experiment and preserved negative schedule regressions |
| [Integrated prototype](epl9-integrated-prototype.md) | Chronological native-job, attachment and cleanup follow-ups |
| [Completion contracts](epl9-completion-contracts.md) | Native format labels, arithmetic and notification/cleanup component checks |
| [Hardware completion](epl9-hardware-completion.md) | Corrected destination fields and bounded status replay, not ISP execution |
| [Real RAW boundary](epl9-real-raw-boundary.md) | Actual input mosaic, CPU configuration versus the missing pixel executor |

## Setup and transport design

| Document | Scope |
| --- | --- |
| [Windows setup](windows-setup.md) | Historical machine setup plus clean-checkout prerequisites |
| [MN103 tooling](mn103-tooling.md) | Pinned Windows reader, upstream licenses and validation boundaries |
| [Offline browser client](offline-browser-client.md) | Cached UI versus camera-network transport and current research status |

Newer Wi-Fi, video/gyro, deep-color and E-PL9 recovery reports mentioned by other chats are listed in [the pending-evidence section](project-status.md#newer-reported-work-awaiting-publication-or-independent-reproduction). They are not supplied by this checkout unless separately published. Do not add broken links or pretend their scripts were synchronized.

Project-wide records: [README](../README.md), [CHANGELOG](../CHANGELOG.md), [contribution rules](../CONTRIBUTING.md), and [agent guidance](../AGENTS.md). Raw firmware, original photographs, generated examples and private reports remain ignored.
