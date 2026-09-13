"""YueKey's bilingual desktop layout, separate from Windows input hooks.

SPDX-License-Identifier: MIT
"""
from __future__ import annotations

import tkinter as tk
from tkinter import font, ttk
from pathlib import Path
import sys

from . import __version__

COLORS = dict(background='#F3F6F8', surface='#FFFFFF', ink='#142C37', muted='#526773',
              sidebar='#102F37', sidebar_text='#C2D5DC', accent='#007D75',
              accent_hover='#006960', pale='#E6F4F0', line='#DCE5E9')


def build_window(app, root):
    c = COLORS
    for name in ('TkDefaultFont', 'TkTextFont', 'TkMenuFont'):
        font.nametofont(name).configure(family='Segoe UI', size=10)
    font.nametofont('TkFixedFont').configure(family='Consolas', size=11)
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', font=('Segoe UI', 10), background=c['surface'], foreground=c['ink'])
    style.configure('TFrame', background=c['surface'])
    style.configure('TLabel', background=c['surface'], foreground=c['ink'])
    style.configure('Muted.TLabel', foreground=c['muted'])
    style.configure('TButton', padding=(14, 9), background=c['surface'], foreground=c['ink'],
                    bordercolor=c['line'], lightcolor=c['line'], darkcolor=c['line'], focuscolor=c['accent'])
    style.map('TButton', background=[('active', c['pale']), ('disabled', c['background'])],
              foreground=[('disabled', c['muted'])])
    style.configure('Primary.TButton', background=c['accent'], foreground='white',
                    bordercolor=c['accent'], lightcolor=c['accent'], darkcolor=c['accent'])
    style.map('Primary.TButton', background=[('active', c['accent_hover']), ('disabled', '#BCD2D2')],
              foreground=[('disabled', '#455F64')])
    style.configure('Nav.TButton', background=c['sidebar'], foreground=c['sidebar_text'],
                    anchor='w', padding=(18, 12), borderwidth=0, relief='flat',
                    lightcolor=c['sidebar'], darkcolor=c['sidebar'], bordercolor=c['sidebar'])
    style.map('Nav.TButton', background=[('active', '#204650')], foreground=[('active', 'white')])
    style.configure('Selected.Nav.TButton', background='#24515B', foreground='white')
    style.map('Selected.Nav.TButton', background=[('active', '#2B5D67')])
    style.configure('TCheckbutton', padding=(0, 7), background=c['surface'], focuscolor=c['accent'])
    style.map('TCheckbutton', background=[('active', c['surface'])])
    style.configure('TCombobox', padding=7, fieldbackground=c['surface'], arrowsize=16,
                    bordercolor=c['line'], lightcolor=c['line'], darkcolor=c['line'])
    style.map('TCombobox', fieldbackground=[('readonly', c['surface'])],
              selectbackground=[('readonly', c['surface'])], selectforeground=[('readonly', c['ink'])])
    style.configure('TEntry', padding=10, fieldbackground=c['surface'], bordercolor=c['line'])
    style.configure('Horizontal.TProgressbar', background=c['accent'], troughcolor=c['line'],
                    borderwidth=0, lightcolor=c['accent'], darkcolor=c['accent'])

    root.title('粵鍵 YueKey')
    assets = (Path(sys._MEIPASS) / 'windows-assets' if hasattr(sys, '_MEIPASS') else
              Path(__file__).resolve().parents[2] / 'desktop/windows/assets')
    root.yuekey_icon = tk.PhotoImage(file=str(assets / 'yuekey.png'))
    root.iconphoto(True, root.yuekey_icon)
    root.configure(background=c['background'])
    root.geometry('1000x760')
    root.minsize(860, 620)
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)
    sidebar = tk.Frame(root, background=c['sidebar'], width=208)
    sidebar.grid(row=0, column=0, sticky='nsew', rowspan=2)
    sidebar.grid_propagate(False)
    sidebar.grid_columnconfigure(0, weight=1)
    sidebar.grid_rowconfigure(6, weight=1)
    brand = tk.Frame(sidebar, background=c['sidebar'])
    brand.grid(row=0, column=0, sticky='ew', padx=22, pady=(28, 26))
    tk.Label(brand, text='粵', font=('Microsoft JhengHei UI', 24, 'bold'), width=2,
             background=c['accent'], foreground='white').pack(anchor='w')
    tk.Label(brand, text='YueKey', font=('Segoe UI Semibold', 21), background=c['sidebar'],
             foreground='white').pack(anchor='w', pady=(12, 2))
    tk.Label(brand, text='打字 · 講嘢 · 隨你', font=('Segoe UI', 10), background=c['sidebar'],
             foreground=c['sidebar_text']).pack(anchor='w')

    content = tk.Frame(root, background=c['background'])
    content.grid(row=0, column=1, sticky='nsew')
    content.grid_rowconfigure(0, weight=1)
    content.grid_columnconfigure(0, weight=1)
    app.pages, app.navigation, app.page_canvases = {}, {}, {}
    app.setting_controls = []

    def select_page(name):
        for key, frame in app.pages.items():
            if key == name:
                frame.grid()
            else:
                frame.grid_remove()
        app.active_page = name
        for key, button in app.navigation.items():
            button.configure(style='Selected.Nav.TButton' if key == name else 'Nav.TButton')

    app.select_page = select_page

    def page(name, nav_label, title, description):
        outer = tk.Frame(content, background=c['background'])
        outer.grid(row=0, column=0, sticky='nsew')
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)
        canvas = tk.Canvas(outer, background=c['background'], highlightthickness=0,
                           width=600, height=450, takefocus=False)
        scroll = ttk.Scrollbar(outer, command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.grid(row=0, column=0, sticky='nsew')
        scroll.grid(row=0, column=1, sticky='ns')
        inner = tk.Frame(canvas, background=c['background'])
        item = canvas.create_window(0, 0, window=inner, anchor='nw')
        inner.bind('<Configure>', lambda _: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda event: canvas.itemconfigure(item, width=event.width))
        body = tk.Frame(inner, background=c['background'])
        body.pack(fill='x', padx=28, pady=26)
        tk.Label(body, text=title, font=('Segoe UI Semibold', 23), background=c['background'],
                 foreground=c['ink'], anchor='w').pack(fill='x')
        subtitle = tk.Label(body, text=description, font=('Segoe UI', 10), justify='left',
                            background=c['background'], foreground=c['muted'], anchor='w')
        subtitle.pack(fill='x', pady=(6, 22))
        subtitle.bind('<Configure>', lambda event: subtitle.configure(wraplength=max(100, event.width)))
        app.pages[name], app.page_canvases[name] = outer, canvas
        button = ttk.Button(sidebar, text=nav_label, style='Nav.TButton', command=lambda: select_page(name))
        button.grid(row=len(app.navigation) + 1, column=0, sticky='ew', padx=10, pady=3)
        app.navigation[name] = button
        return body

    def wheel(event):
        canvas = app.page_canvases.get(app.active_page)
        if canvas and not isinstance(event.widget, (ttk.Combobox, ttk.Entry, tk.Text)):
            canvas.yview_scroll(-1 if event.delta > 0 or event.num == 4 else 1, 'units')
    root.bind('<MouseWheel>', wheel, add='+')
    root.bind('<Button-4>', wheel, add='+')
    root.bind('<Button-5>', wheel, add='+')

    def card(parent, title=None):
        edge = tk.Frame(parent, background=c['line'], padx=1, pady=1)
        edge.pack(fill='x', pady=(0, 16))
        inner = ttk.Frame(edge, padding=20)
        inner.pack(fill='both', expand=True)
        if title:
            ttk.Label(inner, text=title, font=('Segoe UI Semibold', 12)).pack(anchor='w', pady=(0, 12))
        return inner

    def note(parent, text, **options):
        label = ttk.Label(parent, text=text, style='Muted.TLabel', justify='left', **options)
        label.pack(fill='x', pady=(3, 8))
        label.bind('<Configure>', lambda event: label.configure(wraplength=max(100, event.width)))
        return label

    def check(parent, name, label):
        variable = tk.BooleanVar(value=getattr(app.settings, name))
        app.variables[name] = variable
        control = ttk.Checkbutton(parent, text=label, variable=variable)
        control.pack(anchor='w')
        app.setting_controls.append((control, 'normal'))

    def choice(parent, name, label, values):
        row = ttk.Frame(parent)
        row.pack(fill='x', pady=5)
        ttk.Label(row, text=label).pack(side='left', padx=(0, 10))
        variable = tk.StringVar(value=str(getattr(app.settings, name)))
        app.variables[name] = variable
        combo = ttk.Combobox(row, textvariable=variable, values=values, state='readonly', width=14)
        combo.pack(side='right')
        app.setting_controls.append((combo, 'readonly'))
        return combo

    home = page('overview', '總覽  Overview', '每一句，都順手。',
                'Make every word feel natural.\n速成輸入與廣東話語音，在這裡準備就緒。')
    ready = card(home, '速成輸入 · Quick typing')
    app.typing_status = tk.StringVar(value='正在檢查 · Checking…')
    ttk.Label(ready, textvariable=app.typing_status, foreground=c['accent'],
              font=('Segoe UI Semibold', 14)).pack(anchor='w', pady=(0, 8))
    note(ready, '安裝所需元件、保留現有設定，再自動套用速成方案。\n'
               'Set up typing with your existing preferences and learned words preserved.')
    app.setup_button = ttk.Button(ready, text='設定速成 · Set up typing', style='Primary.TButton',
                                   command=app.setup_typing)
    app.setup_button.pack(anchor='w', pady=(4, 0))
    practice = card(home, '試打一句 · Try it out')
    steps = ttk.Frame(practice)
    steps.pack(fill='x', pady=(0, 12))
    for code, character in [('hi1', '我'), ('zb1', '，'), ('zd1', '。')]:
        key = tk.Frame(steps, background=c['pale'], padx=12, pady=8)
        key.pack(side='left', padx=(0, 10))
        tk.Label(key, text=f'{code}  →  {character}', background=c['pale'], foreground=c['accent'],
                 font=('Consolas', 13)).pack()
    note(practice, 'Win + Space 選小狼毫 → F4 選「港式速成」。\n'
                   'Select Weasel with Win + Space, then choose 港式速成 with F4.')
    app.practice_entry = ttk.Entry(practice, font=('Segoe UI', 14))
    app.practice_entry.pack(fill='x', pady=(4, 0))
    voice_card = card(home, '廣東話語音 · Cantonese voice')
    app.speech_status = tk.StringVar(value='未啟用 · Not enabled')
    ttk.Label(voice_card, textvariable=app.speech_status, font=('Segoe UI Semibold', 12)).pack(anchor='w')
    note(voice_card, '連按兩次 Ctrl 開始／停止。辨識在你的電腦上進行。\n'
                     'Double-tap Ctrl to start or stop. Recognition stays on your computer.')
    ttk.Button(voice_card, text='語音設定 · Voice settings', command=lambda: select_page('voice')).pack(anchor='w')

    typing = page('typing', '輸入  Typing', '輸入設定 · Typing',
                  '調整候選字與選字習慣。\nMake the candidate list work the way you do.')
    appearance = card(typing, '候選字外觀 · Candidate appearance')
    check(appearance, 'horizontal', '橫向排列 · Horizontal candidates')
    choice(appearance, 'page_size', '每頁字數 · Candidates per page', list(range(1, 10)))
    choice(appearance, 'font_size', '字體大小 · Font size', list(range(10, 37)))
    choice(appearance, 'theme', '候選字主題 · Candidate theme', ['light', 'dark'])
    behavior = card(typing, '輸入習慣 · Typing behavior')
    check(behavior, 'learning', '記住選字習慣 · Learn candidate choices')
    check(behavior, 'prediction', '顯示關聯字 · Suggest word continuations')
    check(behavior, 'show_candidates', '輸入時顯示候選字 · Show candidates while typing')
    check(behavior, 'ascii_punctuation', '使用英文標點 · Use English punctuation')
    choice(behavior, 'switch_key', '中英切換鍵 · Language key', ['Shift_L', 'Shift_R', 'Control_L', 'none'])
    note(behavior, '儲存後會自動重新部署。設定只影響港式速成。\n'
                   'Saving automatically deploys your changes. These settings apply to Cantonese Quick.')

    voice = page('voice', '語音  Voice', '講出你想打嘅字。',
                 'Cantonese dictation, on your computer.\n純 CPU 運行，下載模型後可離線使用。')
    speech = card(voice, '啟用廣東話語音 · Enable Cantonese voice')
    ttk.Label(speech, textvariable=app.speech_status, foreground=c['accent'],
              font=('Segoe UI Semibold', 14)).pack(anchor='w', pady=(0, 8))
    note(speech, '首次啟用會下載約 302 MB；之後無需上傳錄音。\n'
                 'First use downloads about 302 MB. Audio is processed locally.')
    app.enable_button = ttk.Button(speech, text='啟用語音 · Enable voice', style='Primary.TButton', command=app.enable)
    app.enable_button.pack(anchor='w', pady=5)
    recording = card(voice, '收音與快捷鍵 · Microphone and shortcut')
    app.microphone_value = app.settings.dictation_microphone
    app.microphone = tk.StringVar()
    ttk.Label(recording, text='麥克風 · Microphone').pack(anchor='w', pady=(0, 6))
    app.microphone_combo = ttk.Combobox(recording, textvariable=app.microphone, state='readonly')
    app.microphone_combo.pack(fill='x', pady=(0, 8))
    app.microphone_combo.bind('<<ComboboxSelected>>', app.select_microphone)
    app.setting_controls.append((app.microphone_combo, 'readonly'))
    ttk.Button(recording, text='重新整理 · Refresh microphones', command=app.refresh_microphones).pack(anchor='w', pady=(0, 10))
    choice(recording, 'dictation_key', '連按兩次 · Double-tap key', ['Control_L', 'Control_R'])
    check(recording, 'dictation_punctuation', '自動加入標點 · Add punctuation automatically')
    note(recording, 'Ctrl × 2 開始／停止，Esc 取消。\n'
                    'Double Ctrl starts/stops; Esc cancels.\n\n'
                    '若左 Ctrl 用於中英切換，語音會改用右 Ctrl。\n'
                    'When Left Ctrl switches language, voice uses Right Ctrl.\n\n'
                    '使用語音時請保持粵鍵開啟；可縮小視窗。\n'
                    'Keep YueKey running for dictation; minimizing is fine.')

    advanced = page('advanced', '進階  Advanced', '資料與支援 · Data & support',
                    '管理本機資料與安裝狀態。\nYour preferences, backups and support options.')
    storage = card(advanced, '輸入資料夾 · Typing folder')
    app.folder = tk.StringVar()
    ttk.Entry(storage, textvariable=app.folder, state='readonly').pack(fill='x', pady=(0, 8))
    note(storage, '自動使用小狼毫設定的資料夾，包括自訂位置。\n'
                  'YueKey uses the folder configured in Weasel, including custom locations.')
    ttk.Button(storage, text='開啟資料夾 · Open folder', command=app.open_folder).pack(anchor='w')
    recovery = card(advanced, '學習與移除 · Learning and removal')
    note(recovery, '重設學習前，請先從系統匣退出小狼毫。原有資料會先備份。\n'
                   'Exit Weasel from its tray menu before resetting learning. Existing data is backed up.')
    ttk.Button(recovery, text='備份並重設學習 · Back up / Reset learning', command=app.reset_learning).pack(anchor='w', pady=(0, 12))
    note(recovery, '移除粵鍵速成方案會保留學習資料及小狼毫。\n'
                   'Removing YueKey typing keeps learned words and the Weasel engine.')
    ttk.Button(recovery, text='移除速成方案 · Remove YueKey typing', command=app.remove_typing).pack(anchor='w')
    about = card(advanced, f'粵鍵 YueKey  {__version__}')
    note(about, '速成 · 標點 · 廣東話語音\nQuick typing · Punctuation · Cantonese voice\n\n'
                '原創程式採 MIT 授權；小狼毫與其他元件保留各自授權。\n'
                'Original code: MIT. Weasel and other components retain their own licenses.')
    ttk.Button(about, text='安裝指南 · Installation guide', command=app.open_guide).pack(anchor='w')

    tk.Label(sidebar, text='本機辨識 · Local processing\nCPU only', justify='left', anchor='w',
             background=c['sidebar'], foreground=c['sidebar_text'], font=('Segoe UI', 9)).grid(
                 row=7, column=0, sticky='ew', padx=24, pady=(10, 8))
    tk.Label(sidebar, text=f'YueKey {__version__}', background=c['sidebar'], foreground='#90ADB7',
             font=('Segoe UI', 9), anchor='w').grid(row=8, column=0, sticky='ew', padx=24, pady=(0, 24))
    footer = ttk.Frame(root, padding=(28, 14))
    footer.grid(row=1, column=1, sticky='ew')
    footer.grid_columnconfigure(0, weight=1)
    app.apply_button = ttk.Button(footer, text='儲存並套用 · Save changes', style='Primary.TButton', command=app.apply)
    app.apply_button.grid(row=0, column=1, rowspan=2, padx=(20, 0))
    message = ttk.Label(footer, textvariable=app.status, style='Muted.TLabel', justify='left')
    message.grid(row=0, column=0, sticky='ew')
    message.bind('<Configure>', lambda event: message.configure(wraplength=max(100, event.width)))
    app.progress = ttk.Progressbar(footer, mode='indeterminate', length=120)
    app.progress.grid(row=1, column=0, sticky='ew', pady=(7, 0))
    app.progress.grid_remove()
    select_page('overview')
