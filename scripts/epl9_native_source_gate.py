"""Narrow opt-in source contract for the native primary ART path.

The primary operation 0x1003 producer emits source format 0x0107 and flags
3/7. Stock gamma selection uses flag bit 2, not the entire flag byte.
Only its base-variant flags 3 are qualified here. Existing 0x0100/0x0200,
flags-zero controls remain accepted. This is not a general source-format mask.

The opt-in gain hook runs in the fresh request builder immediately after the
source copy and optional selector callback, before its first submission. The
later FE00 selector branch excludes the accepted ART family. The physical
packing of 0x0107 is not established by these CPU configuration checks.
Arbitrary admission callbacks and same-job concurrent execution remain outside
the qualified owner contract.
"""

SOURCE_PAIRS = ((0x100, 0), (0x200, 0), (0x107, 3))


def qualified(source_format, flags):
    return (type(source_format) is int and type(flags) is int and
            (source_format, flags) in SOURCE_PAIRS)


def assembly(prefix, register, format_offset, flags_offset, accepted, rejected):
    """Inline the same allowlist at WB, COLOR and gamma; clobber only D1."""
    return '\n'.join([
        f' movhu ({format_offset},{register}),d1',
        ' cmp 256,d1', f' beq {prefix}_legacy_flags',
        ' cmp 512,d1', f' beq {prefix}_legacy_flags',
        ' cmp 263,d1', f' beq {prefix}_native_flags',
        f' jmp {rejected}',
        f'{prefix}_legacy_flags:',
        f' movbu ({flags_offset},{register}),d1',
        ' cmp 0,d1', f' beq {accepted}', f' jmp {rejected}',
        f'{prefix}_native_flags:',
        f' movbu ({flags_offset},{register}),d1',
        ' cmp 3,d1', f' beq {accepted}', f' jmp {rejected}',
    ]) + '\n'


def extend_late_source(source):
    """Preserve legacy templates/default bytes; replace two exact opt-in spans."""
    color = '''color_secondary_check:
 movhu (28,a1),d1
 cmp 256,d1
 beq color_variant_check
 cmp 512,d1
 beq color_variant_check
 jmp color_exit_check
color_variant_check:
 movbu (48,a1),d1
 cmp 0,d1
 beq color_selector_check
 jmp color_exit_check
'''
    gamma = '''gamma_secondary:
 movhu (28,a3),d1
 cmp 256,d1
 beq gamma_variant
 cmp 512,d1
 beq gamma_variant
 jmp gamma_done
gamma_variant:
 movbu (48,a3),d1
 cmp 0,d1
 beq gamma_selector
 jmp gamma_done
'''
    replacements = ((color, 'color_secondary_check:\n' + assembly(
        'color_source', 'a1', 28, 48, 'color_selector_check', 'color_exit_check')),
        (gamma, 'gamma_secondary:\n' + assembly(
        'gamma_source', 'a3', 28, 48, 'gamma_selector', 'gamma_done')))
    for before, after in replacements:
        if source.count(before) != 1:
            raise ValueError('native source gate requires the reviewed late template')
        source = source.replace(before, after)
    return source
