# YueKey README artwork

Generated with Codex's built-in image-generation tool on 2026-09-13. These are product illustrations, not application screenshots. They are original YueKey project artwork covered by the root license. English and Traditional Chinese labels were visually checked; usage examples match the fresh-profile input tests.

- `yuekey-hero.png`: ivory/teal brand banner with Cantonese keycaps and voice motif.
- `yuekey-quick-reference.png`: typing, punctuation and double-Ctrl instruction card.

The README retains the same instructions in selectable text and gives both images descriptive alt text. Candidate learning can change the `hi1` ranking.

## Generation prompts

### hero

Create a polished open-source software README hero banner, very wide landscape 2.5:1 composition, for YueKey. Editorial product illustration, warm ivory background, deep dark teal and vivid jade green with tiny vermilion accent, soft 3D tactile keyboard keycaps and elegant sound waveform. Left 45 percent: exact large typography '粵鍵 YueKey' with exact subtitle 'Cantonese, at your fingertips.' and small exact Chinese subtitle '打字・講嘢・隨你'. Right: an original sculptural keycap with Chinese character '粵', a microphone symbol embedded in flowing green waveform, smaller keycaps with 'Ctrl' and punctuation '，'. Bottom small exact text 'QUICK INPUT + OFFLINE VOICE'. Spacious sophisticated composition, crisp readable authentic Traditional Chinese typography, no screenshot, no fake UI, no platform logos, no third party brands, no claims of popularity, no third-party operating-system brands, no watermark. Designed to be attractive at GitHub README width and dark/light backgrounds. Output one high quality raster image.

### quick_reference

Create a clear software README quick-reference illustration for YueKey, wide 2.3:1 landscape, cream background, deep teal type, jade green accents, subtle tactile keycaps, large readable text, generous whitespace. Exact title '粵鍵 YueKey' with exact subtitle 'Quick reference · 快速上手'. Below are three equal numbered cards separated by thin vertical rules, perfectly aligned. CARD 1: exact heading '01  速成 · Type', show three separate keycaps 'h' 'i' '1', arrow to a large Traditional Chinese character '我'. CARD 2: exact heading '02  標點 · Punctuation', show three keycaps 'z' 'b' '1', arrow to a large Chinese comma '，'. CARD 3: exact heading '03  語音 · Dictate', show exact text 'Ctrl × 2' then a microphone and waveform, then exact text 'Ctrl × 2' and a checkmark. At very bottom exact small caption 'Enable dictation in Settings first · 先在設定啟用語音'. Clean accessible typographic instructional card, authentic Traditional Chinese, no extra text, no screen mockup, no platform logos, no claims, no third party brands, no third-party operating-system brands, no watermark. Illustration should complement a refined ivory and teal Hong Kong Cantonese keyboard product brand. Exact sequences hi1 = 我 and zb1 = ， must not be altered.

## Windows interface capture

`windows-overview.png` is an unedited capture of the installed YueKey application
on the Windows 11 ARM64 disposable GitHub runner, from commit `477d139` in
[run 34751815886](https://github.com/angusleung-armitage/YueKey/actions/runs/34751815886).
It shows the actual bilingual interface after bundled engine installation and
profile deployment. It is not a generated product mockup. The original app artwork
and UI are MIT-licensed; the title bar is rendered by Windows.


<a id="app-icon"></a>
## App icon · 粵鍵圖示

`yuekey-icon.png` is the final generated master, using Traditional Chinese
**粵** (U+7CB5), an ivory glyph, a jade speech-key silhouette and an opaque deep
teal tile. Generated with the **built-in image_gen tool**, then exported without
artwork changes to PNG and ICO sizes by `tools/export_icon.py`. The original
Y draft and simplified-character drafts are not used in the app.

A typeset Noto Sans CJK HK Bold rendering of 粵 was used as a glyph reference to
keep the Traditional form accurate. Font files are not bundled with the icon.
The generated project artwork is distributed under this project's MIT license.

### Final prompt set

The existing jade key design was used as the first visual reference; the exact
Traditional glyph was supplied as the second reference.

```text
Edit image 1, the jade YueKey icon. Image 2 is the exact required glyph reference, NOT a second icon or a background: it shows Traditional Chinese 粵 (U+7CB5). Replace the Y in image 1 with an ivory-white rendering of the EXACT outline and strokes of the glyph in image 2, preserving all details of that glyph. In particular preserve the sloping top stroke inside the upper enclosure, the OPEN bottom corners of that enclosure and separate short bottom horizontal stroke; do NOT turn it into the simplified closed-box 米 character 粤. Reproduce the reference glyph faithfully, only scaling and recoloring it, centered at roughly 65 percent of the key size, with clear spacing between strokes. Preserve the rounded jade speech-key shape, colors, depth and balanced composition of image 1. Output ONE square production PNG icon. The background outside the icon must be an actual transparent alpha channel like image 1. Do not draw checkerboard squares, a grid, gray, black or white background. No Y or other letters, no watermark, no mockup, no extra objects.
```

The final background refinement uses an opaque tile:

```text
Edit this final 粵 icon. Keep the exact Traditional Chinese glyph 粵, every stroke, its ivory color, size and position unchanged. Keep the jade key and speech-bubble outline unchanged. Replace ALL of the gray checkerboard exterior with a completely smooth solid deep ink-teal color #102F37, extending to all four edges of the square canvas. This is intentionally an OPAQUE full-bleed square app tile, NOT a transparent image. No checkerboard, no grid, no white margin, no transparency simulation, no extra text or objects. The result must be the same jade key bearing the exact 粵 glyph on an entirely solid deep-teal square background. Output one polished PNG app icon.
```


## Windows 0.6.1 icon capture

`windows-overview-v0.6.1.png` is the unedited installed application captured on the
Windows Server 2025 x64 disposable runner at `69ef2b4` in
[release run 34753111328](https://github.com/angusleung-armitage/YueKey/actions/runs/34753111328).
It shows the final Traditional 粵 icon in the sidebar and title bar. The older
`windows-overview.png` remains an archived 0.6.0 capture.


## Windows 0.6.2 settings audit captures

`windows-overview-v0.6.2.png` and `windows-typing-v0.6.2.png` are unedited
captures of the installed application on the disposable Windows Server 2025
x64 runner, commit `6680c60`,
[run 34755990578](https://github.com/angusleung-armitage/YueKey/actions/runs/34755990578).
The Typing capture shows the shared labels and the horizontal-candidates option.
