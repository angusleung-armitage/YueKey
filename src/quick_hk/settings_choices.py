"""Shared bilingual menu text for the GTK and Windows settings windows."""

LABELS = {
    "horizontal": "橫排候選字 · Horizontal candidates",
    "page_size": "每頁候選字 · Candidates per page",
    "font_size": "字體大小 · Font size (pt)",
    "theme": "外觀 · Appearance",
    "show_candidates": "輸入時顯示候選字 · Show candidates while typing",
    "learning": "學習選字次序 · Learn candidate choices",
    "prediction": "顯示關聯字 · Suggest word continuations",
    "ascii_punctuation": "半形標點 · ASCII punctuation",
    "switch_key": "中英切換鍵 · Chinese / English key",
    "dictation_enabled": "啟用語音輸入 · Enable dictation",
    "dictation_key": "連按兩次 · Double-tap key",
    "dictation_microphone": "麥克風 · Microphone",
    "dictation_punctuation": "自動標點 · Automatic punctuation",
}

ACTIONS = {
    "apply": "儲存並套用 · Save changes",
    "reset_learning": "備份並重設學習 · Back up / Reset learning",
    "refresh_microphones": "重新整理麥克風 · Refresh microphones",
    "disable_dictation": "停用語音輸入 · Disable dictation",
}

HINTS = {
    "show_candidates": "關閉後，按空白鍵展開候選字。\nWhen off, press Space to open candidates.",
    "prediction": "關聯字會先預覽；按數字或空白鍵確認，Esc 或新碼取消。\n"
                  "Suggestions are previews. Confirm with a number or Space; dismiss with Esc or new input.",
    "dictation_key": "如左 Ctrl 用作中英切換，語音輸入會使用右 Ctrl。\n"
                     "If Left Ctrl switches language, dictation uses Right Ctrl.",
}


def microphone_choices(devices, selected):
    """Keep an unplugged selection visible instead of silently choosing another mic."""
    choices = list(devices)
    if selected not in {value for value, _label in choices}:
        choices.append((selected, '未連接 · Unavailable: ' + selected))
    return choices

CHOICES = {
    "theme": [("light", "淺色 · Light"), ("dark", "深色 · Dark")],
    "switch_key": [
        ("Shift_L", "左 Shift · Left Shift"),
        ("Shift_R", "右 Shift · Right Shift"),
        ("Control_L", "左 Ctrl · Left Ctrl"),
        ("none", "停用 · Disabled"),
    ],
    "dictation_key": [
        ("Control_L", "左 Ctrl · Left Ctrl"),
        ("Control_R", "右 Ctrl · Right Ctrl"),
    ],
}
