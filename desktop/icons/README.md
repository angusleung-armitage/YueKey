# YueKey app icon · 粵鍵圖示

The icon uses the Traditional Chinese character **粵** (U+7CB5) on a jade
speech-key tile. Keep the character in its Traditional form.

圖示採用繁體字 **「粵」** 配翡翠綠鍵帽及對話框造型。

- Master artwork: [yuekey-icon.png](../../docs/images/yuekey-icon.png).
- Windows executable/installer: `yuekey.ico` (16–256 px).
- Window icon: `yuekey.png` (256 px).
- Windows sidebar and GTK settings: `yuekey-64.png`.
- Linux desktop icons: `hicolor/` (16–512 px).

The master was generated with the built-in image generation tool. The exports
only resize and encode that artwork. To regenerate them with Pillow installed:

```bash
python3 tools/export_icon.py
```

See the [artwork notes and prompts](../../docs/images/README.md#app-icon).
