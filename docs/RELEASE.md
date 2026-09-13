粵鍵 YueKey 0.2.0：Ubuntu 26.04 速成輸入與純 CPU 廣東話語音，新增 Windows x64 初期支援。

YueKey 0.2.0 brings Cantonese Quick input and CPU-only dictation to Ubuntu 26.04, with initial Windows x64 support.

- **Windows:** download `YueKey-0.2.0-windows-x64.zip`, extract it, install official Weasel 0.17.4, then open `YueKey.exe`. See `docs/WINDOWS.md` inside the ZIP for bilingual setup.
- **Ubuntu GNOME:** download the `core`, `predict`, and `gnome` `.deb` files; add `dictation` for speech. Use the installation guide in the source archive or repository.
- **Kubuntu KDE:** use `core`, `predict`, and `kde`; dictation is currently unavailable on KDE.
- **原始碼 · Source:** `YueKey-0.2.0-source.tar.gz` includes build scripts and checksum-pinned dictionary inputs.
- **檢查碼 · Integrity:** `SHA256SUMS` covers all attached packages and source.

原創程式採 MIT 授權。字典、第三方程式及模型保留原有授權，詳見 `THIRD_PARTY.md` 及各下載內的授權檔案。所有下載免費。

Original code is MIT-licensed. Dictionaries, third-party code and models retain their original licenses; see `THIRD_PARTY.md` and the included license files. All downloads are free.

Windows 版暫未包含 Ubuntu 的原生關聯字插件，未有程式碼簽署憑證。Windows 11 真實麥克風及個別應用程式仍需使用者測試；語音辨識可能出錯。

The Windows build does not yet include Ubuntu's native continuation-prediction plugin and is not code-signed. Real Windows 11 microphone and individual application compatibility need user testing. Speech recognition can make mistakes.
