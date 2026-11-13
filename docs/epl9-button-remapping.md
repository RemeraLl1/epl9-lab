# E-PL9 button remapping: evidence and next experiment

Research handoff, 2026-11-08. Scope: Olympus PEN E-PL9, including Fn, REC and the Delete button during shooting. No camera was contacted, no firmware bytes were changed and no update container was built in this research session.

## Result

The stock E-PL9 offers reassignment of **Fn and REC**. Its manual does not offer Delete as an assignable shooting button. A shooting-only role for Delete is a firmware research target, not an existing project feature or a confirmed working patch.

The useful next result is an **exact-E133 input and dispatch trace**, followed by an isolated emulator candidate. Replacing Delete with Fn globally is unsuitable: Delete must retain its existing role in playback, and an immediate post-shot review may have a different input context from idle live view.

Keep this work separate from the first Gold 200 / Portra 400 integration. Neither recipe deployment nor colour calibration depends on introducing another button hook.

## Evidence

| Item | What the source establishes | Limit |
| --- | --- | --- |
| [Official E-PL9 manual](https://learning.omsystem.com/E-PL9/zz_pdf/PL9_ENU.pdf), pp. 95–97 | Fn and REC can be reassigned through Button Function. Examples include AEL/AFL, preview, one-touch WB, AF target, MF, exposure compensation, digital tele-converter, magnification, peaking and touch lock. Choices depend on mode. | Documentation, not a measurement on the owner's body. It does not document a film-recipe selector or Delete reassignment. |
| Same manual, pp. 103 and 121 | Delete removes a displayed image after confirmation; REC has separate playback assignments through qR Function. | A button can already have different roles in shooting and playback. That does not prove the proposed new Delete role exists. |
| [E-PL9 project input identification](epl9-1.1-initial-findings.md) | Displayed body version 1.1 is owner-reported; the audited stock update is E133, internal build 1101. | Installed-byte identity and a recovery procedure are not established by the displayed version. |
| [E-PL9 OM-Emu validation](epl9-omemu-ui-validation.md) | Exact E133 native GUI execution is available through Player/PlaySession. The project runner presses keys and records GUI states and diagnostics. | Existing 41-frame icon routes do not test Delete remapping, and all five film-site counters stayed zero. |
| [Caduceus E-P7 button analysis](https://github.com/cakelesscoder/caduceus-ep7/blob/825f8e62a9650f7802dade669edce5eb882e112c/docs/BUTTONS.md) | Documents key → setting → function → action dispatch, menu value lists and subsequent button/arrow experiments on E-P7. Later sections report owner observations of widened Fn/REC lists and correct the down/right mapping. | E-P7 addresses, setting IDs and availability rules must be relocated and checked on E133. Its queued profile-switch ideas are not implementations for E-PL9. Delete is not added by that work. |
| [Caduceus button builder](https://github.com/cakelesscoder/caduceus-ep7/blob/825f8e62a9650f7802dade669edce5eb882e112c/patches/omc_buttons/build.py) | A concrete reference for guarded, bounded edits to existing allowed-value lists and records. | The source says its earlier patch was dropped during a bootloop bisect and was not tested on its own. It is not evidence that a data-only patch is safe. |
| [om-c-firmware v0.3.2 release](https://github.com/azqeurio/om-c-firmware/releases/tag/dbv0.3.2) | Author advertises E-P7 button remapping and D-pad customization. | E-PL9 is absent from the listed camera tests. The public repository tree inspected here contains only README; it supplies no source-level button patch to port. |

The official-manual facts above are intentionally compact; use the linked pages for exact operation details.

## Reusable project components

- [Existing UI runner](../scripts/epl9_omemu_ui.mjs): deterministic key down/up, virtual time, native GUI state recording and diagnostic-history capture.
- [OM-Emu pinned revision](https://github.com/flatpanda/om-emu/tree/147ca89c60b24774f3145c2813d79714e0f0b7b7): the revision already used by this project.
- [Upstream play input implementation](https://github.com/flatpanda/om-emu/blob/147ca89c60b24774f3145c2813d79714e0f0b7b7/emu/src/lab/play.mjs): exposes a `delete` control. The generic control's UI_IN code is `0x0084`; the implementation reads each ported model's key tables and disables controls missing from that model.
- [Upstream E133 model definition](https://github.com/flatpanda/om-emu/blob/147ca89c60b24774f3145c2813d79714e0f0b7b7/emu/src/fw/models.mjs): identifies the same main image and E133 analysis base.

**Do not copy generic input coordinates or GUI indices into an E133 patch.** The existence of an emulator control is a lead; its E133 wiring, native event translation and physical behaviour still need a trace. The upstream `test_fnkeys.mjs` is for the generic E143 path and is not an E-PL9 verification result.

Audited stock input to require before tracing:

- `OLY_E_133_1101_0000_0000.BIN`: 104552480 bytes; SHA-256 `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`.
- Decoded main: 26214336 bytes; SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
- Analysis base: `0x60400020`, as established by the project and upstream E133 model.
- Reject a different input rather than adapting offsets silently.

## Practical work order

1. **Record stock E133 inputs.** Start from fresh stock sessions. Export the actual UI_IN entries for Fn, REC and Delete; the event names and IDs for down, hold and up; and the physical-button correspondence. Trace each into the native dispatcher and GUI handler. Include the input table bytes and call sites in the private report.
2. **Separate the two implementation paths.** For Fn/REC, locate E133's key/setting map, allowed-value records, labels, function/action table and mode overrides. If an additional useful action is already implemented, first consider a bounded list expansion. For Delete, establish whether its event reaches the assignable-button dispatcher or a fixed state handler. A missing dispatcher row means widening the Fn menu alone cannot enable Delete.
3. **Choose the first Delete experiment conservatively.** Use a single short press on confirmed idle still-shooting screens to invoke one existing, traced native action, such as peaking. This tests context and event handling before adding recipe-specific state changes. All other contexts follow the original path. No long press, double press, new settings storage or SD configuration in the first experiment.
4. **Then bind the useful recipe action.** Proposed UX, still a design: Delete opens the existing Picture Mode selector at the current film slot; the existing dial/arrows and OK choose Gold/Portra. This avoids silent changes from an accidental press. Direct cycling between the two slots is another design to evaluate after the selector path. Neither action is currently located or implemented for E133; reusing a screen requires tracing its normal entry, exit and commit sequence.
5. **Test an isolated candidate against stock.** Record the exact changed ranges and original-byte guards. Verify registers/stack/callback behaviour at return, press/hold/release delivery, context gates and unchanged stock diagnostics. Keep button edits out of the film candidate until these checks pass.
6. **Only after exact-image checks, plan a separate physical-camera experiment.** Review installation and stock-return evidence for this model and candidate. Passing GUI or emulator tests is insufficient to claim a safe update or recovery from arbitrary startup damage.

## Required regression matrix

| Context or transition | Required result |
| --- | --- |
| Idle P/A/S/M still shooting | Exactly one intended action per short Delete press; release does not repeat it. |
| ART, AP, SCN, AUTO, movie modes | Explicitly tested gate; unchanged stock path wherever support is not established. |
| Playback single/index, no card, empty card | Stock Delete behaviour and confirmation flow. Never treat absence of media as proof of preservation. Use synthetic card fixtures in the emulator. |
| Immediate Rec View, capture/write busy, sequential capture, recording | No new selector or recipe mutation; stock behaviour retained. |
| Menu, SCP, magnify, AF target and text/dialog screens | No inappropriate interception; original navigation and exits. |
| Holding Delete while changing context | No queued action on entry into a permitted state; no leaked key-up/hold event. |
| Fn/REC existing roles and playback REC role | Unchanged outside the explicit allowlist expansion. |
| Restart/sleep/wake and card changes | No unintended persistence, stale selected slot or duplicate event. |
| Recipe changes between captures | Existing parameter-owner/cache-invalidation contracts preserved; a menu value change alone does not establish processing with the new recipe. |

For the last row, preserve the native ownership and cache contracts already documented in [the integrated prototype](epl9-integrated-prototype.md) and [the owner report](epl9-native-owner-binding.md). A direct pointer swap is not an adequate recipe-switch implementation.

## Blockers and completion criteria

The public checkout contains source and notes; `firmware/`, `local/` and upstream checkouts are ignored. Earlier project reports locate the identified image, emulator installation and retained session evidence in local workspaces. Their current presence cannot be checked here: this session has no usable execution environment. **No E133 input trace, new test run, script validation or patch verification was performed.**

Still missing:

- Exact E133 Fn/REC/Delete dispatch and context traces, including short/hold/release behaviour.
- The E133 selector entry/commit path and any setting/action IDs needed for the proposed recipe shortcut.
- An isolated guarded candidate and completed stock comparison.
- Physical-button verification and candidate-specific installation/stock-return evidence.

This research is complete as a source-backed handoff. The button feature is complete only when the above evidence exists and the separately authorized camera experiment confirms the intended behaviour. There is no E-PL9 Delete-remapping firmware ready to install in this branch.

## Follow-up: published E133 address leads, 2026-11-08

The owner clarified that this is a new button investigation and requested analysis of the firmware itself. The earlier manual review is only a baseline. **This follow-up did not obtain the firmware bytes or independently hash them.** It recovers concrete addresses from published, pinned cross-build analysis without claiming a byte-level E133 control-flow trace.

### Image access was checked, not assumed

- The current execution tool returns `No usable execution environment is available`. It cannot enumerate current directories or earlier workspaces. Consequently, a stock image may already exist there; this session cannot establish its presence or absence. The disconnected laptop must not be treated as the only possible location.
- The public E-PL9 tree contains no firmware payload. The exact title searches available in Library returned the earlier research report and no stock-image metadata.
- Upstream [BLOBS.sha256](https://github.com/flatpanda/om-emu/blob/147ca89c60b24774f3145c2813d79714e0f0b7b7/BLOBS.sha256) independently pins the expected whole-container SHA above under `fw/old/OLY_E_133_1101_0000_0000.BIN`. This is an independent published hash pin, not a hash computed here.
- Upstream [firmware inventory](https://github.com/fishcu/oly_fw_analysis/blob/9be1867ace6638d79e705048212dfddd3a1e794f/provenance/firmware-inventory.json) records the same 104552480-byte container and decoded-main hash, and supplies xdel archive URLs. The archive is indexed by search, but both its directory and direct BIN URL were inaccessible through the available browsing tool. No archive bytes were retrieved.
- The [disassembly-window inventory](https://github.com/fishcu/oly_fw_analysis/blob/9be1867ace6638d79e705048212dfddd3a1e794f/provenance/disassembly-windows.json) was inspected: 2581 entries cover 23 distinct input-image hashes; none names the exact E133 decoded-main hash. It therefore does not supply an E133 Delete disassembly window to use here.
- The pinned [stock provisioner](https://github.com/flatpanda/om-emu/blob/147ca89c60b24774f3145c2813d79714e0f0b7b7/emu/host/firmware.mjs) can locate existing blocks, an explicit BIN, `OM_FW_DIR` or `OM_BIN`, and otherwise request stock from the vendor API. It verifies the whole-image pin before decoding. This route needs a working execution environment; it was not run. Obtaining and unpacking stock does not contact a camera.

### Concrete cross-build findings

[Machine-readable address leads](epl9-button-address-leads.json) retain **19 explicit E133 entries** from pinned [ports.mjs](https://github.com/flatpanda/om-emu/blob/147ca89c60b24774f3145c2813d79714e0f0b7b7/emu/src/fw/ports.mjs). No address was filled by the map's unchanged-address fallback. Their roles come from the reference-model source in [play.mjs](https://github.com/flatpanda/om-emu/blob/147ca89c60b24774f3145c2813d79714e0f0b7b7/emu/src/lab/play.mjs) and [menu.mjs](https://github.com/flatpanda/om-emu/blob/147ca89c60b24774f3145c2813d79714e0f0b7b7/emu/src/lab/menu.mjs).

| Address lead | E133 code in OM-Emu disassembly notation, or runtime table address | Runtime code address |
| --- | --- | --- |
| UI_IN task | `0x500f3a6a` | `0x604f3a8a` |
| UI_IN post | `0x500f4b27` | `0x604f4b47` |
| UI_IN forwarding function | `0x500f45fa` | `0x604f461a` |
| UI_IN group descriptions | `0x6058584c` | table |
| Raw code → EV translation | `0x60e3e654` | table |
| Native assignable-button mapping entry | `0x50c4d628` | `0x6104d648` |
| Key → button-setting lookup | `0x50c4c6a6` | `0x6104c6c6` |
| Key → button-setting table | `0x6135d430` | table |
| Button-setting getter | `0x50c5470e` | `0x6105472e` |
| Function → action lookup | `0x50c4c73c` | `0x6104c75c` |
| Function → action table | `0x6135d580` | table |
| GUI send-event | `0x50d52e89` | `0x61152ea9` |
| GUI dispatch | `0x50c7b4f5` | `0x6107b515` |
| GUI event index → message map | `0x615493e0` | table |
| GUI state-name table | `0x615ef200` | table |

The code conversion is the upstream [hle.mjs](https://github.com/flatpanda/om-emu/blob/147ca89c60b24774f3145c2813d79714e0f0b7b7/emu/src/lab/hle.mjs) rule: `runtime = disasm - 0x50000000 + 0x60400020`. Runtime table addresses must not receive this conversion. Every stored lead's calculated file offset lies within the expected 26214336-byte main payload. These arithmetic checks do not validate instructions, table rows or a patch site.

The reference source explicitly describes an assignable-button chain through key-to-setting, getter and function-to-action lookup. Applying the published address map identifies where to examine that chain in E133. **The source map alone does not prove every E133 edge, the physical Fn identity, or that Delete takes this route.** Those claims require the original instructions and table records.

### Delete and context: what is and is not established

The named upstream Delete control uses raw code `0x0084`. Its historical reference-model analysis calls the press/release events `EV_PRESS_DEL_KEY` / `EV_RELEASE_DEL_KEY` and pairs them with GUI ON/LONG/OFF indices 39/40/41. The current player reads the selected model's input matrix and lets the camera application map keys itself; the older stand-in `S-KEYMAP` has been removed. Therefore neither the reference-model bit coordinates nor those GUI indices count as checked E133 mappings.

The published [E133 model survey](https://github.com/flatpanda/om-emu/blob/147ca89c60b24774f3145c2813d79714e0f0b7b7/docs/model-survey.md) reports native playback at GUI `0x0608` and INFO at `0x060b`, with a native card filesystem in its test. The existing project runner uses native E133 shooting/menu states too. Thus distinct playback and shooting contexts are demonstrated by upstream/project execution, but the **Delete handlers within them remain unresolved**.

The same published E133 facts locate the Rec View state word at runtime `0x623976bc`; upstream initializes it to standby 1 as an explicit emulator assumption. This word is an observation lead, not a sufficient physical-camera guard. A patch must distinguish idle still shooting from Rec View and busy capture rather than infer the context solely from the mode dial or one GUI state number.

The current result narrows the pending byte-level work to these exact tables and functions. It does not establish that Delete is unused in all shooting-related states, identify an insertion point for a context hook, or preserve playback by construction. **No new button patch, script execution, disassembly or E133 key test is claimed.**
