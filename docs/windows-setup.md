# Windows setup

## Prepared workspace

- Python 3.12 virtual environment: `.venv`.
- Dependencies are pinned in `requirements.txt`.
- USB Device Tree Viewer is unpacked under `tools/UsbTreeView`.
- Wireshark 4.6.9 files are extracted from the official signed MSI under `tools/Wireshark`.
- Independent firmware-research checkouts are under `references/`; their exact local revisions are saved in `local/upstream-revisions.json`.

Run `scripts/doctor.ps1` to inspect this machine's current readiness. Downloaded installers and installation records remain local.

The initial download set includes Wireshark 4.6.9, USB Device Tree Viewer 4.8.0, USBPcap 1.5.4.0, Npcap 1.90 and OM Workspace installer 2.5.0.11. The Wireshark MSI matches the publisher's SHA-256. Windows validates the signatures of the Wireshark, USBPcap, Npcap and OM Workspace installers.

The prepared Wireshark and TShark executables both pass a version invocation. Their extraction does not register a system-wide installation. Windows Installer service access and the legacy USBPcap installer launch are blocked inside the agent's isolated terminal; system installers must be completed from the user's normal Windows session.

## Capture drivers

Wireshark can inspect saved capture files without capture drivers. Live network capture requires Npcap; USB capture requires USBPcap. Their signed official installers are in `downloads/`. Installing these kernel drivers requires Windows administrator consent and may require a restart. Do not restart the computer automatically.

## Upstream Windows limitation

The `oly_fw_analysis` checkout at `539fcf1fa9eda5fdef8ede4deeab94a4691d94c3` imports its analysis tools and passes the container-specific checks on this Windows environment. The complete input-free suite stops at the Wi-Fi client's use of the POSIX-only `fcntl` module. The upstream checkout has not been modified to hide this failure. Its Wi-Fi client is not yet a native Windows-ready component.

The project's own offline identity inspector has been checked against a multi-chunk synthetic input, including confirmation that the source bytes are unchanged. Camera-specific testing remains pending.
