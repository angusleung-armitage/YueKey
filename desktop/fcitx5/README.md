# Fcitx5 candidate themes

Install `quick-hk-light/` and `quick-hk-dark/` below
`~/.local/share/fcitx5/themes/` (or the equivalent `XDG_DATA_HOME`). Each theme
contains original SVG assets and uses Fcitx5's native numbered candidate labels,
highlight, page buttons, and cursor anchoring. Font packages are supplied by Ubuntu.

Choose **YueKey Light** or **YueKey Dark** in Fcitx5 Configuration → Addons →
Classic User Interface. Select **Noto Sans CJK HK** and the preferred size there.
The setup command can apply these settings with a backup. The root keys in
`~/.config/fcitx5/conf/classicui.conf` are:

```ini
Theme=quick-hk-light
Font=Noto Sans CJK HK 18
UseDarkTheme=False
```

Choose `Theme=quick-hk-dark` for the dark variant. Setting `UseDarkTheme=False`
keeps the explicitly selected appearance; the same themes can also be configured
as Classic UI's light/dark pair if automatic switching is preferred.

Fcitx5 Classic UI applies a selected theme to all its input methods. This is a
frontend limitation; the GNOME extension can scope its styles to 港式速成.
Candidate orientation is controlled by the Rime/frontend configuration rather
than by the theme. Kimpanel has its own presentation: disable the Kimpanel addon
to use Classic UI themes if the desktop routes candidates through Kimpanel.

The panel and highlight assets use nine-slice margins to preserve rounded corners
at different sizes. SVG rendering requires Fcitx5's standard librsvg support.
Fonts fall back through the desktop's normal font resolution if Noto CJK HK is
not installed; install `fonts-noto-cjk` for the intended appearance.

References: [Fcitx5 theme rendering](https://fcitx-im.org/wiki/Create_a_new_Fcitx_Theme),
[theme options](https://github.com/fcitx/fcitx5/blob/master/src/ui/classic/theme.h),
[Classic UI settings](https://github.com/fcitx/fcitx5/blob/master/src/ui/classic/classicui.h).

Manual release checks: select each theme in Classic UI, exercise horizontal and
vertical layouts, page buttons and number keys, and inspect text contrast and
rounded corners at fractional scales. Repeat under KWin Wayland with the
supported GTK, Qt, browser, office, and terminal applications. Theme files alone
cannot establish candidate placement or application integration correctness.
