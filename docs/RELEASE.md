粵鍵 YueKey 0.4.1：Kubuntu 加入廣東話語音；Windows 加入關聯字、完整設定及 WASAPI 麥克風取樣率轉換。

YueKey 0.4.1 includes Kubuntu Cantonese dictation, Windows word continuations and complete settings. This follow-up enables shared-mode WASAPI sample-rate conversion for microphones configured at 44.1/48 kHz.

- **Kubuntu 26.04 amd64:** install the `core`, `predict`, `kde` and optional `dictation` DEBs. Fcitx5 handles double Ctrl, the recording indicator and direct insertion into the original field. [中英指南 · Guide](https://github.com/angusleung-armitage/YueKey/blob/v0.4.1/docs/INSTALL.md#kde).
- **Windows 11 x64:** run `YueKey-0.4.1-windows-x64-setup.exe`; Weasel 0.17.4 is installed separately. A portable ZIP is also available. [中英指南 · Guide](https://github.com/angusleung-armitage/YueKey/blob/v0.4.1/docs/WINDOWS.md).
- **Windows 設定 · Settings:** candidate orientation, page/font size, light/dark themes, learning, continuations, candidate visibility, punctuation, language switching, microphone selection and speech preferences persist across launches. Learning reset backs up the database and refuses while it is locked. Optional login startup is available in the installer.
- **Windows 升級 · Upgrade:** close YueKey and install the new EXE, then click **Install / Update typing** and redeploy Weasel. This installs the new continuation data while keeping original backups and learned words. Externally edited managed files stop the update before writing.
- **Ubuntu GNOME:** use `core`, `predict`, `gnome` and optional `dictation`. Existing features remain available. Install matching 0.4.1 packages together.
- **純 CPU · CPU only:** all platforms use SenseVoice Small Yue INT8, local punctuation and HK Traditional output. First use downloads approximately 302 MB of verified models. No GPU or speech cloud account is required.
- **下載 · Downloads:** five DEBs, Windows setup EXE, portable ZIP, corresponding source archive and `SHA256SUMS` are built by GitHub Actions. The KDE package is now `amd64` because it includes the native Fcitx5 bridge.

原創程式採 MIT 授權，所有下載免費。字典、第三方程式及模型保留原有授權，詳見 `THIRD_PARTY.md`。

Original code is MIT-licensed and downloads are free. Dictionaries, third-party code and models retain their original licenses; see `THIRD_PARTY.md`.

Windows 安裝檔未有程式碼簽署。自動測試涵蓋實際 Rime／Fcitx5 引擎、Windows 安裝及 CPU 模型；真實麥克風與個別應用程式仍需按相容性紀錄驗證。密碼及無法安全識別的欄位不會接受語音。

The Windows installer is unsigned. Automated checks cover actual Rime/Fcitx5 engines, Windows installation and CPU models; real microphones and individual applications need the checks listed in the compatibility record. Password and unsupported fields are excluded from dictation.
