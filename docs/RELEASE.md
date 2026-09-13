粵鍵 YueKey 0.6.0：Windows 安裝檔已包含小狼毫，速成自動部署；全新中英介面，輸入及語音設定更清晰。

YueKey 0.6.0 includes the official Weasel engine in Windows setup, configures typing automatically, and introduces a redesigned bilingual desktop interface.

- **Windows:** choose the `windows-x64`, `windows-x86` or `windows-arm64` setup EXE. Approve the administrator prompt if Weasel is missing; compatible existing engines are reused. Setup preserves preferences and learning, then deploys Cantonese Quick automatically. Portable ZIPs include the same prerequisite through **Overview → Set up typing**.
- **新介面 / New interface:** Overview with readiness and a practice field; dedicated Typing, Voice and Advanced pages; branded icon; background setup and automatic deployment when saving settings.
- **廣東話語音 / Cantonese dictation:** CPU runtime included. First enable downloads about 302 MB of verified models. Double-tap Ctrl to start/stop; recognition runs locally without a GPU.
- **Ubuntu / Kubuntu 26.04:** choose `yuekey_0.6.0-1_amd64.deb` or `yuekey_0.6.0-1_arm64.deb`. Install with `sudo apt install ./yuekey_0.6.0-1_$(dpkg --print-architecture).deb`, then run `quick-hk setup` and `quick-hk configure`. The all-in-one DEB includes speech models; APT resolves system dependencies.
- **Limits:** no Linux i386/ARM32 packages or universal DEB for older distributions. Windows x86 is tested under WOW64, not a complete 32-bit OS. Hardware microphones and individual applications still need hands-on checks. Windows packages are not code-signed.
- **授權 / License:** original YueKey code and artwork are MIT. Unmodified Weasel is GPL-3.0; other dictionaries, models and runtimes retain their licenses. [Weasel binary and corresponding upstream source](https://github.com/angusleung-armitage/YueKey/blob/v0.6.0/docs/WEASEL.md). Dictionary source and checksums accompany this release.

[Linux 中英指南 / Guide](https://github.com/angusleung-armitage/YueKey/blob/v0.6.0/docs/INSTALL.md) · [Windows guide](https://github.com/angusleung-armitage/YueKey/blob/v0.6.0/docs/WINDOWS.md) · [Architecture/test coverage](https://github.com/angusleung-armitage/YueKey/blob/v0.6.0/docs/ARCHITECTURES.md)
