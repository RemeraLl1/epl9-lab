# Start here: build the E-PL9 research files

**Last checked: 12 November 2026.** This guide creates files on your computer. It does not install them or establish a safe camera update procedure.

## 1. Get the correct project folder

Open **[the builder branch](https://github.com/RemeraLl1/epl9-lab/tree/develop/volunteer-builder-20261112)**, then click the green **Code** button and **Download ZIP**. Extract the ZIP into a normal folder. You do not need a GitHub account or Git to download it.

You should see `epl9.py` and `requirements.txt` in that folder. If `epl9.py` is missing, you downloaded the old `main` branch; return to the link above. The reviewed builder commit is `51f6dd0`; see [PR #8](https://github.com/RemeraLl1/epl9-lab/pull/8) for later changes before using a newer revision.

## 2. Install Python and obtain your original firmware

Install [Python 3.10 or newer](https://www.python.org/downloads/). The full build was tested on Linux/Python 3.12.14; Windows commands are provided but have not been exercised in that environment.

You need your own lawfully obtained original **Olympus E-PL9 / IM008 build 1101** file:

- Filename: `OLY_E_133_1101_0000_0000.BIN`
- Size: `104552480` bytes
- SHA-256: `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`

The displayed body version 1.1 alone is not enough to identify the file. The builder verifies the complete file for you.

**There is not yet a verified direct stock-download link in this project.** Use an original you already obtained lawfully or consult [official OM support](https://support.jp.omsystem.com/en/). If you do not have the exact file, stop here; another model or a random patched download is not a substitute. The builder neither downloads firmware nor bypasses its hash check. Do not upload your BIN to an issue or PR.

## 3. Open a terminal in the extracted folder

On Windows, open the folder in File Explorer, click the address bar, type `powershell` and press Enter. Run:

```powershell
py -3 -m pip install -r requirements.txt
py -3 epl9.py check-stock --stock "C:\Camera\OLY_E_133_1101_0000_0000.BIN"
py -3 epl9.py build --stock "C:\Camera\OLY_E_133_1101_0000_0000.BIN"
```

Replace the quoted path with the actual location of your original. On macOS/Linux, open a terminal in the extracted folder and use:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python epl9.py check-stock --stock "/path/to/OLY_E_133_1101_0000_0000.BIN"
python epl9.py build --stock "/path/to/OLY_E_133_1101_0000_0000.BIN"
```

Pillow is the pinned dependency. Allow several hundred MB of RAM and at least 110 MB of free output space. For the complete technical description, see [the builder guide](https://github.com/RemeraLl1/epl9-lab/blob/develop/volunteer-builder-20261112/docs/epl9-volunteer-builder.md).

## 4. Find the output and know when to stop

The new folder `local/volunteer-native-source-v1/` contains:

- `Gold-Portra-v3-native-source-candidate.bin`: experimental ART candidate.
- `Stock-1101-main-osd-restore.bin`: stock main and OSD return package, not a complete camera backup or independent rescue image.
- `SHA256SUMS`, `READ-ME-FIRST.txt`, and `manifest.json`.

Both BIN files are 52,428,800 bytes. The [builder guide](https://github.com/RemeraLl1/epl9-lab/blob/develop/volunteer-builder-20261112/docs/epl9-volunteer-builder.md#build) lists their exact hashes. `manifest.json` is written only after both files have been read back and verified. If it is missing, the build is incomplete.

**This is the end of the currently qualified workflow.** Do not rename files to an assumed SD update filename or follow E-P7/PEN-F flashing steps. E-PL9 entry, completion indication, physical write and return have not been qualified for this package. A damaged early boot path may make ordinary rollback impossible. No flashing steps are supplied here as verified instructions.

## If something goes wrong

- **Python not found:** install Python and reopen the terminal; on Windows try `py -3 --version`.
- **`epl9.py` not found:** open the correct extracted builder folder, not `main` or its parent directory.
- **Stock rejected:** keep the hash check enabled. Confirm the model, filename, size and original source; do not edit the file to make the check pass.
- **Output already exists / partial output:** preserve it for diagnosis and choose a fresh directory using `--out local/volunteer-repeat`. The builder intentionally does not overwrite an earlier result.
- **Missing dependency:** install the branch's `requirements.txt` with the same Python interpreter you use to run the builder.
- **Other error:** [open an issue](https://github.com/RemeraLl1/epl9-lab/issues/new) with OS, Python version, branch/commit, exact command with private paths removed, and the error text. Do not attach firmware, serial numbers, credentials or personal media.

## Want to help instead?

Read [Contributing](../CONTRIBUTING.md). Software reproduction, documentation, source review and Windows testing can help before anyone risks a camera.
