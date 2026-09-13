# GNOME candidate styling

Install `quick-hk@quick-hk.local/` as a GNOME Shell extension. The setup command
copies it to the user's extensions directory; enable **粵鍵 YueKey · Candidates**
in Extensions after logging back in. It declares GNOME Shell 50 compatibility.

Setup also installs `ibus-setup-rime.desktop` in the user's applications directory.
GNOME looks up this desktop ID for Chinese (Rime)'s Preferences action; it opens
YueKey Settings for the IBus profile. The launcher is backed up and restored
by the same deployment/uninstall transaction as the other managed assets.
Reopen GNOME Settings after setup to refresh the action. Rime still contains
multiple schemes: choose 港式速成 from F4 while a text field is focused.

The extension styles the existing `IBusManager.getIBusManager()._candidatePopup`
actor. It never replaces key handlers, candidate selection, cursor placement, or
the popup's contents. `InputSourceManager.currentSource` must be IBus `rime`,
and its `InputMode` property label must equal `港式速成`. `ibus-rime` supplies
this label from Rime's current schema name in Chinese mode. Other schemas, Abc
mode, and unavailable properties use the desktop's original appearance.

Settings deployment writes `~/.config/quick-hk/presentation.json`, respecting
`XDG_CONFIG_HOME`, with `theme` (`light` or `dark`) and `font_size` (10–36 pt).
The extension watches that directory, including atomic replacement saves.
Candidate orientation and count come from the Rime/IBus lookup table.
Disabling the extension removes all its classes and restores the previous
inline font style. A later style change made by another extension is preserved.

This uses one private GNOME actor reference, so new major Shell versions need
source review and desktop testing before updating `shell-version`.

Primary integration references:

- [GNOME Settings 50.3 IBus preferences launcher lookup](https://github.com/GNOME/gnome-control-center/blob/50.3/panels/keyboard/cc-input-source-ibus.c)
- [GNOME Shell 50 IBus manager](https://github.com/GNOME/gnome-shell/blob/50.0/js/misc/ibusManager.js)
- [GNOME Shell 50 input sources and property updates](https://github.com/GNOME/gnome-shell/blob/50.0/js/ui/status/keyboard.js)
- [GNOME Shell 50 native candidates](https://github.com/GNOME/gnome-shell/blob/50.0/js/ui/ibusCandidatePopup.js)
- [IBus Rime InputMode implementation](https://github.com/rime/ibus-rime/blob/master/rime_engine.c)

Manual release checks: enable while Rime is active, switch between 港式速成 and
another schema, toggle Abc, edit font/theme, disable and re-enable, and restart
IBus. Check both layouts, light/dark appearance, selection and paging, fractional
scale, screen edges, and multiple monitors. Automated lifecycle checks cannot
establish live Shell compatibility or correct cursor placement in applications.
