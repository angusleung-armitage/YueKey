粵鍵 YueKey 0.6.5 改善輸入狀態及語音提示：Windows 中文模式顯示「港」圖示；雙按 Ctrl 後，小咪高峰會出現在文字游標或輸入欄旁。

YueKey 0.6.5 adds a 港 input-mode icon on Windows and a compact dictation indicator beside the caret or input field.

- **Windows 狀態 / Input mode:** language bar and tray use 港 for Chinese and A for English. The application logo remains 粵. Existing preferences and user learning are retained.
- **標點補齊 / Punctuation:** restores all 75 traditional Z-code symbols from the previous 38-symbol subset, including `zf → ‧`, `zk → ︰`, `zt → ﹖`, `zu → ﹗`, and vertical forms. Default candidates follow full-code order; personal learning can change ranking. See the [symbol reference](https://github.com/angusleung200/YueKey/blob/v0.6.5/docs/PUNCTUATION.md).
- **語音提示 / Dictation indicator:** compact microphone and level display on GNOME, KDE and Windows. Windows uses a non-activating, click-through badge; KDE uses its native input panel. GNOME uses candidate-panel coordinates and accessibility field geometry. If the app reports no geometry, GNOME/Windows use the active window edge.
- **Ubuntu 更新 / GNOME upgrade:** a previously loaded extension keeps its old JavaScript until the next login. Installing does not restart the desktop or sign you out.
- **關聯字 / Continuations:** retains 0.6.4's list-only suggestions: 你 stays 你 until you explicitly select 講. Browsing does not insert the suggestion.
- **語音 SSL / Voice HTTPS:** retains native Windows certificate validation and checksum-verified model downloads.
- **Windows 設定 / Settings:** rapid saves now invalidate Rime's whole-second configuration cache, so layout and page-size changes are applied reliably.
- **下載重試 / Downloads:** temporarily rate-limited model downloads retry with bounded delays and retain checksum and certificate validation.

- **Windows:** choose the `windows-x64`, `windows-x86` or `windows-arm64` setup EXE. Approve the administrator prompt if Weasel is missing; compatible existing engines are reused. Setup preserves preferences and learning, then deploys Cantonese Quick automatically. Portable ZIPs include the same prerequisite through **Overview → Set up typing**.
- **新介面 / New interface:** Overview with readiness and a practice field; dedicated Typing, Voice and Advanced pages; branded icon; background setup and automatic deployment when saving settings.
- **廣東話語音 / Cantonese dictation:** CPU runtime included. First enable downloads about 302 MB of verified models. Double-tap Ctrl to start/stop; recognition runs locally without a GPU.
- **Ubuntu / Kubuntu 26.04:** choose `yuekey_0.6.5-1_amd64.deb` or `yuekey_0.6.5-1_arm64.deb`. Install with `sudo apt install ./yuekey_0.6.5-1_$(dpkg --print-architecture).deb`, then run `quick-hk setup` and `quick-hk configure`. The all-in-one DEB includes speech models; APT resolves system dependencies.
- **Limits:** no Linux i386/ARM32 packages or universal DEB for older distributions. Windows x86 is tested under WOW64, not a complete 32-bit OS. Hardware microphones and individual applications still need hands-on checks. Windows packages are not code-signed.
- **授權 / License:** original YueKey code and artwork are MIT. Unmodified Weasel is GPL-3.0; other dictionaries, models and runtimes retain their licenses. [Weasel binary and corresponding upstream source](https://github.com/angusleung-armitage/YueKey/blob/v0.6.5/docs/WEASEL.md). Dictionary source and checksums accompany this release.

[Linux 中英指南 / Guide](https://github.com/angusleung-armitage/YueKey/blob/v0.6.5/docs/INSTALL.md) · [Windows guide](https://github.com/angusleung-armitage/YueKey/blob/v0.6.5/docs/WINDOWS.md) · [Architecture/test coverage](https://github.com/angusleung-armitage/YueKey/blob/v0.6.5/docs/ARCHITECTURES.md)
