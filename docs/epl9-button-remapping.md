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

The public checkout contains source and notes; `firmware/`, `local/` and upstream checkouts are ignored. The disconnected laptop holds the identified image, emulator installation and retained session evidence. They were not available here. This session also had no usable execution environment, so **no E133 input trace, new test run, script validation or patch verification was performed**.

Still missing:

- Exact E133 Fn/REC/Delete dispatch and context traces, including short/hold/release behaviour.
- The E133 selector entry/commit path and any setting/action IDs needed for the proposed recipe shortcut.
- An isolated guarded candidate and completed stock comparison.
- Physical-button verification and candidate-specific installation/stock-return evidence.

This research is complete as a source-backed handoff. The button feature is complete only when the above evidence exists and the separately authorized camera experiment confirms the intended behaviour. There is no E-PL9 Delete-remapping firmware ready to install in this branch.
