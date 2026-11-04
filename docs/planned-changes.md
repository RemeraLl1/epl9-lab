# Illustrated change plan

**The illustrations are concepts, not screenshots or rendered examples.** Actual desktop Gold/Portra v0 TIFFs now exist in private research artifacts; no installed camera replacement is established. The first integration baseline is the two Watercolor slots. The owner also requested a wider 31-profile visual catalog and icons; that design backlog does not establish 31 working firmware slots or final menu mapping. See [current status, 2026-11-04](project-status.md).

![Conceptual mapping from Watercolor I and II to separate Gold 200 and Portra 400 recipes, names, icons and example images](../assets/docs/recipe-change-map.svg)

Original schematic; dimensions and arrangement are illustrative. The camera's existing menu structure and unrelated controls are to be preserved for this baseline.

## The four changes must agree

| Layer | Present / observed | Intended result | Still required |
| --- | --- | --- | --- |
| Image processing | Native jobs reach hardware configuration; desktop CMIO controls and v0 drafts produce real TIFF pixels | Separate Gold 200-inspired and Portra 400-inspired rendering on the camera, with the Watercolor-specific spatial effect removed where appropriate | Actual ISP execution/coherence, real caller contracts, preview/capture coverage and calibration; desktop output is a separate path |
| Recipe name | English Watercolor I/II labels are associated with distinct UI values | Names that identify the correct recipe in the applicable screens | Targeted string/resource encoding, language/screen coverage and an audited rebuild |
| Small icon / inline badge | Separate I/II bitmap and symbol resources were decoded | Distinct G200 / P400 icons in existing native sizes | Runtime palette/screen validation and integration; draft assets fit their checked allocations but are not installed |
| Large menu example | Picture resources and visual candidates have been extracted; runtime selection is unresolved | A correctly mapped, authorized example image for each slot | Resolve actual resource bindings, choose licensed/owner-approved content, encode within allocation and check on screen |

A label change alone is not a film look. A new sample photograph does not change processing. A valid icon encoding does not establish a bootable firmware package.

## What the selection screen could show

![Two schematic future recipe cards, Gold 200 and Portra 400, with existing-style navigation and explicitly unrendered example-image placeholders](../assets/docs/menu-concept.svg)

**Concept only, not a camera capture.** The empty image areas intentionally do not simulate the uncalibrated recipe's output. They represent future authorized example images; the drawing does not specify exact final layout, typography, palette or menu order.

Existing original draft artwork is available for inspection:

| Gold slot | Portra slot |
| --- | --- |
| ![Draft G200 icon](../assets/film-menu/G200.svg) | ![Draft P400 icon](../assets/film-menu/P400.svg) |

The [icon report](epl9-watercolor-icons.md#standalone-replacement-artwork-2026-11-02) records all ten encoded candidates fitting their tested bitmap/symbol allocations and round-tripping through an independent decoder. The artwork remains a draft. Shared Roman numeral symbols and generic resources must not be overwritten globally.

For menu photos, the [source shortlist](epl9-art-example-pictures.md#digital-recipe-photo-shortlist-2026-11-02) links digital-recipe examples made on Fujifilm cameras. They are references, not E-PL9 results or permission to redistribute them. No third-party photograph is copied into these illustrations. The example-picture binding is still open: visually similar resources 360/361 and UI table values 399/400 must not be treated as interchangeable verified targets.

## Processing changes are deeper than color-table replacement

The intended flow is **retain the selected I/II recipe identity → choose a valid ordinary processing route → supply that recipe's color/tone parameters → preserve normal completion and ownership → render the correct preview and captured image**. It must preserve detail, unaffected modes and stable switching between recipes.

The current [native investigation](epl9-real-raw-boundary.md) reaches the peripheral boundary with actual source mosaic backing and attached table state. It makes no CPU source-pixel reads and produces no native output image. In contrast, the [Workspace bridge](epl9-workspace-cmio-bridge.md) and [v0 trials](epl9-film-draft-trials.md) now demonstrate actual desktop pixels from copied ORF controls. They qualify a desktop development path, not the modified native worklist, live view or a finished film recipe.

The native cache comparison reads a parameter object's field at +20 but does not directly compare its table pointer at +16. Consequently, merely exchanging Gold/Portra table pointers could retain stale settings. The eventual integration needs the actual invalidation and lifetime contract, not an invented flag update. Live view, captured JPEGs, warm recipe switching and power-cycle persistence must be checked independently.

## Parallel investigations and how results become part of this plan

Snapshot checked on 2026-11-04. The [source-qualified status report](project-status.md) distinguishes published results from more recent chat reports whose code/manifests are not in this checkout. This document creates no new camera feature commitment.

| Work area | Current basis | Integration condition |
| --- | --- | --- |
| ART processing and resource integration | Published native configuration/RAW/completion audits; actual desktop v0 TIFFs; no complete native pixel cycle | Preserve the desktop/native distinction, complete ISP/data flow and validate target/control modes |
| Deeper color and tone control | Chat-reported native controls and newer v1/v2 desktop tone trials, including a negative RGB-remap result | Publish exact edits, controls, curves and pixel comparisons; v0 remains the public recipe target until then |
| Larger film-recipe catalog | Requested 31-profile visual catalog and per-film icons | Reconcile actual slot capacity, final mapping/order, image rights and per-profile evidence |
| Wi-Fi original-file throughput | Chat reports native rd data-preservation/copy savings and a separate ISC reuse model; no measured acceleration | Publish isolated source and resolve sector/stale-response semantics before camera timing claims |
| Full-field 1920×1440 at 60 fps | Native timing/marker work is reported; physical TG phase and video-buffer/MOV-PTS link remain open | Verify hardware readout and timing; model constants or unchanged FULL template selection cannot establish a mode |
| Gyro logging during video | Diagnostic access is a lead; sample/video synchronization is unverified | Establish raw rate, timestamp origin, buffer ownership, drops and recording impact |
| Installation and recovery | E-PL9 validator/service scenarios are reported with intercepted writes | Publish/reproduce the audit, trace early entry and restore every modified component; no universal recovery claim |

Detailed results should move into model/build-specific repository reports with input identity, pinned source, commands, tests, unresolved points and an entry in [CHANGELOG.md](../CHANGELOG.md). Local Windows paths or a chat statement alone are insufficient public evidence. The [contribution rules](../CONTRIBUTING.md) and [handoff guide](porting-guide.md) define the format.

For installation planning, start with [future installation and recovery](firmware-installation-plan.md). Its candidate SD path remains blocked on E-PL9-specific validation; these illustrations are not instructions to flash the camera now.
