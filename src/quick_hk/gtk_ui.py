"""GTK rendering of YueKey's shared desktop design. SPDX-License-Identifier: MIT."""
from __future__ import annotations

from . import __version__
from .settings import NUMBER_RANGES
from .settings_choices import ACTIONS, CHOICES, HINTS, LABELS, microphone_choices
from .ui_common import COLORS, PAGES


def build_window(app, settings):
    from gi.repository import Gtk, Pango
    from .deployment import desktop_directory, frontend_directory
    from .dictation_setup import microphones, status as speech_status

    c = COLORS
    css = '''
    .yuekey-settings { background: @background; color: @ink;
        font-family: "Noto Sans", "Noto Sans CJK HK", sans-serif; font-size: 13px; }
    .yuekey-settings headerbar { min-height: 32px; background: @surface; color: @ink;
        box-shadow: none; border-bottom: 1px solid @line; }
    .yuekey-settings .sidebar { background: @sidebar; color: @sidebar_text; }
    .yuekey-settings .brand-title { font-size: 28px; font-weight: 700; color: white; }
    .yuekey-settings .brand-note { color: @sidebar_text; }
    .yuekey-settings .nav { background: transparent; background-image: none;
        color: @sidebar_text; border: none; box-shadow: none; border-radius: 0;
        padding: 13px 18px; min-height: 18px; font-weight: 400; }
    .yuekey-settings .nav:hover { background: #204650; color: white; }
    .yuekey-settings .nav:checked { background: #24515B; color: white; }
    .yuekey-settings .page-title { font-size: 29px; font-weight: 700; }
    .yuekey-settings .subtitle, .yuekey-settings .note { color: @muted; }
    .yuekey-settings .card { background: @surface; border: 1px solid @line; padding: 20px; }
    .yuekey-settings .card-title { font-size: 16px; font-weight: 600; }
    .yuekey-settings .readiness { color: @accent; font-size: 18px; font-weight: 600; }
    .yuekey-settings .keycap { background: @pale; color: @accent; padding: 10px 14px;
        font-family: "Noto Sans Mono", "Noto Sans CJK HK", monospace; font-size: 16px; }
    .yuekey-settings .footer { background: @surface; border-top: 1px solid @line; padding: 14px 28px; }
    .yuekey-settings button:not(.nav), .yuekey-settings entry, .yuekey-settings spinbutton {
        background: @surface; background-image: none; color: @ink;
        border: 1px solid @line; border-radius: 2px; box-shadow: none; min-height: 22px; }
    .yuekey-settings button:not(.nav) { padding: 8px 14px; font-weight: 400; }
    .yuekey-settings button:not(.nav):hover { background: @pale; }
    .yuekey-settings button.primary { background: @accent; color: white; border-color: @accent; }
    .yuekey-settings button.primary:hover { background: @accent_hover; }
    .yuekey-settings button:disabled { opacity: .55; }
    .yuekey-settings headerbar button:not(.nav) { border: none; border-radius: 50%;
        padding: 4px; min-width: 24px; min-height: 24px; }
    .yuekey-settings button:focus-visible, .yuekey-settings entry:focus-within,
    .yuekey-settings spinbutton:focus-within, .yuekey-settings checkbutton:focus-visible {
        outline: 2px solid @accent; outline-offset: 2px; }
    .yuekey-settings .nav:focus-visible { outline-color: #9DDCD1; outline-offset: -3px; }
    .yuekey-settings entry { padding: 8px 10px; }
    .yuekey-settings spinbutton entry { border: none; }
    .yuekey-settings spinbutton button { border-width: 0 0 0 1px; padding: 4px 8px; }
    .yuekey-settings checkbutton { padding: 7px 0; }
    .yuekey-settings check { background: @surface; color: @ink; border: 1px solid @muted; }
    .yuekey-settings check:checked { background: @accent; color: white; border-color: @accent; }
    .yuekey-settings .practice { font-size: 18px; }
    .yuekey-settings .error { color: #B3261E; }
    .yuekey-settings .update-note { background: @pale; color: @ink; padding: 10px; }
    .yuekey-settings popover contents, .yuekey-settings listview { background: @surface; color: @ink; }
    .yuekey-settings listview row:selected { background: @pale; color: @ink; }
    '''
    for name, value in sorted(c.items(), key=lambda item: -len(item[0])):
        css = css.replace('@' + name, value)
    app.css_provider = Gtk.CssProvider()
    app.css_provider.load_from_string(css)
    Gtk.StyleContext.add_provider_for_display(app.window.get_display(), app.css_provider,
                                              Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    app.window.add_css_class('yuekey-settings')
    app.window.set_default_size(960, 700)
    app.window.set_size_request(860, 620)
    icons = desktop_directory() / 'icons'
    Gtk.IconTheme.get_for_display(app.window.get_display()).add_search_path(str(icons))
    app.window.set_icon_name('yuekey')
    header = Gtk.HeaderBar()
    header.set_title_widget(Gtk.Label(label='粵鍵 YueKey'))
    app.window.set_titlebar(header)
    outer = Gtk.Box()
    app.window.set_child(outer)
    sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, width_request=208)
    sidebar.add_css_class('sidebar')
    outer.append(sidebar)

    def label(parent, text, style=None):
        widget = Gtk.Label(label=text, xalign=0, wrap=True)
        widget.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        if style:
            widget.add_css_class(style)
        parent.append(widget)
        return widget

    brand = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                    margin_start=22, margin_end=22, margin_top=28, margin_bottom=26)
    sidebar.append(brand)
    logo = Gtk.Image.new_from_file(str(icons / 'yuekey-64.png'))
    logo.set_pixel_size(64)
    logo.set_halign(Gtk.Align.START)
    brand.append(logo)
    label(brand, 'YueKey', 'brand-title').set_margin_top(4)
    label(brand, '打字 · 講嘢 · 隨你', 'brand-note')
    main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
    outer.append(main)
    app.form = Gtk.Stack(vexpand=True, hhomogeneous=False, vhomogeneous=False,
                         transition_type=Gtk.StackTransitionType.NONE)
    main.append(app.form)
    app.pages, app.navigation, app.setting_rows = {}, {}, {}
    app.readiness_labels = []

    def select_page(name):
        app.form.set_visible_child_name(name)
        app.active_page = name
        for key, button in app.navigation.items():
            button.set_active(key == name)
    app.select_page = select_page

    def page(name):
        nav, title, description = PAGES[name]
        scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
                                      overlay_scrolling=False, vexpand=True)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16,
                       margin_start=28, margin_end=28, margin_top=26, margin_bottom=26)
        scroller.set_child(body)
        heading = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_bottom=6)
        body.append(heading)
        label(heading, title, 'page-title')
        label(heading, description, 'subtitle')
        app.form.add_named(scroller, name)
        app.pages[name] = scroller
        button = Gtk.ToggleButton(margin_start=10, margin_end=10, margin_top=3, margin_bottom=3)
        button.set_child(Gtk.Label(label=nav, xalign=0))
        button.add_css_class('nav')
        button.connect('clicked', lambda *_: select_page(name))
        sidebar.append(button)
        app.navigation[name] = button
        return body

    def card(parent, title):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.add_css_class('card')
        parent.append(box)
        label(box, title, 'card-title').set_margin_bottom(2)
        return box

    def button(parent, text, callback, primary=False):
        widget = Gtk.Button(label=text, halign=Gtk.Align.START)
        if primary:
            widget.add_css_class('primary')
        widget.connect('clicked', callback)
        parent.append(widget)
        return widget

    def check(parent, name):
        control = Gtk.CheckButton(label=LABELS[name], active=getattr(settings, name))
        parent.append(control)
        app.controls[name] = control
        app.fields[name] = control.get_active
        app.setting_rows[name] = control
        return control

    def choice(parent, name, choices=None, stacked=False):
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL if stacked else Gtk.Orientation.HORIZONTAL,
                      spacing=8)
        parent.append(row)
        text = label(row, LABELS[name])
        text.set_hexpand(True)
        if name in NUMBER_RANGES:
            low, high = NUMBER_RANGES[name]
            control = Gtk.SpinButton.new_with_range(low, high, 1)
            control.set_value(getattr(settings, name))
            control.set_numeric(True)
            app.fields[name] = control.get_value_as_int
        else:
            choices = choices if choices is not None else CHOICES[name]
            values = [key for key, _ in choices]
            control = Gtk.DropDown.new_from_strings([text for _, text in choices])
            # Long microphone names must not force the window wider than its monitor.
            control.set_enable_search(name == 'dictation_microphone')
            factory = Gtk.SignalListItemFactory()
            factory.connect('setup', lambda _, item: item.set_child(
                Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END, max_width_chars=28)))
            factory.connect('bind', lambda _, item: item.get_child().set_label(item.get_item().get_string()))
            control.set_factory(factory)
            control.set_selected(values.index(getattr(settings, name)))
            app.choice_values[name] = values
            app.fields[name] = lambda: app.choice_values[name][control.get_selected()]
        control.set_valign(Gtk.Align.CENTER)
        if not stacked:
            control.set_size_request(220, -1)
        else:
            control.set_hexpand(True)
        text.set_mnemonic_widget(control)
        row.append(control)
        app.controls[name] = control
        app.setting_rows[name] = row
        return control

    home = page('overview')
    ready = card(home, '速成輸入 · Quick typing')
    app.typing_status = label(ready, '正在檢查 · Checking…', 'readiness')
    label(ready, '保留現有設定與學習資料，再套用港式速成。\n'
                'Set up typing with your existing preferences and learned words preserved.', 'note')
    app.setup_button = button(ready, '設定速成 · Set up typing', app._setup_typing, True)
    practice = card(home, '試打一句 · Try it out')
    keys = Gtk.Box(spacing=10)
    practice.append(keys)
    for code, character in [('hi1', '我'), ('zb1', '，'), ('zd1', '。')]:
        label(keys, f'{code}  →  {character}', 'keycap')
    guide = ('在輸入法選單選 Rime，即可使用港式速成。\n'
             'Select Rime in the input-method menu. Cantonese Quick is ready by default.'
             if app.frontends == ['fcitx5'] else
             'Super + Space 選「中文（Rime）」，即可使用港式速成。\n'
             'Select Chinese (Rime) with Super + Space. Cantonese Quick is ready by default.')
    label(practice, guide, 'note')
    app.practice_entry = Gtk.Entry()
    app.practice_entry.add_css_class('practice')
    app.practice_entry.update_property([Gtk.AccessibleProperty.LABEL], ['試打一句 · Try it out'])
    practice.append(app.practice_entry)
    voice_card = card(home, '廣東話語音 · Cantonese voice')
    app.readiness_labels.append(label(voice_card, '', 'readiness'))
    label(voice_card, '連按兩次 Ctrl 開始／停止。辨識在你的電腦上進行。\n'
                      'Double-tap Ctrl to start or stop. Recognition stays on your computer.', 'note')
    button(voice_card, '語音設定 · Voice settings', lambda *_: select_page('voice'))

    typing = page('typing')
    appearance = card(typing, '候選字 · Candidates')
    check(appearance, 'horizontal')
    for name in ('page_size', 'font_size', 'theme'):
        choice(appearance, name)
    check(appearance, 'show_candidates')
    label(appearance, HINTS['show_candidates'], 'note')
    behavior = card(typing, '輸入習慣 · Typing')
    check(behavior, 'learning')
    check(behavior, 'prediction')
    label(behavior, HINTS['prediction'], 'note')
    check(behavior, 'ascii_punctuation')
    choice(behavior, 'switch_key')
    label(behavior, '儲存後會重新部署。重新載入輸入法後生效。\n'
                    'Saving deploys your changes. Reload the input method to activate them.', 'note')

    voice = page('voice')
    speech = card(voice, '啟用廣東話語音 · Enable Cantonese voice')
    app.readiness_labels.append(label(speech, '', 'readiness'))
    bundled = speech_status().get('bundled')
    label(speech, '安裝包已包含語音模型；毋須額外下載。\n'
                  'Speech models are included in the installer. No extra download is needed.' if bundled else
                  '首次準備會下載語音模型；之後無需上傳錄音。\n'
                  'First setup downloads speech models. Audio is processed locally.', 'note')
    app.enable_button = button(speech, LABELS['dictation_enabled'], app._toggle_dictation, True)
    app.controls['dictation_enabled'] = app.enable_button
    app.fields['dictation_enabled'] = lambda: app.dictation_enabled
    app.speech_hint = label(speech, 'SenseVoice Small Yue · CPU · 離線', 'note')
    app.extension_hint = label(speech,
        '語音提示已更新，GNOME 會在下次登入載入新介面。\n'
        'Microphone UI updated; GNOME loads it at the next login.', 'update-note')
    button(speech, '驗證語音模型 · Verify speech models' if bundled else '準備語音模型 · Set up speech models',
           lambda *_: app._start_command(['dictation', 'setup'], '正在準備語音模型… · Preparing speech models…'))
    recording = card(voice, '收音與快捷鍵 · Microphone and shortcut')
    choice(recording, 'dictation_key')
    choice(recording, 'dictation_microphone', microphone_choices(microphones(), settings.dictation_microphone), True)
    button(recording, ACTIONS['refresh_microphones'], app._refresh_microphones)
    check(recording, 'dictation_punctuation')
    label(recording, 'Ctrl × 2 開始／停止，Esc 取消。\nDouble Ctrl starts/stops; Esc cancels.\n\n'
                    + HINTS['dictation_key'] + '\n\n'
                    '語音服務在背景運行，可以關閉設定視窗。\n'
                    'Dictation runs in the background. You can close Settings.', 'note')

    advanced = page('advanced')
    storage = card(advanced, '輸入資料夾 · Typing folder')
    for frontend in app.frontends:
        folder = frontend_directory(frontend)
        label(storage, 'IBus · GNOME' if frontend == 'ibus' else 'Fcitx5 · KDE', 'note')
        path = Gtk.Entry(text=str(folder), editable=False)
        path.update_property([Gtk.AccessibleProperty.LABEL], ['輸入資料夾 · Typing folder'])
        storage.append(path)
        button(storage, '開啟資料夾 · Open folder', lambda _, p=folder: app._open_folder(p))
    recovery = card(advanced, '學習與移除 · Learning and removal')
    label(recovery, '重設學習前，請先停止輸入法。原有資料會先備份。\n'
                    'Stop the input method before resetting learning. Existing data is backed up.', 'note')
    app.reset_button = button(recovery, ACTIONS['reset_learning'], app._reset)
    label(recovery, '移除速成方案會保留學習資料及輸入法引擎。\n'
                    'Removing YueKey typing keeps learned words and the input-method engine.', 'note')
    button(recovery, '移除速成方案 · Remove YueKey typing',
           lambda *_: app._start_command(['uninstall', '--frontend', app.frontend],
                                         '正在移除速成方案… · Removing YueKey typing…'))
    about = card(advanced, f'粵鍵 YueKey  {__version__}')
    label(about, '速成 · 標點 · 廣東話語音\nQuick typing · Punctuation · Cantonese voice\n\n'
                 '原創程式採 MIT 授權；其他元件保留各自授權。\n'
                 'Original code: MIT. Other components retain their own licenses.', 'note')
    button(about, '安裝指南 · Installation guide', app._open_guide)
    sidebar.append(Gtk.Box(vexpand=True))
    tail = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_start=24,
                   margin_end=24, margin_bottom=24, margin_top=16)
    sidebar.append(tail)
    label(tail, '本機辨識 · Local processing\nCPU only', 'brand-note')
    label(tail, f'YueKey {__version__}', 'brand-note')
    footer = Gtk.Box(spacing=16)
    footer.add_css_class('footer')
    main.append(footer)
    app.status_scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
        max_content_height=96, propagate_natural_height=True, hexpand=True)
    app.status = Gtk.Label(label='準備就緒 · Ready', xalign=0, wrap=True, selectable=True)
    app.status.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
    app.status.add_css_class('note')
    app.status_scroller.set_child(app.status)
    footer.append(app.status_scroller)
    app.spinner = Gtk.Spinner(valign=Gtk.Align.CENTER)
    footer.append(app.spinner)
    app.apply_button = button(footer, ACTIONS['apply'], app._apply, True)
    app.apply_button.set_valign(Gtk.Align.CENTER)
    select_page('overview')
