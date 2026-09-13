# Dictation validation

Implementation target: Ubuntu 26.04, GNOME Shell 50, IBus Rime. Selected model:
SenseVoice Small Yue INT8, sherpa export 2025-09-09. All speech models use the
CPU provider, with four recognition threads and one punctuation/VAD thread.

## Automated checks

- The ordinary suite passes 73 tests and 15 subtests, covering existing typing,
  deployment and GTK settings alongside new dictation ownership/setup checks.
- The C++ gesture test covers complete taps, Ctrl chords, key repeats, held
  modifiers, timeout, unmatched releases and Right Ctrl.
- `tools/smoke_dictation_bridge.py` exercises real librime and real session D-Bus:
  start/stop gesture, Unicode insertion once, duplicate/stale result rejection,
  ClearComposition/focus reset, Escape, Ctrl+C and English-mode exclusion.
- The worker's real recording pipeline was exercised with a temporary
  `pw-record` fixture returning a public test recording, then silence. It
  produced `兩隻小企鵝都有嘢食。`; cancellation produced no transcript. This test
  did not open the microphone.
- An isolated GNOME Shell 50.1 Wayland session with software rendering and a
  real GTK4/IBus text field passed compositor keyboard-event checks: double
  Left Ctrl starts/stops, the transcript is inserted once, changing fields and
  Escape cancel, a GTK password field does not start recording, and subsequent
  `hi1` / `zb1` typing produces `我，`. Capture used the public audio fixture,
  not the microphone. The desktop harness and logs are in the ignored
  `build/gnome-test/` artifacts.
- Recognition also passed inside a namespace with networking disabled and GPU
  devices hidden. Terminating the worker during capture was verified to close
  its recorder child process.
- Installed-package smoke tests passed for both IBus and Fcitx5, including
  `zb1`/`zd1` punctuation and preservation of learning on uninstall.

Run the native bridge test in a disposable session bus:

```bash
QUICK_HK_ISOLATED_BUS=1 dbus-run-session -- \
  /usr/bin/python3 tools/smoke_dictation_bridge.py
ctest --test-dir build/native --output-on-failure
node desktop/gnome/test-extension.cjs
node desktop/gnome/test-dictation.cjs
```

## CPU measurements on this computer

Intel Core i7-14700KF; warm model; sherpa-onnx 1.13.8. Six public Cantonese
recordings bundled with the upstream model, lasting 3.07–13.8 seconds, took
0.06–0.258 seconds each for VAD, recognition, punctuation and conversion.
Peak process RSS was 543,400 KiB (approximately 531 MiB). Initial model loading
in a separate check took about 0.81 seconds. These are a small development
sample and do not establish microphone-to-insertion latency or general accuracy.
Raw results are in the ignored build artifact `build/dictation-benchmark.json`.

Proper names, Cantonese particles and punctuation had some errors. The separate
English sample also had errors and uppercase output. Universal application compatibility and a measured character-error rate have
not been established.

## Desktop activation and remaining manual checks

GNOME 50 does not reload extension JavaScript in an existing session. Sign out
and back in after installing the optional extension/native plugin. Confirm
`quick-hk-dictation@quick-hk.local` is enabled in Extensions.

For a first installation, the Looking Glass activation command in the README
was also tested: the extension directory was added after an isolated GNOME 50.1
session had started, and the exact command loaded it into ACTIVE state with no
extension error. Restarting only the IBus user service loads the native plugin
without restarting the desktop. Previously imported extension updates still
require a new session to replace their JavaScript.

Validate real microphone selection, level display, double Ctrl, Escape and
focus changes in the applications used daily. Check GTK, Qt, browsers, terminals,
XWayland, password/private fields, screen locking, microphone unplugging,
long recordings, and Cantonese/English mixtures. Recognition-only measurements
above do not substitute for this desktop verification.
