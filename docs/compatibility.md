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
The GitHub Actions workflow performs the full build and these checks; it has
been added locally and has not yet run on GitHub.

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
