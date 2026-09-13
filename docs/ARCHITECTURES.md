# 架構與支援範圍 · Architectures and support

一個 DEB 可包含全部 YueKey 功能，但含原生程式的 DEB 不能同時作為 x86、x64 及 ARM 安裝檔。每個 CPU 架構都須獨立建置、安裝及測試。

An all-in-one DEB contains every YueKey component, but native binaries require a separate package for each CPU architecture. Each target is built, installed and tested separately.

| Target | Installer | Automated validation |
| --- | --- | --- |
| Ubuntu 26.04 amd64, GNOME 50 / KDE | `yuekey_*_amd64.deb` | Native x64 Linux runner, Ubuntu container, IBus/Fcitx5 input, package migration, frozen CPU speech |
| Ubuntu 26.04 arm64, GNOME 50 / KDE | `yuekey_*_arm64.deb` | Native ARM64 Linux runner, same container/runtime/input checks |
| Windows x64 | `YueKey-*-windows-x64-setup.exe` / ZIP | Windows Server 2025 x64 runner, x64 companion and Weasel runtime |
| Windows x86 / 32-bit | `YueKey-*-windows-x86-setup.exe` / ZIP | 32-bit Python and executable on the x64 Windows runner; 28-byte Win32 INPUT, x86 Weasel runtime |
| Windows 11 ARM64 | `YueKey-*-windows-arm64-setup.exe` / ZIP | Native Windows 11 ARM runner and companion; official Weasel's x64 Rime server through Windows emulation |

Windows checks cover fresh installation of the bundled Weasel engine, automatic profile deployment, engine reuse on repair, four-page UI navigation at two window sizes, installer removal, real Unicode insertion into an isolated text field, password/focus guards, settings, learning locks and public Cantonese audio. They never record a microphone. The x86 executable is tested on 64-bit Windows through WOW64; a complete 32-bit Windows 10 installation has not been tested. Linux tests exercise both input frameworks, but do not replace hands-on GNOME/KDE Wayland and microphone testing on each device.

Windows 測試包括內置小狼毫引擎全新安裝、自動部署、修復時沿用引擎、四頁介面於兩種視窗大小的導覽、移除、真實文字欄輸入、密碼及焦點保護、設定、學習資料鎖定及公開廣東話錄音。測試不會收音。x86 程式在 64-bit Windows 的 WOW64 驗證，尚未於完整 32-bit Windows 10 實機驗證。Linux 兩種輸入框架均有測試；完整 Wayland 桌面及不同硬件麥克風仍需實機驗證。

## 選擇下載檔案 · Choose a download

- Linux: `dpkg --print-architecture` returns `amd64` or `arm64` for these packages.
- Windows: **Settings → System → About → System type**. Use x64 for Intel/AMD 64-bit, x86 for 32-bit, or ARM64 for ARM-based PCs.
- `x32` here means **32-bit x86**, not Linux's separate x32 ABI.
- ARM means **ARM64 / AArch64** in this release. ARM32 / armhf is not packaged.

## DEB 內有甚麼？ · What is all-in-one?

The single DEB includes the scheme/dictionary/predictions, settings app, GNOME extensions, KDE addon/themes, Rime speech bridge, a frozen Python CPU recognizer, and checksum-verified SenseVoice Small Yue INT8, Silero VAD and CT-Transformer INT8 models. No uv, pip or model download is needed during Linux speech setup. Dictation remains opt-in.

單一 DEB 已包括速成字典／關聯字、設定介面、GNOME／KDE 整合、語音橋接、獨立 CPU 執行環境及已驗證模型。Linux 語音設定毋須 uv、pip 或下載模型；語音預設關閉。

APT still resolves system libraries, fonts, IBus and Fcitx5 from Ubuntu. The package does not install the GNOME or KDE desktop shell. Existing desktop selection is not changed. This is an all-in-one **YueKey** package, not an offline copy of Ubuntu's dependency repositories. Its native Rime/Fcitx ABI dependencies target Ubuntu 26.04 specifically.

APT 仍會由 Ubuntu 安裝所需系統函式庫、字型、IBus 及 Fcitx5；不會安裝 GNOME／KDE 桌面或更改預設輸入框架。這是 YueKey 全合一套件，不是整個 Ubuntu 軟件庫的離線副本。原生 Rime／Fcitx 依賴針對 Ubuntu 26.04。

## 不能承諾的版本 · Unavailable targets

Ubuntu 26.04 has no i386 kernel, installer or bootloader. Its i386 packages supplement amd64 systems; they do not form a 32-bit desktop OS. The pinned sherpa-onnx Python runtime also has no Linux i686 wheel. Therefore no full-feature Linux x86 DEB is published. ARM32 additionally needs a separately validated NumPy/runtime build and desktop image. Renaming an amd64 package or marking its native payload `Architecture: all` would not make either target work.

Ubuntu 26.04 沒有 i386 核心或桌面安裝程式；i386 套件只補充 amd64 系統。本工具鎖定的 sherpa-onnx Python 執行環境亦沒有 Linux i686 wheel，因此不發佈聲稱支援全部功能的 Linux x86 DEB。ARM32 另需驗證 NumPy／語音執行環境及桌面系統。不能只改檔名或標示 `Architecture: all` 當作支援。

Older Ubuntu/Debian releases need their own native builds and desktop integration validation. These 26.04 DEBs are not advertised for them. Windows x64/x86 installers accept Windows 10 2004 and newer; ARM64 requires Windows 11, matching the official Weasel server's emulation path.

Official references, checked 2026-09-13: [Ubuntu architectures](https://ubuntu.com/project/docs/how-ubuntu-is-made/concepts/supported-architectures/), [sherpa-onnx 1.13.8 wheel inventory](https://pypi.org/project/sherpa-onnx/1.13.8/#files), [official Weasel 0.17.4 installer architecture selection](https://github.com/rime/weasel/blob/0.17.4/output/install.nsi), [GitHub runner architectures](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
