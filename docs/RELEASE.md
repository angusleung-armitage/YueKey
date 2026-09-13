粵鍵 YueKey 0.3.0：新增 Windows 安裝程式，修正設定及語音停止問題，專案正式改名為 YueKey。

YueKey 0.3.0 adds a Windows setup installer, fixes configuration and microphone shutdown errors, and moves the repository to `angusleung-armitage/YueKey`.

- **Windows 安裝 · Setup:** download `YueKey-0.3.0-windows-x64-setup.exe`, run it, then open YueKey from the Start Menu. Install official Weasel 0.17.4 separately for typing. [中英安裝指南 · Bilingual guide](https://github.com/angusleung-armitage/YueKey/blob/v0.3.0/docs/WINDOWS.md).
- **Windows 免安裝 · Portable:** `YueKey-0.3.0-windows-x64.zip` contains the same program and CPU runtime.
- **Ubuntu GNOME:** download the `core`, `predict`, and `gnome` `.deb` files; add `dictation` for speech. [安裝指令 · Install commands](https://github.com/angusleung-armitage/YueKey/blob/v0.3.0/docs/INSTALL.md).
- **Kubuntu KDE:** use `core`, `predict`, and `kde`; dictation is currently unavailable on KDE.
- **修正 · Fixes:** Windows setup rejects duplicate/ambiguous YAML before writing. Removal checks backups and the complete manifest before deleting files. Microphone shutdown failures release capture/decoding without leaving dictation stuck.
- **資料保留 · Preservation:** setup updates the companion; app removal retains Rime configuration, learning, backups and downloaded models. There is no typing-data change requiring redeployment for this release.
- **原始碼 · Source:** `YueKey-0.3.0-source.tar.gz` includes build scripts and checksum-pinned dictionary inputs. `SHA256SUMS` covers every package and source archive.

原創程式採 MIT 授權。字典、第三方程式及模型保留原有授權，詳見 `THIRD_PARTY.md` 及各下載內的授權檔案。所有下載免費。

Original code is MIT-licensed. Dictionaries, third-party code and models retain their original licenses; see `THIRD_PARTY.md` and the included license files. All downloads are free.

Windows 版暫未包含 Ubuntu 的原生關聯字插件，未有程式碼簽署憑證。Windows 11 真實麥克風及個別應用程式仍需使用者測試；語音辨識可能出錯。

The Windows build does not yet include Ubuntu's native continuation-prediction plugin and is not code-signed. Real Windows 11 microphone and individual application compatibility need user testing. Speech recognition can make mistakes.
