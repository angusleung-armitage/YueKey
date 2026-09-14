"""Shared YueKey desktop palette and navigation. SPDX-License-Identifier: MIT."""

COLORS = dict(background='#F3F6F8', surface='#FFFFFF', ink='#142C37', muted='#526773',
              sidebar='#102F37', sidebar_text='#C2D5DC', accent='#007D75',
              accent_hover='#006960', pale='#E6F4F0', line='#DCE5E9')

PAGES = {
    'overview': ('總覽  Overview', '每一句，都順手。',
                 'Make every word feel natural.\n速成輸入與廣東話語音，在這裡準備就緒。'),
    'typing': ('輸入  Typing', '輸入設定 · Typing',
               '調整候選字與選字習慣。\nMake the candidate list work the way you do.'),
    'voice': ('語音  Voice', '講出你想打嘅字。',
              'Cantonese dictation, on your computer.\n純 CPU 運行，模型準備好後可離線使用。'),
    'advanced': ('進階  Advanced', '資料與支援 · Data & support',
                 '管理本機資料與安裝狀態。\nYour preferences, backups and support options.'),
}
