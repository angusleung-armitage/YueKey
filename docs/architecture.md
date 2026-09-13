# Implementation and boundaries

YueKey provides Cantonese Quick typing on Ubuntu and Kubuntu 26.04, with
optional local CPU dictation on GNOME. Rime controls ranking and learning.

1. `tools/fetch_sources.py` verifies the lock manifest and downloads build inputs.
2. `tools/build_data.py` emits a deterministic Quick dictionary, suffix/weight
   prediction input, and coverage report. It accepts one-letter codes, preserves
   alternatives, and includes Unicode supplementary-plane HK characters.
3. CMake builds the scoped deployer, headless probe, and the adapted official
   prediction plugin. Its database is immutable; mutable candidate state is
   cached per Rime engine, never shared by schema across input contexts.
   A fresh commit notification is required for suggestions, so a frontend reset
   cannot recreate candidates from stale commit history.
4. Rime owns candidate lookup, Unicode text, personal learning, and the normal
   commit lifecycle. `rime/lua/quick_hk.lua` controls bounded Quick composition,
   explicit candidate revelation, and dismissal of prediction on a new code.
5. The Python CLI stages all target profiles before writing any live files.
   Files are backed up and recorded by hash in a per-user state manifest.
   Compilation targets this schema and relevant frontend/default configuration.
6. IBus and Fcitx5 retain ownership of input contexts and cursor placement.
   Desktop assets restyle their native windows. The GTK application edits the
   same validated settings used by the CLI and deploys without blocking its UI.

Generated settings use one shared model, with independent learning/prediction,
candidate visibility, punctuation, page size, orientation, font size, theme,
and English toggle. Deployment writes YueKey patches and merges the scheme
entry into the existing Rime switcher configuration. Ambiguous patches are
reported instead of overwriting them.

There is no HTTP service, global keyboard hook, or clipboard substitution.
Runtime typing needs no source checkout or network. Each frontend has a separate
user database; live LevelDB directories are never copied during deployment.

Data uses Cangjie 5 as a chosen open baseline. Initial frequencies are from the
Cantonese essay data (minimum weight one), ties sort by Unicode character, and
personal learning follows Rime. Rare/simplified code-table variants are retained
for character coverage; there is no automatic simplified-to-traditional rewrite
that could change the requested character or its code.

Prediction training uses observed dictionary/frequency words of 2–12 Unicode
characters. Prefixes up to four characters map to suffixes, ordered by descending
frequency then Unicode text; at most 90 continuations are retained per prefix.
Only one consecutive prediction is suggested by default. This is an open-data
implementation of 關聯字 based on the recorded frequency corpus.

Debugging interfaces: `quick-hk doctor --json`, the generated `coverage.json`,
the native `quick-hk-probe` JSON-line test driver, and staged compiler logs.
The probe is a development artifact, not part of installed runtime packages.

## CPU-only dictation

The optional `quick-hk-dictation` package adds a native Rime processor before
the ordinary keyboard processors. Two complete Control taps within 400 ms
toggle a UUID-scoped request. Holds, repeats and chords do not trigger it.
The processor is deployed only for enabled IBus profiles; ordinary typing has
no speech dependency. A separate GNOME extension supplies the focus guard and
non-focusable microphone overlay, independently of candidate styling.

The controller owns `org.quick_hk.Dictation` on session D-Bus. It starts an
isolated Python 3.12 worker and exchanges JSON messages through private pipes.
The worker captures PipeWire PCM, runs Silero VAD and SenseVoice Small Yue INT8
in bounded chunks, restores punctuation with CT-Transformer INT8, and converts
to HK Traditional characters with OpenCC. Explicit CPU providers are used for
all models. The punctuation pass is discarded if it changes recognized words.
Runtime and model versions/hashes are pinned in the speech setup module and
requirements lock file. Only explicit setup performs network downloads.

The GNOME extension owns `org.quick_hk.DictationDesktop`. Focus changes, field
resets, content-purpose changes and surrounding-text edits invalidate its
generation. The controller also remembers the IBus context path and window.
It queues a matching result through `org.quick_hk.RimeDictation`, then asks the
desktop to recheck focus and send a Right Ctrl wake tap through the compositor.
IBus accepts key events only from the context's owning application, so the
application forwards this tap normally. Only the native processor consumes
queued text, on Rime's input thread, then acknowledges the commit. The controller
waits for that acknowledgement and expires undelivered results after five seconds.
The wake tap inserts no character if the request was cancelled. Reset, cancellation,
schema destruction and unrelated typing invalidate native requests. Duplicate
and stale results cannot commit. No clipboard replacement or synthetic
CommitText D-Bus signal is used.

Recognition is performed while speech chunks finish, but there is one insertion
after stopping. Audio, text and queues are bounded and transient. The desktop
checks password/private hints from both GNOME's input method and its IBus panel
signals, including direct IBus clients. Unknown content types block dictation.
Integration with individual applications still requires validation, especially direct IBus and
XWayland clients with limited focus metadata.

## Windows companion and release builds

The Windows package uses Weasel for TSF input. `prepare_windows_data.py` consumes
exactly the same generated character dictionary as Ubuntu and removes components
that require Ubuntu native modules. Rime still owns candidate selection and local
learning. Continuation prediction remains Ubuntu-only in this version.

`windows_setup.py` adds the scheme to the existing Weasel configuration, backs up
changed files and records their installed hashes. Removal restores only unchanged
managed files and preserves learned dictionaries and later user edits.

`windows_app.py` provides the bilingual setup window and optional speech controls.
It shares `Recognizer`, the pinned models and VAD/decode path with Ubuntu.
`WindowsRecording` captures 16 kHz mono PCM through PortAudio using the system's
default microphone. Model loading and decoding run off the GUI thread.

`windows_input.py` uses low-level Ctrl hooks plus mouse and focus events to track
cancellation, without retaining typed characters. UI Automation queries run in a
separate MTA thread; unknown/password controls and stale snapshots are rejected.
A request binds the foreground window, provider process, runtime control ID and
activity generation. A matching result is consumed once and inserted as one
Unicode SendInput batch. There is no clipboard fallback or automatic retry after
a partial insertion. This Windows companion is independent of the active IME;
users must finish any pending IME composition before dictating.

GitHub Actions builds the Windows executable on Windows and Ubuntu packages in an
Ubuntu 26.04 container. Tests cover actual Weasel DLL typing, focus/password
checks, packaged CPU model initialization, both Linux frontends and the Rime
D-Bus bridge. Tag releases require all jobs to pass and publish a complete set of
packages, corresponding dictionary source, license notices and SHA-256 checksums.
The original project code is MIT; third-party data/code keep their own terms.
