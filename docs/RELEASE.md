粵鍵 YueKey 0.6.2：港式速成成為 Ubuntu、Kubuntu 及 Windows 的預設及唯一可選 Rime 方案，毋須按 F4 選擇。保留原有學習資料，並統一 Windows 與 Linux 的主題及按鍵選項名稱。

YueKey 0.6.2 makes Cantonese Quick the default and only selectable Rime scheme on Ubuntu, Kubuntu and Windows. No F4 selection is needed. Existing learned words are preserved. All 13 preferences now share bilingual labels, choices and numeric ranges; Linux also gains microphone refresh. See the [menu audit](https://github.com/angusleung-armitage/YueKey/blob/v0.6.2/docs/platform-parity.md).

- **Windows 顯示修正 / Display fixes:** 關聯字會在文字欄預覽，按數字／空白鍵確認，Esc 或新碼取消。橫／直排設定會同時更新小狼毫的兩個排列設定。Windows now previews continuations inline and applies both candidate-layout settings together. Confirm with a number/Space or dismiss with Esc/new input.

- **Windows:** choose the `windows-x64`, `windows-x86` or `windows-arm64` setup EXE. Approve the administrator prompt if Weasel is missing; compatible existing engines are reused. Setup preserves preferences and learning, then deploys Cantonese Quick automatically. Portable ZIPs include the same prerequisite through **Overview → Set up typing**.
- **新介面 / New interface:** Overview with readiness and a practice field; dedicated Typing, Voice and Advanced pages; branded icon; background setup and automatic deployment when saving settings.
- **廣東話語音 / Cantonese dictation:** CPU runtime included. First enable downloads about 302 MB of verified models. Double-tap Ctrl to start/stop; recognition runs locally without a GPU.
- **Ubuntu / Kubuntu 26.04:** choose `yuekey_0.6.2-1_amd64.deb` or `yuekey_0.6.2-1_arm64.deb`. Install with `sudo apt install ./yuekey_0.6.2-1_$(dpkg --print-architecture).deb`, then run `quick-hk setup` and `quick-hk configure`. The all-in-one DEB includes speech models; APT resolves system dependencies.
- **Limits:** no Linux i386/ARM32 packages or universal DEB for older distributions. Windows x86 is tested under WOW64, not a complete 32-bit OS. Hardware microphones and individual applications still need hands-on checks. Windows packages are not code-signed.
- **授權 / License:** original YueKey code and artwork are MIT. Unmodified Weasel is GPL-3.0; other dictionaries, models and runtimes retain their licenses. [Weasel binary and corresponding upstream source](https://github.com/angusleung-armitage/YueKey/blob/v0.6.2/docs/WEASEL.md). Dictionary source and checksums accompany this release.

[Linux 中英指南 / Guide](https://github.com/angusleung-armitage/YueKey/blob/v0.6.2/docs/INSTALL.md) · [Windows guide](https://github.com/angusleung-armitage/YueKey/blob/v0.6.2/docs/WINDOWS.md) · [Architecture/test coverage](https://github.com/angusleung-armitage/YueKey/blob/v0.6.2/docs/ARCHITECTURES.md)
