# Illustrated change plan

**The illustrations are concepts, not screenshots or rendered examples.** Public v2 desktop trials and newer reported v3 review exist, alongside actual native-hook and partial emulator UI integration; no installed camera replacement is established. The first integration baseline is the two Watercolor slots. The owner also requested a wider 31-profile visual catalog and icons; that design backlog does not establish 31 working firmware slots or final menu mapping. See [current status, 2026-11-07](project-status.md) and [first-integration readiness](first-integration-readiness.md).

![Conceptual mapping from Watercolor I and II to separate Gold 200 and Portra 400 recipes, names, icons and example images](../assets/docs/recipe-change-map.svg)

Original schematic; dimensions and arrangement are illustrative. The camera's existing menu structure and unrelated controls are to be preserved. **For the first package, keep stock large example photographs and current Watercolor text labels.**

## Processing and UI scope

| Layer | Present / observed | Intended result | Still required |
| --- | --- | --- | --- |
| Image processing | Native jobs reach hardware configuration; desktop CMIO and v2 color/tone/WB drafts produce real TIFF pixels | Separate Gold 200-inspired and Portra 400-inspired rendering on the camera, with the Watercolor-specific spatial effect removed where appropriate | Actual ISP execution/coherence, real caller contracts, preview/capture coverage and calibration; desktop output is a separate path |
| Recipe name | Native GUI checks retain Watercolor I/II text | No unannounced label change in the current candidate | Renaming remains separate unless explicitly included in an approved release scope |
| Small icon / inline badge | Corrected row-bounded icons now render in three native E133 emulator screen contexts | Distinct G200 / P400 icons in existing allocations | Two bitmap pairs, ART-screen modeling and real-camera rendering remain outside coverage |
| Large menu example | Historical extraction and binding research is preserved | **Keep the existing examples unchanged for the first integration** | No picture-component modification in the reported first package; future replacement would need new scope and evidence |

A label change alone is not a film look. A new sample photograph does not change processing. A valid icon encoding does not establish a bootable firmware package.

## Earlier concept for possible future recipe cards

![Two schematic future recipe cards, Gold 200 and Portra 400, with existing-style navigation and explicitly unrendered example-image placeholders](../assets/docs/menu-concept.svg)

**Concept only, not a camera capture or the current first-package scope.** The empty image areas do not simulate recipe output. Current native-menu validation is documented separately in [the OM-Emu report](epl9-omemu-ui-validation.md); the first candidate retains stock example photographs and Watercolor I/II text. This earlier concept does not specify final layout, palette or menu order.

Existing original draft artwork is available for inspection:

| Gold slot | Portra slot |
| --- | --- |
| ![Draft G200 icon](../assets/film-menu/G200.svg) | ![Draft P400 icon](../assets/film-menu/P400.svg) |

The [icon report](epl9-watercolor-icons.md#standalone-replacement-artwork-2026-11-02) records all ten encoded candidates fitting their tested bitmap/symbol allocations and round-tripping through an independent decoder. The artwork remains a draft. Shared Roman numeral symbols and generic resources must not be overwritten globally.

For menu photos, the [source shortlist](epl9-art-example-pictures.md#digital-recipe-photo-shortlist-2026-11-02) links digital-recipe examples made on Fujifilm cameras. They are references, not E-PL9 results or permission to redistribute them. No third-party photograph is copied into these illustrations. The example-picture binding is still open: visually similar resources 360/361 and UI table values 399/400 must not be treated as interchangeable verified targets.

## Processing changes are deeper than color-table replacement

The intended flow is **retain the selected I/II recipe identity → choose a valid ordinary processing route → supply that recipe's color/tone parameters → preserve normal completion and ownership → render the correct preview and captured image**. It must preserve detail, unaffected modes and stable switching between recipes.

The current [native investigation](epl9-real-raw-boundary.md) reaches the peripheral boundary with actual source mosaic backing and attached table state. It makes no CPU source-pixel reads and produces no native output image. In contrast, the [Workspace bridge](epl9-workspace-cmio-bridge.md), [v0 controls](epl9-film-draft-trials.md) and [v2 tonal trials](epl9-tonal-neutral-trials.md) demonstrate actual desktop pixels from copied ORFs. They qualify color/tone/WB development on the desktop, not the modified native worklist, live view or a finished film recipe.

The native cache comparison reads a parameter object's field at +20 but does not directly compare its table pointer at +16. Consequently, merely exchanging Gold/Portra table pointers could retain stale settings. The eventual integration needs the actual invalidation and lifetime contract, not an invented flag update. Live view, captured JPEGs, warm recipe switching and power-cycle persistence must be checked independently.

## Parallel investigations and how results become part of this plan

Snapshot checked on 2026-11-07. The [readiness review](first-integration-readiness.md) records current package work and the owner's recipe freeze. The [source-qualified status report](project-status.md) distinguishes published results from more recent chat reports whose code/manifests are not in this checkout. This document creates no new camera feature commitment.

| Work area | Current basis | Integration condition |
| --- | --- | --- |
| ART processing and resource integration | Published emitted late hooks, stock producer/owner and load checks, plus scoped native GUI/icon validation | Bind the frozen v3 data, audit exact candidate/restore packages and review hardware/runtime/recovery limits |
| Deeper color and tone control | Published v1/v2 definitions, native curves and actual TIFF comparisons; additional independent-channel controls are still reported work | Preserve the zero-effect v1 gamma control, joint-only v2 tone qualification and need for neutral/highlight/illuminant calibration |
| Larger film-recipe catalog / later SD slots | Separate 29-recipe review and preference for mostly built-in recipes plus some SD-backed/open slots | Counts/mapping/loader remain undecided; exclude from the first two-slot test and do not retune Gold/Portra |
| Wi-Fi original-file throughput | Chat reports native rd data-preservation/copy savings and a separate ISC reuse model; no measured acceleration | Publish isolated source and resolve sector/stale-response semantics before camera timing claims |
| Full-field 1920×1440 at 60 fps | Native timing/marker work is reported; physical TG phase and video-buffer/MOV-PTS link remain open | Verify hardware readout and timing; model constants or unchanged FULL template selection cannot establish a mode |
| Gyro logging during video | Diagnostic access is a lead; sample/video synchronization is unverified | Establish raw rate, timestamp origin, buffer ownership, drops and recording impact |
| Log / 10-bit / HEVC | **Paused by the owner on 2026-11-04**; bounded curve-transport findings exist, but no practical quality/DR gain or genuine ten-bit recording | Preserve [the handoff](log-ten-bit-handoff.md); resume only on a new explicit owner request, with no feature promise |
| Installation and recovery | E-PL9 validator/service scenarios are reported with intercepted writes | Publish/reproduce the audit, trace early entry and restore every modified component; no universal recovery claim |

Detailed results should move into model/build-specific repository reports with input identity, pinned source, commands, tests, unresolved points and an entry in [CHANGELOG.md](../CHANGELOG.md). Local Windows paths or a chat statement alone are insufficient public evidence. The [contribution rules](../CONTRIBUTING.md) and [handoff guide](porting-guide.md) define the format.

For installation planning, start with [future installation and recovery](firmware-installation-plan.md). Its candidate SD path remains blocked on E-PL9-specific validation; these illustrations are not instructions to flash the camera now.
