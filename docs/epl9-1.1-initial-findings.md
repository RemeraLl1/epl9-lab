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

Follow-up: the [Watercolor I / Gold 200 investigation](watercolor-gold200.md) now records native instruction decoding, separate type-I/type-II key branches, and a mode-key-11 call to the shared table consumer. It supersedes the literal-only status for those specific windows; hardware reachability and an isolated ART replacement remain unverified.

The next implementation milestone is to trace the table consumer and ART mode dispatch, then design one isolated look with consistent live view, captured JPEGs and saved settings. Replacing the ART menu labels is a separate UI/resource step.

## USB observations

- One initial connection failed device enumeration with code 43.
- Storage later exposed the camera and a roughly 64 GB SD volume. Windows reported `ERROR_UNRECOGNIZED_VOLUME`; the owner reports that the camera can display its photos. The cause is unresolved.
- MTP without the SD card enumerated as `07b4:012f`, with Microsoft's MTP driver started and a USB 2.0 High-Speed link. Bulk OUT `0x05`, bulk IN `0x86`, interrupt IN `0x83` were reported.
- This establishes successful enumeration in that session. It is not a throughput or sustained-transfer test. USB descriptor revision `0x0100` must not be interpreted as the body's firmware version.

The SD card, raw USB report with serial identifiers, firmware and decoded payloads stay local. No firmware has been flashed by this project.

### Read-only MTP follow-up — 2026-11-04

The owner connected the E-PL9 in ordinary MTP mode without an SD card.
Windows identified one present WPD device, model E-PL9, USB `07b4:012f`,
with status OK and problem code 0. Microsoft's `WUDFWpdMtp` driver was in
use. USB descriptor collection confirmed USB 2.0 **High-Speed**, imaging
interface class/subclass/protocol `06/01/01`, and endpoints `05` Bulk OUT,
`86` Bulk IN, `83` Interrupt IN. High-Speed is the connection mode; no file
transfer speed was measured in this no-card session.

The ordinary Windows Portable Devices API opened with `GENERIC_READ` and
returned all six requested DEVICE properties: manufacturer OLYMPUS, model
E-PL9, protocol `MTP: 1.00`, battery 100%, battery power, and the firmware
version property string `1.00`. The Windows shell exposed the camera but
listed no child storage with the card absent. The helper's property-key and
value marshalling was checked first using local synthetic containers, without
opening a device in that check.

**The WPD string `1.00` does not contradict the owner-reported body menu
version 1.1.** In the exact downloaded **1101** main, the PTP information
serializer passes the literal `1.00` at `61312b0d` to its string writer at
`60fb4875`, after the manufacturer and model fields. The USB device-descriptor
revision `0100` is a third, separate field. We did not reread the body's
on-screen firmware version or identify installed bytes in this session.

The private reports and byte-checked version listing are in
`local/epl9-live-diagnostics-20261104/`. USB device identifiers and the full
host tree remain in ignored local files. No raw USB transaction capture or
PTP operation list was acquired. No diagnostic vendor commands, memory reads,
flash writes, reset or firmware update were requested. The cardless MTP
session does not demonstrate BOOT access, recovery or media transfer.

### WPD capabilities and stock MTP table — 2026-11-04

A second `GENERIC_READ` query on the connected cardless E-PL9 returned
**40 WPD command keys and 24 supported DEVICE property keys**. The probe
called `GetSupportedCommands` and `GetSupportedProperties("DEVICE")`.
This lists capabilities through the Windows driver, which can use cached
information. It does not execute the listed commands or read all 24 values.
The properties include device and object identifiers, name, device type,
transport, date/time, power source and battery level. The commands include
object enumeration, property retrieval and reading object resources.

Eight command keys match Microsoft's MTP extension interface, including
discovery and generic vendor-command transport. In particular, Microsoft's
`WPD_COMMAND_MTP_EXT_READ_DATA` reads a chunk of a vendor transfer that has
already been opened. The name does not identify Olympus's `0x9021 READ_DATA`
memory operation. Delete and format keys also appear in the driver list.
Only the two capability queries above were made by this probe.
[Microsoft MTP extension interface](https://learn.microsoft.com/en-us/windows/win32/wpd_sdk/supporting-mtp-extensions)

The decoded stock E-PL9 / IM008 / 1330 main (displayed version 1.1,
build 1101, 26214336 bytes, SHA-256
`8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`)
contains the PTP `GetDeviceInfo` serializer at `0x60fb45ad`. Its internal
mode 4 sets the MTP vendor extension ID 6 and uses the following little-endian
tables:

| DeviceInfo field | Address | Values in hex |
| --- | --- | --- |
| Operations | `613129c8` | `1001 1002 1003 1004 1005 1006 1007 1008 1009 100a 100b 100f 1014 1015 1016 101b 9801 9802 9803 9805` |
| Events | `61312976` | `4004 4005 4002 4009` |
| Device properties | `61312964` | `5001 5011 d405 d406 d407` |
| Capture formats | `6131293c` | `3008 b980 3800 3801 b101` |
| Image/object formats | `6131292c` | `3000 3001 3006 3008 b980 3800 3801 b101` |

The 20 advertised operations include storage and object listing, full and
partial object reads, thumbnails and object metadata. The diagnostic
`9021`, `902a` and `902b` operations traced in the
[board readout notes](epl9-board-readout.md) are absent from this MTP table.
This bounds what the stock image advertises in ordinary MTP. Acceptance of
unadvertised operations and behavior of other modes were not tested.
The table came from the stock image; no live USB `GetDeviceInfo` packet was
captured. Media transfer requires a test with storage present. BOOT and
full flash acquisition remain unverified.

The raw and named WPD reports are under
`local/epl9-live-diagnostics-20261104/mtp-no-sd-connected-01/`.

### USB identification retest — 2026-11-05

Present-device enumeration found one E-PL9 on USB `07b4:012f` in class
`WPD` with status OK. A fresh root-property query with `GENERIC_READ`
returned OLYMPUS E-PL9, `MTP: 1.00`, battery 100%, battery power and the
WPD version string `1.00`. The version distinction above still applies.
The query read only root metadata. No media object was opened.

The explicit parameterless PTP `0x1001 GetDeviceInfo` attempt through
WPD `SendCommand` returned `0x80070005` (access denied) before a data phase
was available. This is a Windows API result, with no captured PTP response.
USBPcap did not provide an accessible capture interface in the session.
The result confirms normal Windows identification, while the live PTP
operation array remains uncaptured. The private root metadata report is
`local/epl9-live-diagnostics-20261104/usb-identification-20261105-051728.json`.

## Reproduce the offline audit

With the exact stock input, local Workspace installation and reference checkout available:

```powershell
.\.venv\Scripts\python.exe .\scripts\epl9_color_audit.py --out .\local\new-color-audit
```

Raw and generated evidence is kept under ignored `local/` and `firmware/` directories.
