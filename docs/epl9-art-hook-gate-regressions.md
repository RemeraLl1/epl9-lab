# E-PL9: input-free ART hook gate regressions

## Result, 2026-11-08

Seven new synthetic tests protect the exact request-kind and recipe-identity
gates in the published late color, gamma and early-WB hooks. Both Watercolor
slots accept `0x0040`, `0x0100`, `0x0200` and `0x1000`; adjacent values and
bitwise combinations are not accepted as additional request kinds. This
preserves the [native producer correction](epl9-native-owner-binding.md).

No production source or numerical recipe data changed. In particular, this
work does not import or reconstruct unavailable v3 definitions, replace v3
with public v2, or create a firmware container.

## Source and evidence boundary

- Reviewed published main: `1f4dc523fc8db1a61863da66a09413627d5eb8e8`.
- Documentation/source snapshot: PR #1 head
  `318d7b4ceacbfe724a7626b18eada87f162497ba`.
- Host: Linux, Python 3.12.14. Tests use only public Python and assembly source.
- New test: `scripts/test_epl9_art_hook_gates.py`.
- The tests interpret the assembler's authored instruction rows. They do not
  independently disassemble the resulting bytes with the qualified GNU reader.
- Color cases stop before native processing; gamma cases start after its
  original native call and stop before pointer stores; WB cases execute its
  authored arithmetic and stop at the stock continuation address.
- State, addresses, gain values and tone constants are synthetic test fixtures,
  not a photographic recipe or an observed camera request.

## Coverage

- Both exact Watercolor keys and all four supported request kinds.
- Rejection of neighboring/combined kinds, unrelated keys and mismatched
  request/context identities.
- Color/gamma secondary-format, variant and selector guards.
- Gamma caller, request pointer, wrapper return address, temporary header,
  extended-control pointer and magic checks. Rejected kinds cannot read an
  unavailable stack record.
- Whole-region comparisons confirm the tested color/gamma gates do not write.
- WB arithmetic matches the integer oracle for ordinary, zero and saturated
  inputs. Only the expected gain halfwords change; non-clobbered registers,
  stack pointer, other request bytes and other regions are preserved. The
  displaced instructions restore the expected D0/D2/A1 values.
- Three in-memory mutation checks separately removed exact `0x1000` acceptance
  from color, gamma and WB. Each was detected for both recipe slots. These
  mutations were not written to production source.

Run the focused tests from the repository root:

```text
python -m unittest discover -s scripts -p 'test_epl9_art_hook_gates.py' -v
```

All seven pass. The available suite excluding the externally dependent
`test_epl9_osd_audit` module passes **149 tests** (142 existing plus seven new).
Full discovery remains blocked at that module's setup because the pinned
`references/caduceus-ep7/tools/osd_extract.py` file is absent. Its five tests
were not run; this is not a full-suite pass and no hash guard was disabled.
See [the pinned dependency setup](windows-setup.md#clean-checkout-and-cloud-reproduction-2026-11-04).

## What remains blocked

The frozen v3 numerical inputs and matching full-size install/stock-return
containers are not supplied by this public snapshot. Neither are the exact
firmware components or qualified native reader. Exact-image probes, complete
container checks, OM-Emu GUI sessions and physical-camera tests were not run.
Current package and recovery gates remain in
[first-integration readiness](first-integration-readiness.md). The next worker
must obtain the actual frozen inputs and source artifacts, not infer them from
chat summaries or diagnostic constants. No flashing or other camera write was
attempted.
