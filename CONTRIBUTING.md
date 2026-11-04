# Contributing and continuing the research

Anyone may read, fork, question or continue this project under its [licenses](docs/licensing.md). Contributions and corrections are welcome. Please write documentation, research notes, code comments, issues and pull requests in English. Specialist expertise is not required to ask a question; claims of functionality do require evidence. Maintenance, response times and acceptance of contributions are not guaranteed.

Read the [risks](docs/risks-and-limitations.md), [accepted scope](docs/research-scope.md) and [handoff / porting guide](docs/porting-guide.md). Current work is offline analysis and read-only diagnostics. The disclaimer does not expand that scope to camera writes.

Before changing a summary, read [current project status](docs/project-status.md) and [the documentation index](docs/README.md). A dated report can remain historically correct after its next step has been superseded. Update current navigation and add a scoped follow-up rather than deleting negative results. For work reported by another chat, identify whether its public source, exact inputs and results are actually available; never invent a missing report, command or test run.

## Make a result independently checkable

For an issue, pull request or research note, include:

- The concrete question and result, including failures and unresolved dependencies.
- Model, displayed firmware version, internal build if known, file sizes and SHA-256 hashes. State whether the installed image was actually obtained or is only owner-reported.
- Repository revision, upstream URLs and pinned commits, host OS, tool/compiler versions and required local inputs.
- Exact commands, expected output and actual checks. Explain any paths or inputs the next researcher must supply; ignored local files are not delivered by a clone.
- The evidence category for each claim: external source report, hypothesis, static file observation, bounded offline execution, or on-camera measurement. State synthetic state, modeled behavior, hooks and stopping boundaries explicitly.
- Effects on both target slots and unaffected controls, plus what was not tested. Tests of scripts are not tests of a camera feature.

Keep public summaries sufficient to explain the reasoning without needing a private chat. Link the relevant report and script, preserve contradictory observations and explain superseded conclusions instead of silently deleting them. A maintainer or another researcher should be able to resume from the repository alone.

## Work with files and licenses

Firmware, decoded binaries, extracted manufacturer artwork, captures, original media, credentials and machine configuration stay in ignored directories. Record hashes and provenance rather than embedding copyrighted payloads in reports. Review diffs and staged files before publishing; an ignored path does not sanitize an attachment or prevent an accidentally forced addition.

Keep upstream projects separate under ignored `references/`; record their URLs, commits, notices and acquisition steps. Do not rename their work as this project's source. Preserve SPDX notices and the MIT/GPL split in [licensing](docs/licensing.md). Identify any third-party material and its license in a proposed contribution. Submit original contributions under the applicable file license; this is not a request to relicense someone else's work.

## Validation and handoff

Documentation changes need accurate claims, working links and review of the final diff. Code changes need relevant local or synthetic checks, including wrong-image rejection where applicable. Do not claim a firmware-dependent audit passed if its input, reader or host platform is unavailable.

Keep three image-evidence paths distinct: desktop Workspace/LibRaw output, native CPU configuration/status models, and an actual modified-camera render. Count the tests run in the current checkout; higher totals from another workspace may include unpublished independent scripts. The [setup follow-up](docs/windows-setup.md#clean-checkout-and-cloud-reproduction-2026-11-04) describes the pinned OSD dependency needed by the full public test discovery.

For the existing routing helpers, from the repository root with Python 3.12 or newer:

```text
python -m unittest discover -s scripts -p test_epl9_art_routing_probe.py -v
```

The [integrated prototype report](docs/epl9-integrated-prototype.md) records additional interpreter checks and exact-image runs. Its Windows build prerequisites and ignored dependencies must be supplied separately; a clean clone is not a ready-to-flash setup.

For each meaningful change, update [CHANGELOG.md](CHANGELOG.md) with what changed, why, checks actually performed and remaining limitations, and link the detailed evidence. Keep intended behavior separate from verified behavior. Review the [installation plan](docs/firmware-installation-plan.md) before making any future release claim; documentation does not authorize camera writes.

Before pausing an investigation, leave a report with input identity, commands, observed results, remaining uncertainty and the next concrete offline experiment. For another camera or firmware build, open a separate model/build note using the [porting template](docs/porting-guide.md#new-model-or-build-report-template). Preserve the E-PL9 baseline and its exact-input guards.
