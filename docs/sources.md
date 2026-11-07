# Sources

## Firmware research

- [Olympus / OM System firmware research](https://github.com/fishcu/oly_fw_analysis)
- [Reproducing that research](https://github.com/fishcu/oly_fw_analysis/blob/main/REPRODUCING.md)
- [PEN-F Wi-Fi notes](https://github.com/fishcu/oly_fw_analysis/blob/main/docs/protocols/pen-f/WIFI.md)
- [PEN-F USB update notes](https://github.com/fishcu/oly_fw_analysis/blob/main/docs/protocols/pen-f/USB_UPDATE.md)
- [Caduceus for E-P7](https://github.com/cakelesscoder/caduceus-ep7)

## Camera and gyro formats

- [Official E-PL9 manual](https://download.omsystem.com/pages/inst/epl9/manual_epl9_ENU.pdf)
- [Gyroflow GCSV format](https://docs.gyroflow.xyz/app/technical-details/gcsv-format)

## Diagnostic tools

- [Wireshark official downloads](https://www.wireshark.org/download.html)
- [USBPcap official releases](https://github.com/desowin/usbpcap/releases)
- [USB Device Tree Viewer](https://www.uwe-sieber.de/usbtreeview_e.html)
- [OM Workspace official download](https://download.omsystem.com/pages/owdownload/en/)

Upstream checkouts under `references/` are independent projects. Their local revisions and tool hashes are recorded in ignored setup records.

## Current source navigation, 2026-11-07

[First-integration readiness](first-integration-readiness.md) links the late native hooks, owner/load checks, corrected OM-Emu UI evidence and current reported v3 package work. [Project status](project-status.md) identifies the published main commit reviewed for this refresh and distinguishes newer chat-reported work from available source. The [directory index](README.md) links every public report. Firmware identity is recorded in [initial findings](epl9-1.1-initial-findings.md); native configuration versus pixel execution is established in [the real-RAW audit](epl9-real-raw-boundary.md).

Actual desktop image evidence is in [the CMIO bridge](epl9-workspace-cmio-bridge.md), [v0 controls](epl9-film-draft-trials.md) and [v1/v2 tonal trials](epl9-tonal-neutral-trials.md), with [current v2 definitions](../recipes/epl9-film-drafts-v2.json). Original media, TIFFs, DLLs and decoded tables remain private inputs, not public attachments. Digital recipe/photo references are visual direction, not measured Olympus coefficients or redistribution permission.

The [installation guide](firmware-installation-plan.md) retains manufacturer and pinned E-P7/PEN-F sources, while its newer E-PL9 validator findings are explicitly reported work pending public audit integration. The [setup follow-up](windows-setup.md#clean-checkout-and-cloud-reproduction-2026-11-04) records the OSD decoder's LF/CRLF identities without weakening its exact-byte check.
