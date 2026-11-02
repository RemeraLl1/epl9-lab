# E-PL9 1.1: first firmware findings

Research priority: in-camera film looks and ART replacement first; Wi-Fi and an offline browser client second. This report records offline findings and observed USB enumeration. It does not provide an installable modification.

## Exact stock input

The owner reports body version **1.1**. This is a displayed version, not a byte-level identification of the installed firmware.

OM's firmware catalog identifies E-PL9 as model `1330` and offers:

- File: `OLY_E_133_1101_0000_0000.BIN`.
- Main internal build: `1101`.
- Size: `104552480` bytes.
- SHA-256: `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`.

The assembled download matches the [research inventory](https://github.com/fishcu/oly_fw_analysis/blob/539fcf1fa9eda5fdef8ede4deeab94a4691d94c3/provenance/firmware-inventory.json). All five component checksums pass. Decoding and re-encoding reproduces the original file exactly.

| Component kind | Decoded payload bytes |
| --- | ---: |
| `0x100` | 26214336 |
| `0x101` | 26214336 |
| `0x106` | 38797248 |
| `0x10e` | 219104 |
| `0x102` | 13107136 |

These checks establish input identity and container consistency. They do not establish bootability of changed files or a recovery method.

## Shared COLOR table found in E-PL9

The main component contains exactly one byte-identical copy of the **3028-byte COLOR table** documented for PEN-F/E-P7:

- Decoded main SHA-256: `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
- Table offset in decoded main: `0x4ee340`.
- Table SHA-256: `a33d64bdb78ac41ba24ccbff820380f563211a095ac08a12a7c37a51b5c00531`.
- The local OM Workspace `OlyAcacia.dll` contains the same table at file offset `0xd73d0`; library SHA-256 is `59801b67c9575909bac29d51d4d859dd4eb5bbb7c3fe9c0848f83ad8330785ed`.

The [documented structure](https://github.com/fishcu/oly_fw_analysis/blob/539fcf1fa9eda5fdef8ede4deeab94a4691d94c3/docs/color/pen-f/HSL_TABLES.md) contains twelve 28-byte sector records and associated LUTs. The exact match makes this a concrete starting point for locating native color processing on E-PL9. It does not demonstrate that a COLOR editor, editable H/L controls or named film profiles are available on this camera.

## Code-location candidates

The main component has an absolute-jump pattern at decoded offset `0xb6`, targeting `0x604000f9`; the candidate initialization prologue is at file offset `0xd9`. Together these suggest an analysis base of `0x60400020`.

Under that candidate mapping, the table address is `0x608ee360`, with one little-endian literal occurrence at decoded offset `0x39ec2f`. A Pop Art key used by the reference projects (`0x01010064`) also occurs in the nearby region, at `0x39ee11`, as well as at other locations. Main-component diagnostic strings include Color Creator, picture-mode and ART-related names.

These are **candidates**, not validated instructions, semantic cross references or safe patch addresses. A disassembler and control-flow review are required before claiming which modes use the table. PEN-F and E-P7 addresses must not be copied into E-PL9 patches.

The next implementation milestone is to trace the table consumer and ART mode dispatch, then design one isolated look with consistent live view, captured JPEGs and saved settings. Replacing the ART menu labels is a separate UI/resource step.

## USB observations

- One initial connection failed device enumeration with code 43.
- Storage later exposed the camera and a roughly 64 GB SD volume. Windows reported `ERROR_UNRECOGNIZED_VOLUME`; the owner reports that the camera can display its photos. The cause is unresolved.
- MTP without the SD card enumerated as `07b4:012f`, with Microsoft's MTP driver started and a USB 2.0 High-Speed link. Bulk OUT `0x05`, bulk IN `0x86`, interrupt IN `0x83` were reported.
- This establishes successful enumeration in that session. It is not a throughput or sustained-transfer test. USB descriptor revision `0x0100` must not be interpreted as the body's firmware version.

The SD card, raw USB report with serial identifiers, firmware and decoded payloads stay local. No firmware has been flashed by this project.

## Reproduce the offline audit

With the exact stock input, local Workspace installation and reference checkout available:

```powershell
.\.venv\Scripts\python.exe .\scripts\epl9_color_audit.py --out .\local\new-color-audit
```

Raw and generated evidence is kept under ignored `local/` and `firmware/` directories.
