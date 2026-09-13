粵鍵 YueKey 0.5.0：一個 DEB，速成及離線廣東話語音全部包含；新增 ARM64 及 Windows x86 安裝檔。

YueKey 0.5.0 combines Linux typing, settings, desktop integrations, CPU speech runtime and models into one DEB per architecture. It adds ARM64 Linux builds and native x86/ARM64 Windows companions, plus illustrated bilingual getting-started guides.

- **Ubuntu / Kubuntu 26.04:** choose `yuekey_0.5.0-1_amd64.deb` or `yuekey_0.5.0-1_arm64.deb`. Install with `sudo apt install ./yuekey_0.5.0-1_$(dpkg --print-architecture).deb`. APT resolves system dependencies; speech models are already included. Existing split packages are replaced automatically.
- **Windows:** choose the `windows-x64`, `windows-x86` or `windows-arm64` setup EXE. Portable ZIPs are also available. Install official Weasel 0.17.4 separately. Speech models download on first enable; CPU runtime is included.
- **啟用 / Activate:** Linux: `quick-hk setup`, then `quick-hk configure`. GNOME uses IBus; KDE uses Fcitx5. Enable speech and double-tap Ctrl to start/stop.
- **Limits:** no Linux i386/ARM32 packages and no universal DEB for older Ubuntu/Debian releases. Windows x86 is tested under WOW64, not a complete 32-bit OS. Hardware microphones and individual applications need hands-on checks.
- **授權 / License:** original YueKey code is MIT; third-party dictionaries, models and runtimes retain their licenses. Corresponding dictionary source and checksums accompany this release.

[Linux 中英指南 / Guide](https://github.com/angusleung-armitage/YueKey/blob/v0.5.0/docs/INSTALL.md) · [Windows guide](https://github.com/angusleung-armitage/YueKey/blob/v0.5.0/docs/WINDOWS.md) · [Architecture/test coverage](https://github.com/angusleung-armitage/YueKey/blob/v0.5.0/docs/ARCHITECTURES.md)
