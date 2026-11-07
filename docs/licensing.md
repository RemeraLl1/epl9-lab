# Licensing and third-party notices

Public visibility lets people read the repository. The licenses below also permit others to copy, modify, redistribute and continue the work, including forks for other cameras, subject to their terms. They provide no guarantee that an experiment works or is safe.

## Original project material

The root [MIT License](../LICENSE) applies to original project code, research notes and documentation except files with a different explicit license notice. Retain the copyright and license notice in copies or substantial portions. Contributions follow the applicable file license.

## MN103 reader and GNU binutils

These adapter files explicitly retain **GPL-3.0-or-later**:

- `scripts/mn103_reader/reader.c`
- `scripts/mn103_reader/disassemble.h`
- `scripts/mn103_reader/opintl.h`
- `scripts/mn103_reader/sysdep.h`

Their SPDX notices take precedence over the root MIT license. The [GPL version 3 text](../LICENSES/GPL-3.0-or-later.txt) is included; the notices permit version 3 or any later version. Python build/validation scripts and the provenance JSON remain under the root MIT license unless separately marked.

The local reader links these adapters with GNU binutils disassembler sources. The combined program is governed by GPL-3.0-or-later; redistributing it requires satisfying that license, including applicable corresponding-source and notice obligations. The MIT license does not replace those terms. GNU sources are acquired separately under ignored `references/`; preserve their original notices and `COPYING3`. Exact provenance is in [MN103 tooling](mn103-tooling.md) and `scripts/mn103_reader/upstream.json`.

## Material outside the license grant

Camera firmware, decoded payloads, manufacturer graphics and example photographs, OM Workspace libraries, tool installers, personal media and independent upstream projects are not relicensed by this repository. Their owners' terms continue to apply, even if a file is locally available for analysis. Firmware and extracted assets are not included in the public source tree. Use hashes, provenance and minimal reviewed findings instead of uploading these payloads.

Olympus, OM System, Kodak and film names identify research targets or references; they do not imply affiliation, endorsement or measured film equivalence. The project grants no trademark rights.

See [risks and limitations](risks-and-limitations.md) for the research status and [CONTRIBUTING.md](../CONTRIBUTING.md) for publication rules.
