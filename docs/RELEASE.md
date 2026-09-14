粵鍵 YueKey 0.6.8 調整 Ubuntu GNOME 與 Windows 的語音提示比例：綠色膠囊改為 64 × 24，左邊是白色咪高峰，右邊是「粵」。提示置於游標下方；接近畫面底部時移到上方，並隨顯示比例縮放。

YueKey 0.6.8 reshapes the Ubuntu GNOME and Windows dictation indicator into a 64 × 24 green capsule: an outlined microphone, a subtle divider and 粵. It sits below the caret, moves above near the screen edge, and scales with the display.

- **Ubuntu GNOME 升級 / Upgrade:** GNOME caches extension JavaScript for the current login. If the previous microphone display remains, install the update and sign out and back in when convenient. `quick-hk dictation status --json` reports the loaded and installed extension versions. Restarting IBus or toggling the extension does not load updated JavaScript. Your current session is never ended automatically.
- **Windows:** close YueKey, run the new setup EXE and reopen YueKey. The capsule remains nonactivating and click-through, so dictation keeps focus in the text field.
- **Kubuntu:** continues to use Fcitx5’s native status panel beside the input field; this release changes the GNOME and Windows capsule artwork.
- **驗證 / Validation:** a separate GNOME 50.1 Wayland desktop verified the visible 64 × 24 capsule, double Ctrl, CPU recognition and insertion of a public Cantonese audio fixture, focus-change cancellation, Escape and password exclusion. Geometry checks cover monitor edges, negative coordinates and 200% scaling. Windows installer CI checks the actual capsule size and focus preservation on x64, x86 and ARM64. No hardware microphone is opened by these checks.
- **Ubuntu / Kubuntu 26.04:** choose `yuekey_0.6.8-1_amd64.deb` or `yuekey_0.6.8-1_arm64.deb`. Install with `sudo apt install ./yuekey_0.6.8-1_$(dpkg --print-architecture).deb`. The all-in-one DEB includes CPU speech models; APT resolves system dependencies. Settings and learned words are preserved.
- **Windows downloads:** choose the `windows-x64`, `windows-x86` or `windows-arm64` setup EXE. Weasel is included; voice models download on first enable. Portable ZIPs are also available.
- **Limits:** no Linux i386/ARM32 packages or universal DEB for older distributions. Windows x86 is tested under WOW64. Hardware microphones and individual applications still need hands-on checks; Windows packages are not code-signed.
- **授權 / License:** original YueKey code and artwork are MIT. Weasel is GPL-3.0; dictionaries, models and runtimes retain their licenses. [Weasel binary and corresponding upstream source](https://github.com/angusleung200/YueKey/blob/v0.6.8/docs/WEASEL.md).

[Linux 中英指南 / Guide](https://github.com/angusleung200/YueKey/blob/v0.6.8/docs/INSTALL.md) · [Windows guide](https://github.com/angusleung200/YueKey/blob/v0.6.8/docs/WINDOWS.md) · [標點對照 / Symbols](https://github.com/angusleung200/YueKey/blob/v0.6.8/docs/PUNCTUATION.md)
