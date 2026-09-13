# Windows typing engine · Windows 輸入法引擎

YueKey's Windows EXE and ZIP include the **unmodified official Weasel 0.17.4
installer** as a separately licensed prerequisite. Weasel provides Windows TSF
input-method registration and the Rime typing engine. YueKey's original code,
interface and artwork remain MIT-licensed; this does not relicense Weasel or its
dependencies.

Windows EXE 及 ZIP 已包含未經修改的官方小狼毫 0.17.4 安裝檔，作為獨立授權
元件。小狼毫提供 Windows 輸入法註冊及 Rime 引擎；粵鍵原創程式、介面及美術
仍採 MIT 授權，不會更改小狼毫及其依賴的授權。

- Binary: [`weasel-0.17.4.0-installer.exe`](https://github.com/rime/weasel/releases/download/0.17.4/weasel-0.17.4.0-installer.exe)
- SHA-256: `cf509534a8f5f8af9c98ed7cbb8f135439f145a8cbe7e50ede42bb5b5ab45c29`
- License: [GPL-3.0](../LICENSES/GPL-3.0.txt). The official installer retains the
  upstream licenses and third-party notices within its payload.
- Corresponding upstream source, build scripts and dependency references are
  available at no charge in the [Weasel 0.17.4 source tree](https://github.com/rime/weasel/tree/0.17.4)
  and its pinned submodules. Obtain the complete checkout with:

  ```bash
  git clone --branch 0.17.4 --recurse-submodules https://github.com/rime/weasel.git
  ```

The package builder verifies the binary hash before bundling. Setup verifies it
again before running the official installer with `/S /T` (silent, Traditional
Chinese). Only the engine installer requests administrator privileges. YueKey
configures and deploys the typing profile for the original current user, and adds
the installed input profile without replacing the user's default keyboard.

建置及安裝時都會核對安裝檔 SHA-256。只有引擎安裝會要求管理員權限；速成設定
及部署由原本的使用者執行，並保留預設鍵盤。

Existing compatible Weasel installations (0.17.4 or newer) are reused. Older or
incomplete installations require an explicit upstream update/repair; YueKey does
not silently overwrite them. Cancelling the administrator prompt leaves setup
available to retry. Removing YueKey preserves the shared engine, Rime settings,
learning and backups. Weasel can be removed separately through Windows Apps after
it is no longer needed by any typing profile.

已安裝的相容版本會直接沿用；舊版或不完整安裝須先透過官方安裝程式更新／修復。
取消管理員提示後可重試。移除粵鍵會保留共用引擎、設定、學習及備份；確定其他
輸入方案不再使用小狼毫後，可於 Windows 應用程式設定另行移除。
