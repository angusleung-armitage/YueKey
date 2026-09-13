# 粵鍵 YueKey — 安裝指南 · Installation guide

[← 返回介紹 · Back to README](../README.md)

本指南適用於 Ubuntu 26.04 amd64／arm64（GNOME Shell 50／IBus）及 Kubuntu 26.04 amd64／arm64（KDE／Fcitx5）。語音輸入支援 GNOME／IBus 及 KDE／Fcitx5。Windows 使用者請看 [Windows 安裝指南](WINDOWS.md)。

This guide targets Ubuntu 26.04 amd64／arm64 with GNOME Shell 50/IBus and Kubuntu 26.04 amd64／arm64 with KDE/Fcitx5. Dictation supports GNOME/IBus and KDE/Fcitx5. For Windows, see the [Windows guide](WINDOWS.md).

產品名稱為 **粵鍵 YueKey**；本版本套件為 `yuekey`，指令仍使用 `quick-hk`，Rime 方案名稱仍是 **港式速成**。所有 `quick-hk` 指令都應以桌面使用者執行；只有系統套件安裝／移除需要 `sudo`。

The product is **YueKey**; the package is `yuekey` and commands remain `quick-hk` and the **港式速成** Rime scheme name. Run all `quick-hk` commands as your desktop user. Only system package installation/removal needs `sudo`.

[建置 · Build](#build) · [GNOME](#gnome) · [語音 · Dictation](#dictation-setup) · [免登出 · Without signing out](#live-activation) · [KDE](#kde) · [排解問題 · Troubleshooting](#troubleshooting) · [移除 · Uninstall](#uninstall)

<a id="build"></a>
## 1. 準備安裝套件 · Prepare the packages

可先到 [GitHub Releases](https://github.com/angusleung-armitage/YueKey/releases) 免費下載本平台單一 all-in-one `.deb` 及 `SHA256SUMS`，放入 `dist/` 資料夾，然後跳到 GNOME／KDE 安裝步驟。只核對已下載的檔案時可用 `sha256sum --check --ignore-missing SHA256SUMS`。

Download the single all-in-one `.deb` and `SHA256SUMS` for free from [GitHub Releases](https://github.com/angusleung-armitage/YueKey/releases), place them in a `dist/` folder, then continue to GNOME/KDE installation. To verify only the files you downloaded, use `sha256sum --check --ignore-missing SHA256SUMS`.

以下由原始碼建置本機 `.deb`。先安裝 [Docker Engine](https://docs.docker.com/engine/install/ubuntu/)，確認 `docker version` 能連接 Docker，再在包含 `Dockerfile.dev` 的專案根目錄執行：

The following steps build local `.deb` packages from source. Install [Docker Engine](https://docs.docker.com/engine/install/ubuntu/), confirm that `docker version` can connect to Docker, then run these commands in the project root containing `Dockerfile.dev`:

```bash
docker build -f Dockerfile.dev -t yuekey-dev:26.04 .
docker run --rm --init --user "$(id -u):$(id -g)" \
  -v "$PWD:/work" yuekey-dev:26.04 bash -c '
  python3 -m venv build/linux-venv &&
  build/linux-venv/bin/python -m pip install --require-hashes --only-binary=:all: -r desktop/linux/requirements.txt &&
  build/linux-venv/bin/python tools/package_linux_speech.py &&
  make all test packages'
```

首次建置需要網絡。若 Docker 的 bridge 網絡無法連接套件來源，可按網絡環境嘗試在 `docker build` 及 `docker run` 加上 `--network host`。這不是所有網絡問題的通用修復。

The first build needs Internet access. If Docker's bridge network cannot reach package sources, try `--network host` with `docker build` and `docker run` where appropriate for your network. It is not a general fix for every connectivity problem.

建置完成後，`dist/` 應有以下檔案；此版本的檔名為：  
After the build, `dist/` should contain these files for this version:

| 套件 · Package | 用途 · Purpose |
| --- | --- |
| `yuekey_0.5.0-1_amd64.deb` **或 / or** `yuekey_0.5.0-1_arm64.deb` | 一個檔案包含全部 YueKey 元件及 CPU 語音模型／All YueKey components and CPU speech models |
| `SHA256SUMS` | 套件檢查碼／Package checksums |

建置使用主機的 CPU 架構；各架構須分別建置。執行 `dpkg --print-architecture` 選擇對應檔案。此版本不提供 Linux i386／ARM32；亦不支援以強制架構選項安裝錯誤 DEB。詳見[架構指南](ARCHITECTURES.md)。

Builds use the host CPU architecture; build each architecture separately. Select the matching file with `dpkg --print-architecture`. Linux i386/ARM32 packages are unavailable. Do not force installation of a mismatched DEB. See the [architecture guide](ARCHITECTURES.md).

可在 `dist/` 核對檔案完整性：  
Check file integrity inside `dist/`:

```bash
(cd dist && sha256sum --check SHA256SUMS)
```

已有這些套件可跳到下一節。Docker 只用於建置；日常輸入直接在桌面運作。  
If you already have these packages, continue below. Docker is used for building; everyday input runs directly on the desktop.

<a id="gnome"></a>
## 2. Ubuntu GNOME：安裝速成 · Install Quick input

在專案根目錄執行：  
Run from the project root:

```bash
sudo apt install ./dist/yuekey_0.5.0-1_$(dpkg --print-architecture).deb
quick-hk setup --frontend ibus
```

安裝只把檔案放到系統；`setup` 才會部署到目前使用者的 Rime 設定。  
Package installation places files on the system; `setup` deploys them to the current user's Rime profile.

首次安裝新插件／擴充功能後，可以登出再登入，或使用下方[免登出步驟](#live-activation)，然後繼續以下操作。如要加語音輸入，可先完成下一節，一次啟用。

After installing new plugins/extensions, sign out and back in or use the [no-logout steps](#live-activation), then continue below. If you also want dictation, finish the next section first and activate everything together.

1. 在 **設定 → 鍵盤 → 輸入來源** 加入 **Chinese (Rime)**，保留原有英文輸入來源。  
   Add **Chinese (Rime)** in **Settings → Keyboard → Input Sources**, keeping your English source.
2. 用 **Super+Space** 切換至 Rime，點選文字欄，按 **F4**，選擇 **港式速成**；如未見，可按 Page Down。  
   Switch to Rime with **Super+Space**, focus a text field, press **F4** and select **港式速成**. Use Page Down if needed.
3. 在 Extensions 啟用 **粵鍵 YueKey · Candidates**，套用候選字外觀。  
   Enable **粵鍵 YueKey · Candidates** in Extensions for the candidate appearance.

開啟 **YueKey Settings／粵鍵設定** 或執行：  
Open **YueKey Settings／粵鍵設定**, or run:

```bash
quick-hk configure
```

舊套件可能仍顯示先前的設定視窗名稱；指令相同。  
Older packages may show the previous settings-window name; the command is the same.

<a id="dictation-setup"></a>
## 3. GNOME：加入廣東話語音 · Add Cantonese dictation

all-in-one DEB 已包含 SenseVoice Small Yue INT8、Silero VAD、CT-Transformer INT8 標點模型、OpenCC 及獨立 CPU 執行環境。毋須安裝 uv／Python 或另行下載模型。`setup` 會核對已安裝檔案並測試靜音，不會開啟麥克風。

The all-in-one DEB includes SenseVoice Small Yue INT8, Silero VAD, CT-Transformer INT8 punctuation, OpenCC and an isolated CPU runtime. No uv, separate Python setup or model download is needed. `setup` verifies installed files and checks silence without opening the microphone.

```bash
quick-hk dictation setup
quick-hk configure --set dictation_enabled=true --frontend ibus
```

語音預設關閉；啟用後仍須連按 Ctrl 才開始收音。安裝 DEB 時 APT 可能需要下載系統依賴；安裝完成後語音可完全離線使用。

Dictation is disabled by default and only records after the Ctrl gesture. APT may download system dependencies during DEB installation; speech works fully offline afterward.

用[免登出步驟](#live-activation)或重新登入載入新元件，再在 Extensions 啟用 **粵鍵 YueKey · Dictation**。選擇 **港式速成**，點選文字欄並完成待確認的速成碼後，連按兩次 **左 Ctrl** 開始，再連按兩次停止並插入文字；**Esc** 取消。每次最多兩分鐘。

Load the new components with the [no-logout steps](#live-activation) or a new login, then enable **粵鍵 YueKey · Dictation** in Extensions. Select **港式速成**, focus a text field and finish pending character codes. Double-tap **Left Ctrl** to start, then double-tap again to stop and insert text; **Esc** cancels. Each recording is limited to two minutes.

在 `quick-hk configure` 選擇麥克風、Ctrl 鍵及自動標點。若左 Ctrl 已作中英切換，語音會使用右 Ctrl。

Use `quick-hk configure` to select the microphone, Ctrl key and automatic punctuation. If Left Ctrl switches Chinese/English, dictation uses Right Ctrl.

<a id="live-activation"></a>
## 4. 首次免登出啟用 · First activation without signing out

以下適用於 GNOME 50 的**首次安裝**。先完成目前正在組合的文字，再重新啟動 IBus；這會短暫中斷輸入法連線，但不會重新啟動桌面。

These steps apply to a **first installation** on GNOME 50. Finish any current composition before restarting IBus. Input-method connections briefly restart; the desktop session stays running.

```bash
systemctl --user restart org.freedesktop.IBus.session.GNOME.service
```

GNOME 尚未發現新擴充功能時，按 **Alt+F2**，輸入 `lg`，按 Enter。下列各行要**逐行貼入並按 Enter**。每行應完整複製，字串內不要加空格。

If GNOME has not discovered the new extensions, press **Alt+F2**, enter `lg` and press Enter. **Paste each line below separately and press Enter after each one.** Copy each line intact; do not add spaces inside strings.

第一行啟用候選字外觀；已啟用語音才執行第二行。已載入的擴充功能會沿用現有實例：  
The first command activates candidate styling. Run the second only if you enabled dictation. An already loaded extension reuses its existing instance:

```javascript
const u='quick-hk@quick-hk.local'; const m=Main.extensionManager; m.lookup(u) ? m.enableExtension(u) : await m.loadExtension(m.createExtensionObject(u, Gio.File.new_for_path(global.userdatadir).get_child('extensions').get_child(u), 2))
```

```javascript
const u='quick-hk-dictation@quick-hk.local'; const m=Main.extensionManager; m.lookup(u) ? m.enableExtension(u) : await m.loadExtension(m.createExtensionObject(u, Gio.File.new_for_path(global.userdatadir).get_child('extensions').get_child(u), 2))
```

完成後按 Esc，在 Extensions 啟用相應項目，再選擇 Rime／港式速成並點選文字欄。`undefined` 或 `true` 可以是正常結果；出現 `<exception …>` 則表示指令未成功。

Press Esc, enable the relevant entries in Extensions, then select Rime/港式速成 and focus a text field. `undefined` or `true` can be a normal result; `<exception …>` means the command failed.

此方法不能替換本次登入已載入的 JavaScript。更新既有擴充功能後，仍須在方便時登出再登入；Rime 指令及設定則可重新部署。

This method cannot replace JavaScript already imported during the current session. After updating an already loaded extension, sign out and back in when convenient. Rime configuration can be redeployed separately.

<a id="kde"></a>
## 5. Kubuntu KDE：安裝速成 · Install Quick input

```bash
sudo apt install ./dist/yuekey_0.5.0-1_$(dpkg --print-architecture).deb
quick-hk setup --frontend fcitx5
```

在 KDE Wayland 設定選擇 **Fcitx 5** 作虛擬鍵盤／輸入法，登出後登入。開啟 Fcitx 5 Configuration、加入 Rime，再在文字欄按 F4 選 **港式速成**。

In KDE Wayland settings, select **Fcitx 5** as the virtual keyboard/input method, then sign out and back in. Open Fcitx 5 Configuration, add Rime, and select **港式速成** through F4 in a text field.

使用 **Classic User Interface**，選 **YueKey Light** 或 **YueKey Dark**。如候選窗由 Kimpanel 接管，先停用 Kimpanel 才能使用 Classic UI 主題。外觀、選字學習、關聯字、標點及中英切換均可在 `quick-hk configure --frontend fcitx5` 設定。

Use **Classic User Interface** with **YueKey Light** or **YueKey Dark**. If Kimpanel controls the candidate window, disable it to use Classic UI themes. Use `quick-hk configure --frontend fcitx5` for appearance, learning, continuations, punctuation and language switching.

### KDE 廣東話語音 · KDE Cantonese dictation

先完成上述 KDE 安裝，再執行：  
After completing the KDE typing installation:

```bash
quick-hk dictation setup
quick-hk configure --frontend fcitx5 --set dictation_enabled=true
```

完成正在組合的文字後，在 Fcitx5 系統匣選單選「重新啟動」。首次安裝原生橋接需要重新啟動 Fcitx5；現有 KDE 桌面毋須登出。若尚未將 KDE 的輸入法設定為 Fcitx5，先完成上一節的桌面設定。

Finish any active composition, then choose **Restart** from Fcitx5's tray menu. Restarting Fcitx5 loads the newly installed bridge; an existing KDE session does not need to sign out. If Fcitx5 is not yet configured as KDE's input method, complete the desktop setup above first.

開始本次登入的語音服務：  
Start the speech service for the current login:

```bash
quick-hk dictation serve --frontend fcitx5
```

這個指令會持續執行；保持終端開啟。之後每次登入，已啟用的語音服務會自動啟動。也可從 KDE 的「自動啟動」設定啟動 **YueKey Dictation**。

This command stays running; leave its terminal open. With dictation enabled, the service starts automatically on subsequent logins. You can also launch **YueKey Dictation** from KDE's Autostart settings.

選擇港式速成並點選文字欄，連按兩次 Ctrl 開始／停止；Esc 取消。候選窗會顯示收音狀態及音量。語音直接交由 Fcitx5 插入原欄位，毋須 GNOME 擴充功能或剪貼簿。密碼／敏感欄位及無法提供欄位安全資訊的 XIM 程式不會啟動語音；Qt／GTK 的 Fcitx5 整合及原生 Wayland 是支援路徑。

Select 港式速成 and focus a text field. Double Ctrl starts/stops; Esc cancels. The candidate panel shows recording status and microphone level. Fcitx5 inserts the result into the original field directly. No GNOME extension or clipboard is required. Password/sensitive fields and XIM clients that cannot report field security are excluded; use Qt/GTK Fcitx5 integration or native Wayland.

```bash
quick-hk dictation status
quick-hk configure --frontend fcitx5
```


## 6. 常用操作與設定 · Everyday use and settings

| 按鍵 · Key | 操作 · Action |
| --- | --- |
| `1`–`9` | 選候選字／Choose a candidate |
| Space | 確認；或先展開候選字／Confirm, or reveal hidden candidates first |
| Page Up / Page Down | 上／下一頁／Previous/next page |
| Backspace | 修改速成碼／Edit the code |
| Esc | 取消組字或語音／Cancel composition or dictation |
| 左 Shift · Left Shift | 中英切換，可設定／Toggle Chinese/English; configurable |
| 左 Ctrl 連按兩次 · Double Left Ctrl | 語音開始／停止／Start/stop dictation |

| 標點碼 · Code | 符號 · Symbol | 標點碼 · Code | 符號 · Symbol |
| --- | --- | --- | --- |
| `zb` | ， | `zc` | 、 |
| `zd` | 。 | `zg` | ； |
| `zh` | ： | `zi` | ？ |
| `zj` | ！ | `zl` | … |
| `zy` | — | | |

用數字鍵或 Space 選取候選符號。  
Use a number key or Space to choose the punctuation candidate.

```bash
quick-hk configure
quick-hk configure --show
quick-hk configure --set theme=dark --frontend ibus
```

KDE 請使用 `--frontend fcitx5`。套用設定後須重新載入 Rime；`setup`／`deploy` 本身不會重新啟動輸入服務。

Use `--frontend fcitx5` on KDE. Reload Rime after applying changes; `setup`/`deploy` do not restart input services themselves.

<a id="troubleshooting"></a>
## 7. 排解問題 · Troubleshooting

| 情況 · Symptom | 處理方法 · What to check |
| --- | --- |
| 打 `h` 出現和、好、還／Unexpected candidates for `h` | 可能是其他 Rime 方案；在文字欄按 F4 選 **港式速成**。／Another Rime scheme may be active; select **港式速成** with F4. |
| `zb` 沒有標點／No punctuation for `zb` | 確認已更新並部署本版本資料，再重新載入 Rime；輸入 `zb1` 測試。／Deploy this version's data, reload Rime and try `zb1`. |
| Preferences 無法開啟／Preferences does not open | 執行 `quick-hk configure`；setup 後重新開啟 GNOME Settings。／Run `quick-hk configure`; reopen GNOME Settings after setup. |
| View Keyboard Layout 無法開啟／Keyboard preview fails | Rime 的 `default` 佈局可能沒有預覽；用英文輸入來源查看實體鍵盤。／Rime's `default` layout may have no preview; use the English source to inspect the physical layout. |
| 雙 Ctrl 沒有反應／Double Ctrl does nothing | 檢查語音已啟用、模型就緒、擴充功能啟用、港式速成中文模式、文字欄焦點及 Ctrl 選擇。／Check speech settings, models, extension activation, the Chinese Quick scheme, field focus and selected Ctrl key. |
| 密碼欄不能語音輸入／No dictation in password fields | 屬預期行為：已知密碼／私密欄位及未知輸入類型會被阻擋。／Expected: known password/private fields and unknown input types are blocked. |
| 語音無聲或停止／Silent or stopped capture | 在系統聲音設定及 `quick-hk configure` 檢查麥克風、靜音及裝置選擇。／Check the input device and mute settings in system sound settings and `quick-hk configure`. |

診斷指令／Diagnostics：

```bash
quick-hk doctor --frontend ibus
quick-hk dictation status --json
```

語音狀態中，最外層 `ready` 代表模型就緒；`service.ready` 代表模型已載入；`desktop_ready` 代表桌面擴充功能可用；`rime_ready` 代表 Rime 橋接已啟動。模型就緒不代表桌面已啟用。

In speech status, top-level `ready` means the models are prepared; `service.ready` means they are loaded; `desktop_ready` indicates the desktop extension is available; `rime_ready` indicates the Rime bridge has started. Prepared models alone do not mean desktop activation is complete.

### 資料位置 · Data locations

| 資料 · Data | 預設位置 · Default location |
| --- | --- |
| 設定／Preferences | `~/.config/quick-hk/settings.toml` |
| GNOME Rime | `~/.config/ibus/rime` |
| Fcitx5 Rime | `~/.local/share/fcitx5/rime` |
| 語音模型及環境／Speech models and runtime | `~/.local/share/quick-hk/dictation` |
| 設定備份／Configuration backups | `~/.local/state/quick-hk` |

適用位置會遵從 `XDG_CONFIG_HOME`、`XDG_DATA_HOME` 或 `XDG_STATE_HOME`；IBus Rime 使用 `$HOME/.config/ibus/rime`。兩個前端的學習資料獨立保存。

Applicable paths honor `XDG_CONFIG_HOME`, `XDG_DATA_HOME` or `XDG_STATE_HOME`; IBus Rime uses `$HOME/.config/ibus/rime`. The two frontends keep separate learning databases.

<a id="uninstall"></a>
## 8. 停用、移除及復原 · Disable, uninstall and recover

只停用語音／Disable dictation only：

```bash
quick-hk configure --set dictation_enabled=false --frontend ibus
```

GNOME 完整移除：先在 Extensions 停用兩個粵鍵擴充功能，再執行：  
For removal on GNOME, first disable both YueKey extensions in Extensions, then run:

```bash
quick-hk uninstall --frontend ibus
sudo apt remove yuekey
```

KDE 移除／Remove the KDE installation：

```bash
quick-hk uninstall --frontend fcitx5
sudo apt remove yuekey
```

如兩個前端都已安裝，先分別解除部署，再移除共用套件。解除部署只還原未被修改的受管理檔案，保留使用者修改、學習資料及已下載模型；最後重新載入 Rime 或在方便時重新登入。

If both frontends are installed, remove both deployments before removing shared packages. Undeployment restores unchanged managed files and preserves user edits, learned data and downloaded models. Reload Rime afterward, or sign in again when convenient.

原生插件依賴建置時的指定 librime 版本。系統更新造成版本不符時，請重新建置套件，不要強制安裝不相容的二進位檔案。

Native plugins depend on the librime version used to build them. If a system update changes that dependency, rebuild the packages instead of forcing incompatible binaries to install.
