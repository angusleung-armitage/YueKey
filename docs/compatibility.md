# Compatibility and release checks

Target: Ubuntu 26.04 amd64 GNOME 50 / IBus and Kubuntu 26.04 amd64 KDE / Fcitx5.
Wayland sessions and their XWayland clients are in scope. Other Ubuntu releases,
desktop versions and architectures are not certified.

## Input behavior and data

YueKey derives Quick codes from the first and last Cangjie letters. The source
manifest in [data/sources.lock.json](../data/sources.lock.json) records the open
Cangjie, Quick and Cantonese datasets and their pinned versions.

Project defaults: horizontal nine-candidate pages, visible candidates, learning
and predictions on, Chinese punctuation, Left Shift for English mode. Return
commits literal input as in Rime. Selection ordering, prediction weights and
learning follow Rime and the selected open data. In explicit
Space-to-open mode the hidden preedit may show Latin codes until candidates are
revealed. Fonts and window details follow native GNOME/Fcitx renderers.

## Automated checks

`make test` covers generated code integrity/reproducibility, actual librime key
sequences and learning, session-isolated predictions, staging/rollback, settings,
and preserving user configuration. Native tests require `make all` and the
Ubuntu environment; a skipped engine suite is not a successful engine check.

`node desktop/gnome/test-extension.cjs` checks the extension's signal lifecycle,
schema scoping, restore behavior, and settings changes using isolated mocks.
These mocks cannot establish live GNOME compatibility.

## Recorded local validation — 2026-09-12

- **65 tests passed**, including 38 actual librime acceptance cases, GTK4/Xvfb,
  data integrity, settings and transactional deployment checks. No skipped tests
  in the Xvfb run. The warm two-key roundtrip p95 check passed its 20 ms limit.
- Restored 38 legacy punctuation mappings across 21 `z` codes. Regression checks
  cover `zb1` → ， and other common marks, `z` after a complete character code,
  punctuation-to-character continuation, and dismissing predictions with `z`.
- GNOME extension lifecycle/scoping mock check passed.
- The four `.deb` packages installed together with their dependencies in a fresh
  Ubuntu 26.04 container. Lintian reported no errors; its four remaining warnings
  say the initial changelog does not close a Debian bug.
- Installed IBus-Rime and Fcitx5-Rime, each on a private D-Bus/Xvfb session,
  committed `你好`, loaded the packaged native prediction plugin, offered `好`
  after `你`, cleared suggestions on reset, and resumed after focus out/in.
- Repeated setup/deployment and doctor succeeded for both profiles. Uninstall
  restored an existing commented configuration byte for byte and preserved real
  learning databases and frontend user state.

Versions: librime `1.16.1+dfsg1-1build1`, Lua plugin
`1.16.1+dfsg1~git20250707-1build1`, IBus-Rime `1.6.0-1`,
Fcitx5 `5.1.19-1`, Fcitx5-Rime `5.1.13-1`, GTK4
`4.22.4+ds-0ubuntu0.1`, Python `3.14.3-0ubuntu2`. Installing the GNOME integration
resolved GNOME Shell `50.1-0ubuntu1.2`.

The private IBus smoke test emits upstream GI floating-object warnings and a
portal-startup warning in the minimal container; its assertions still pass.
The GTK test emits upstream Python/GI deprecation warnings. These runs use Xvfb
and direct frontend protocols, not an interactive Wayland desktop.

Reproduce the package checks after building:

```bash
docker run --rm --init -v "$PWD:/work:ro" quick-hk-dev:26.04 \
  python3 tools/test_packages.py
```

Add `--network host` to `docker run` and `--with-desktops` to the Python command
to also install both desktop packages and resolve all their apt dependencies.
The script refuses to run outside a root Docker container. It is intended for
fresh disposable containers with no personal home or desktop bus mounted.
The GitHub Actions workflow performs the full build and these checks. Both
Ubuntu and Windows jobs passed on 2026-09-13 in
[run 34740387882](https://github.com/angusleung-armitage/YueKey/actions/runs/34740387882).

## Live release matrix — must be recorded separately

The optional fifth package, CPU Cantonese dictation, was added on 2026-09-13.
Its automated and isolated GNOME/GTK Wayland checks are recorded in
[dictation-validation.md](dictation-validation.md). The broader application
matrix below still requires separate validation.

For each desktop, record package/application version, Wayland versus XWayland,
typed text, cursor placement, focus behavior and actual result for:

| Application category | GNOME / IBus | KDE / Fcitx5 |
|---|---|---|
| GTK3 and GTK4 text fields | Pending live desktop QA | Pending live desktop QA |
| Qt text fields | Pending live desktop QA | Pending live desktop QA |
| Firefox | Pending live desktop QA | Pending live desktop QA |
| Chromium and Electron | Pending live desktop QA | Pending live desktop QA |
| LibreOffice | Pending live desktop QA | Pending live desktop QA |
| Terminal application | Pending live desktop QA | Pending live desktop QA |

Also check native popup anchoring near every screen edge, multiple monitors,
fractional scaling, both layouts and themes, focus changes, secure input fields,
extension disable/re-enable, daemon restart, and package upgrades. Honor secure
field restrictions exposed by the frontend; X11 clients may not expose them.
Headless tests alone do not establish production desktop readiness.

Package checks include installation into an isolated Ubuntu container, setup for
both frontend profiles, repeated deployment, and uninstall with existing custom
configuration. A graphical login is still needed to activate desktop input.

## Windows automated validation — 2026-09-13

On the GitHub Windows Server 2025 x64 runner, Python 3.12.10:

- All seven Windows deployment/gesture/result-guard tests passed.
- Both x86 and x64 Rime DLLs extracted from the checksum-pinned official Weasel
  0.17.4 installer loaded the Windows schema and passed `hi1`, `zb1`, `zd1`,
  third-letter commit and unmatched-code checks.
- The packaged x64 executable opened its actual bilingual setup window, checked
  that controls fit and showed its dictation overlay without stealing focus.
- Its keyboard/focus hooks and MTA UI Automation worker started successfully.
- Unicode `我，𨋢` reached an isolated native Edit control exactly once.
  A password control and the previous stale target were rejected.
- The packaged runtime initialized the INT8 ASR, VAD and punctuation models on
  CPU, passed a silence check and decoded a checksum-pinned public Cantonese WAV.
- No physical microphone was opened during automated testing.

The Windows 11 target still needs real microphone and application tests, including
Weasel-active dictation in browsers, office applications and text editors.
Windows 10, ARM64 and 32-bit companion builds are not validated. The 0.2/0.3 Windows builds did not include continuations; 0.4.0 adds them through Rime Lua.

## YueKey 0.3.0 review and packaging — 2026-09-13

Local Ubuntu 26.04 container checks passed: **85 tests and 21 subtests**, both
GNOME lifecycle suites, the native gesture test and isolated dictation bridge.
The new DEBs installed and exercised real IBus and Fcitx5 input, punctuation,
prediction and repeat deployment. Uninstall restored configuration and retained
learning. Lintian reported no errors, with only the five existing initial-upload
changelog warnings.

The [code review](REVIEW.md) records the fixed configuration, removal and capture
shutdown failures. Windows setup EXE integration results are recorded with the
GitHub release workflow; real Windows microphone/application checks remain
separate from these automated tests.

The Windows installer checks also passed in [run 34741463809](https://github.com/angusleung-armitage/YueKey/actions/runs/34741463809)
at commit `cb0afe5`: 11 Windows tests and 6 subtests, both official Weasel DLL
architectures, setup and same-version repair into a path with spaces and Chinese
characters, running-companion rejection, and uninstall preservation. The
installed executable passed Unicode/password/focus checks and CPU Cantonese
fixture recognition. The Ubuntu job, including all desktop package dependencies,
also passed. No physical microphone was opened.


## YueKey 0.4.0 platform parity — 2026-09-13

See the [bilingual feature matrix and implementation record](platform-parity.md).
Local Ubuntu 26.04 checks passed: 89 tests, 21 subtests and one Windows-only
file-lock test skipped. Both installed input frontends passed actual character,
punctuation, continuation and focus/reset checks. The new Fcitx5 native bridge
passed start/stop, Unicode once, unauthorized/replayed/premature result rejection,
password/sensitive/disabled fields, focus/reset/cursor/key cancellation, ASCII
mode, right Ctrl and controller-owner loss. The production KDE controller passed
start/stop and insertion with a deterministic worker; no microphone was opened.
Shared service files passed single-frontend and combined uninstall preservation.
Windows release CI additionally exercises the actual Weasel 32/64-bit libraries,
Windows file locking and the installed companion/runtime. Results are available
with the 0.4.0 GitHub Actions release run.

The full Linux and Windows workflows passed at `efaf38d` in
[run 34743641409](https://github.com/angusleung-armitage/YueKey/actions/runs/34743641409).
Windows passed 15 tests and 6 subtests, actual Weasel 0.17.4 in both architectures,
exclusive learning-lock/reset checks, and the installed EXE's settings controls,
nonactivating indicator, Unicode/password guards and public Cantonese CPU fixture.
Setup, repair, optional login startup, running-app protection and uninstall
preservation also passed. The release workflow repeats these checks and adds a
second real-Rime run with changed page size, candidate visibility, learning,
prediction, punctuation and language-switch preferences.


## YueKey 0.4.1 microphone compatibility

WASAPI streams now request Windows shared-mode sample-rate conversion when
capturing mono 16 kHz audio. This supports system mixers configured at 44.1/48 kHz
without requesting exclusive access. MME and other backends keep their normal
stream settings. A regression check covers backend selection and conversion
parameters; real microphone hardware checks remain necessary.

## YueKey 0.5.0 all-in-one and architecture validation

Verified on 2026-09-13 at commit `1adac1a57759e87e4444e89fccc95a23ea289eb1`,
[Actions run 34746384659](https://github.com/angusleung-armitage/YueKey/actions/runs/34746384659).
Every required architecture job passed:

| Target | Checks |
| --- | --- |
| Ubuntu 26.04 amd64 and arm64 | 92 tests, 1 Windows-only skip, 21 subtests per architecture; native gesture/Rime bridge, GNOME extension lifecycle, DEB metadata, IBus/Fcitx5 input and KDE controller |
| Windows x64, x86 and ARM64 | 16 tests and 6 subtests per architecture; official Weasel runtime, setup/repair/startup/uninstall, packaged settings window, Unicode insertion and password/focus guards |
| All five CPU runtimes | Verified public Cantonese WAV and silence; CPU execution; no microphone opened |

The all-in-one DEBs contain the isolated recognizer and all four pinned model
files. Installed offline setup ran as an unprivileged user. APT migration tests
replaced fixtures for the five old package ownership/dependency relationships,
including an overlapping command path; pre-existing Rime preferences survived.
Both input profiles were deployed repeatedly, exercised and removed while
preserving user configuration and learning. Frozen workers restore the system
library path before starting PipeWire.

GTK startup now uses `Gtk.Application` initialization rather than cached legacy
import-time initialization. Windows ARM64 tests dismiss a known first-login
account prompt on the disposable runner and, if required, activate only the
verified, unobscured test Edit control. This setup is restricted to CI; production
focus and secure-field guards remain in effect. The x86 executable uses the
28-byte Win32 INPUT layout; x64 and ARM64 use 40 bytes.

此版本已在原生 Linux x64／ARM64 及 Windows x64／x86／ARM64 執行上述自動測試。Linux 語音模型及執行環境已包含在 DEB，普通使用者可離線完成設定。Windows x86 測試使用 WOW64；完整 32-bit Windows 10、不同實機麥克風及完整 Wayland 桌面仍需另外驗證。詳見[架構與限制](ARCHITECTURES.md)。

These checks do not establish support for Linux i386/ARM32, older Ubuntu/Debian
versions, every desktop/application, or every physical microphone. Windows x86
was tested under WOW64, not a complete 32-bit Windows installation. See
[ARCHITECTURES.md](ARCHITECTURES.md) for the exact boundaries.
