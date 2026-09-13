粵鍵 YueKey 0.6.4 修正關聯字顯示：輸入「你」後，文字欄只顯示「你」，「講」、「好」等建議只留在關聯字清單。按數字鍵或空白鍵確認後才加入文字欄。

YueKey 0.6.4 keeps word continuations in the candidate list until you select one. After committing 你, the field remains 你; it becomes 你講 only after selecting 講. Browsing suggestions does not change the text field.

- **三個平台 / All desktops:** Ubuntu GNOME, Kubuntu and Windows use list-only continuations. Number keys or Space accept a suggestion; Esc or new Quick input dismisses it.
- **Ubuntu GNOME:** 字根及待確認文字改在候選框顯示，文字欄只顯示已確認文字。Radicals and pending composition appear in the candidate panel, keeping only confirmed text in the field.
- **驗證 / Validation:** installed IBus, Fcitx5 and Weasel checks verify unchanged text while suggestions are shown and highlighted, explicit acceptance and cancellation. Horizontal/vertical layouts, shared settings and CPU Cantonese recognition remain covered by CI.
- **語音 SSL / Voice HTTPS:** retains 0.6.3's native Windows certificate validation and checksum-verified model downloads.

- **Windows:** choose the `windows-x64`, `windows-x86` or `windows-arm64` setup EXE. Approve the administrator prompt if Weasel is missing; compatible existing engines are reused. Setup preserves preferences and learning, then deploys Cantonese Quick automatically. Portable ZIPs include the same prerequisite through **Overview → Set up typing**.
- **新介面 / New interface:** Overview with readiness and a practice field; dedicated Typing, Voice and Advanced pages; branded icon; background setup and automatic deployment when saving settings.
- **廣東話語音 / Cantonese dictation:** CPU runtime included. First enable downloads about 302 MB of verified models. Double-tap Ctrl to start/stop; recognition runs locally without a GPU.
- **Ubuntu / Kubuntu 26.04:** choose `yuekey_0.6.4-1_amd64.deb` or `yuekey_0.6.4-1_arm64.deb`. Install with `sudo apt install ./yuekey_0.6.4-1_$(dpkg --print-architecture).deb`, then run `quick-hk setup` and `quick-hk configure`. The all-in-one DEB includes speech models; APT resolves system dependencies.
- **Limits:** no Linux i386/ARM32 packages or universal DEB for older distributions. Windows x86 is tested under WOW64, not a complete 32-bit OS. Hardware microphones and individual applications still need hands-on checks. Windows packages are not code-signed.
- **授權 / License:** original YueKey code and artwork are MIT. Unmodified Weasel is GPL-3.0; other dictionaries, models and runtimes retain their licenses. [Weasel binary and corresponding upstream source](https://github.com/angusleung-armitage/YueKey/blob/v0.6.4/docs/WEASEL.md). Dictionary source and checksums accompany this release.

[Linux 中英指南 / Guide](https://github.com/angusleung-armitage/YueKey/blob/v0.6.4/docs/INSTALL.md) · [Windows guide](https://github.com/angusleung-armitage/YueKey/blob/v0.6.4/docs/WINDOWS.md) · [Architecture/test coverage](https://github.com/angusleung-armitage/YueKey/blob/v0.6.4/docs/ARCHITECTURES.md)
