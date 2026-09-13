# Code review — YueKey 0.3.0

Reviewed on 2026-09-13: installation/removal, Windows keyboard and focus handling,
speech capture/result ownership, shared Rime configuration, Linux dictation
bridge, and package/release automation. This is a focused correctness review;
it does not certify every desktop application or audio driver.

## Findings fixed

| Priority | Finding and consequence | Fix and regression evidence |
|---|---|---|
| P2 | Windows used ordinary YAML loading and could discard duplicate settings or accept conflicting schema-list patches when rewriting `default.custom.yaml`. | Both platforms now use the strict parser in [rime_config.py](../src/quick_hk/rime_config.py). Windows tests reject duplicate keys, conflicting patches and malformed schema entries before creating any files. |
| P2 | Both removal paths changed live files before checking later backups. A missing backup could leave only part of the typing scheme installed. Windows also validated manifest entries during mutation. | [Windows removal](../src/quick_hk/windows_setup.py) validates the full manifest and reads required backups first. [Ubuntu removal](../src/quick_hk/deployment.py) preflights both frontend plans. Fault tests verify every live file remains intact if a later backup or manifest entry is invalid. |
| P2 | A PortAudio abort/close exception could escape the Windows UI callback or skip the decoder's end marker, leaving dictation stuck on “previous recording is still stopping.” | [WindowsRecording](../src/quick_hk/dictation_worker.py) serializes abort/close and handles errors while still releasing the decoder. Injected abort and close failures stop both threads without emitting a transcript. |

Model-loading imports are also inside the setup error handler, so a missing
runtime dependency produces a retryable error instead of leaving the button
disabled. The Linux worker now waits for both capture and decoding to finish
before accepting another recording.

## Installer and release changes

- Windows setup EXE installs per user, adds a Start Menu shortcut and registers
  an uninstaller. A stable application ID supports subsequent updates.
- A running-companion mutex prevents setup from overwriting active files.
  Uninstall removes registered application files while retaining Rime data,
  learned dictionaries, backups, downloaded models and unrelated user files.
- The existing five Ubuntu `.deb` packages remain compatible with `quick-hk`
  commands and settings. GNOME and KDE integration remain separate choices.
- CI tests setup, same-version repair, running-app rejection, the installed
  executable and uninstall on a disposable Windows runner. The installed app
  checks Unicode insertion, password/stale-field rejection and CPU recognition
  of a public Cantonese sample without opening a microphone.
- The release requires five DEBs, setup EXE, portable ZIP and corresponding
  source before generating checksums and publishing.

## Validation and remaining limits

Local Ubuntu build and regression checks are recorded in
[compatibility.md](compatibility.md). The release workflow must pass on both
platforms before publishing version 0.3.0.

Windows 11 physical microphone tests and the desktop application matrix remain
outstanding. Windows currently has no continuation-prediction plugin, and its
EXE is unsigned. The current Ubuntu packages target 26.04 amd64 and the tested
librime ABI. No claim of Windows 10, ARM64, or universal application support is
made.
