# Contributing to E-PL9 Lab

Thank you for helping extend Olympus camera firmware research to the E-PL9. Start with the [project status](docs/PROJECT-STATUS.md), [credits](docs/CREDITS.md) and the instructions on the branch you intend to work on.

## Choose a task

- **Build/test tools:** reproduce the frozen files from exact stock, improve error messages, test the builder on Windows/macOS, or document a verified lawful stock acquisition route.
- **Firmware research:** trace the video colour path, recovery entry, buffers/ownership, SD lifecycle or button dispatch. Record what you know and what remains hypothetical.
- **Emulation:** improve instruction coverage, persistent-device models and reproducible traces without treating synthetic inputs as hardware observations.
- **Recipes:** preserve V6/Astra and individual recipe provenance; translate verified parameters into the E-PL9 path rather than inventing missing values.
- **Documentation:** follow Start here as a newcomer, report a broken link or ambiguous step, or explain a research result in plain language.

Before starting, search [open issues](https://github.com/RemeraLl1/epl9-lab/issues) and [PRs](https://github.com/RemeraLl1/epl9-lab/pulls). Open an issue naming the workstream, what you want to establish and the branch you will use. Do not interpret an old report as proof that a later prerequisite is complete.

## Get the right branch

`main` is the public entry point but does not yet contain all runtime work. Use the [branch/dependency map](docs/PROJECT-STATUS.md#published-workstreams). For example, the local builder is in `develop/volunteer-builder-20261112`; downloading main is not sufficient. Read `AGENTS.md` and relevant documentation in your selected branch.

For a code contribution, branch from the workstream's actual base. Do not merge all experimental branches into a firmware image. The first Gold/Portra candidate must remain bit-for-bit frozen while it awaits hardware evaluation.

## A useful report or PR includes

1. Exact source commit, model, original firmware size and SHA-256; use the builder's identifier checks where appropriate.
2. The command and prerequisites needed to reproduce the result, with personal paths removed.
3. What ran: static analysis, host-side model, actual native instructions with synthetic state, UI emulation, or physical camera observation.
4. Expected and observed behaviour, error text and relevant non-sensitive logs/hashes.
5. Tests run, skips/failures, and what was not tested. A focused pass is not a full-suite pass.
6. For cross-model work, evidence for each mapped address and call/argument/lifetime contract. No guessed E-P7/PEN-F offsets.
7. Source attribution, licences and modification notices for reused material.

Keep work small enough to review and open draft PRs while evidence is incomplete. Avoid hardware claims based only on menu screenshots or successful stub return codes. There is no established benchmark requiring hundreds of extra tests; run the functional checks needed to support the claim.

## Camera owners

Experienced owners with a spare E-PL9 can [express interest in an issue](https://github.com/RemeraLl1/epl9-lab/issues/new): give the displayed body version and your firmware-testing experience. Do not post serial numbers.

**There is no qualified first-camera flashing procedure in this project yet.** Participating is not an instruction to install the files. Agree the exact package, input identity, entry/completion observations and return plan before any hardware experiment. A stock-return file is not proof that a bricked camera can use it. Do not apply another model's update filenames, LED timing or button sequence.

Initial evaluation needs startup, ordinary shooting, both looks, saved JPEGs and the stock-return path documented separately. Video support requires saved-video evidence, not just preview. Avoid risking an only/working camera.

## Keep private and proprietary inputs out

Never commit or attach Olympus update BINs, decoded firmware, binary overlays, extracted manufacturer assets, camera serials, credentials, private media or packet captures with identifiers. Use ignored local directories for authorized research inputs. Publish your own source, tests, safe manifests/hashes and explanations. Inspect both staged files and history before pushing.

External tools keep their licences. Do not strip attribution or assume a linked project's licence covers this repository. Caduceus's own `NOTICE` and recipe credits must accompany applicable reused material; see [Credits](docs/CREDITS.md). This repository currently has no project-wide licence grant. A maintainer decision is needed before representing all of it as licensed open-source or granting downstream rights; no contributor should silently relicense existing work.
