# 粵鍵 YueKey — Windows 安裝 · Windows installation

[← 返回介紹 · Back to README](../README.md)

Windows 11 x64 的初期支援：港式速成、標點符號、本機選字學習，以及選配的純 CPU 廣東話語音輸入。ARM64、32 位元及 Windows 10 尚未驗證。

Initial support targets Windows 11 x64: Cantonese Quick typing, punctuation, local candidate learning and optional CPU-only Cantonese dictation. ARM64, 32-bit Windows and Windows 10 have not been validated.

## 1. 免費下載 · Free download

到 [GitHub Releases](https://github.com/angusleung-armitage/ubuntu-quick-input-method/releases) 下載 **`YueKey-0.2.0-windows-x64.zip`** 及 `SHA256SUMS`。解壓整個資料夾到固定位置，例如 `%LOCALAPPDATA%\Programs\YueKey`。請保留 `_internal` 資料夾；不能只移動 EXE。

Download **`YueKey-0.2.0-windows-x64.zip`** and `SHA256SUMS` from [GitHub Releases](https://github.com/angusleung-armitage/ubuntu-quick-input-method/releases). Extract the entire folder to a permanent location, such as `%LOCALAPPDATA%\Programs\YueKey`. Keep `_internal` beside the executable.

在 PowerShell 檢查 ZIP 的 SHA-256，與下載頁的 `SHA256SUMS` 比對：  
Compare the ZIP's SHA-256 with `SHA256SUMS` in PowerShell:

```powershell
Get-FileHash .\YueKey-0.2.0-windows-x64.zip -Algorithm SHA256
```

此版本未有 Windows 程式碼簽署憑證，系統可能顯示發行者未經驗證。請只使用本專案 Release 的檔案及檢查碼。

This release is not code-signed; Windows may show an unverified publisher. Use this project's release assets and verify their checksums.

## 2. 安裝速成 · Install typing

1. 安裝官方 [小狼毫 Weasel 0.17.4](https://github.com/rime/weasel/releases/tag/0.17.4)。這是 Windows 的 Rime 輸入法前端。  
   Install official [Weasel 0.17.4](https://github.com/rime/weasel/releases/tag/0.17.4), the Rime frontend for Windows.
2. 開啟 **`YueKey.exe`**，確認小狼毫使用者資料夾。預設為 `%APPDATA%\Rime`；如安裝時改過位置，請選取正確資料夾。  
   Open **`YueKey.exe`** and confirm the Weasel user folder. The default is `%APPDATA%\Rime`; select your custom folder if needed.
3. 按 **安裝速成 · Install typing**。粵鍵會先備份相關檔案，保留其他輸入方案及學習資料。  
   Click **Install typing**. YueKey backs up affected files and retains other schemes and learned data.
4. 右擊系統匣的小狼毫圖示，選 **重新部署 · Deploy**，等待完成。  
   Right-click Weasel in the system tray, select **Deploy**, and wait for completion.
5. 按 **Win + Space** 切換到小狼毫。在文字欄按 **F4**，選 **港式速成**。試打 `hi1` → `我`、`zb1` → `，`、`zd1` → `。`。  
   Press **Win + Space** to select Weasel. In a text field, press **F4** and choose **港式速成**. Try `hi1` → `我`, `zb1` → `，`, and `zd1` → `。`.

選字次序會隨本機學習改變。Windows 版使用同一份速成字典；Ubuntu 的原生關聯字插件及 GTK 設定介面並未包含在此版。小狼毫的外觀可按其官方設定方式調整。

Candidate order can change with local learning. Windows uses the same Quick dictionary. This version does not include Ubuntu's native continuation-prediction plugin or GTK settings window. Configure candidate appearance through Weasel's own settings.

## 3. 廣東話語音 · Cantonese dictation

在粵鍵視窗按 **啟用語音／下載模型**。首次需要下載約 302 MB 的模型；每個檔案均會核對 SHA-256。Python 與 CPU 語音執行環境已包含在 ZIP，無需另裝 Python、GPU 驅動或語音雲端帳戶。模型下載後會在本機初始化，通過檢查才會顯示「Dictation ready」。

Click **Enable dictation / Get models**. First use downloads about 302 MB of models and verifies every SHA-256. Python and the CPU speech runtime are included in the ZIP. No separate Python installation, GPU driver or speech cloud account is needed. The models are initialized locally before the app reports **Dictation ready**.

1. 在 Windows 音效設定選好預設麥克風，並允許桌面應用程式使用麥克風。  
   Select your default microphone in Windows sound settings and allow desktop apps to access it.
2. 點選一般文字欄，完成未確認的輸入碼。連按兩次 **左 Ctrl**，看到收音提示後開始講廣東話。  
   Focus a normal text field and finish any pending input code. Double-tap **Left Ctrl** and speak when the listening indicator appears.
3. 再連按兩次 **左 Ctrl** 停止，文字會插入原來欄位。每次最多錄音兩分鐘。可在視窗改用右 Ctrl 或關閉自動標點。  
   Double-tap **Left Ctrl** again to stop and insert into the original field. Each recording lasts up to two minutes. The app offers Right Ctrl and optional punctuation.
4. 按 **Esc**、按其他打字鍵、點擊滑鼠或切換欄位會取消。關閉粵鍵會停止語音；可縮小視窗繼續使用。每次重新開啟後須再次按「啟用語音」。  
   **Esc**, other typing keys, mouse clicks or a field change cancel dictation. Closing YueKey stops speech; minimizing keeps it available. Enable dictation again after reopening the app.

Windows 語音是獨立伴隨程式，可配合不同輸入法使用。它只接受 Windows UI Automation 能識別的一般 Edit／Document 欄位；密碼欄、無法識別的欄位及較高權限的程式不支援。辨識文字透過 Windows Unicode 輸入插入，工具不使用剪貼簿，也不會儲存錄音或逐字稿。

Windows dictation is a separate companion that can work alongside different input methods. It accepts normal Edit/Document fields identified by Windows UI Automation. Password fields, unidentifiable controls and elevated applications are unsupported. Transcripts use Windows Unicode input; YueKey does not use the clipboard or save recordings/transcripts.

## 排解問題及移除 · Troubleshooting and removal

- **沒有候選字：** 確認已重新部署，並在 F4 選了港式速成；Shift 可切換中英文。  
  **No candidates:** redeploy, select 港式速成 with F4, and check Chinese mode with Shift.
- **語音沒有開始：** 確認粵鍵正在執行及已啟用語音，兩次 Ctrl 都要按下再放開；Ctrl 組合快捷鍵不會開始錄音。先在一般文字編輯器測試。  
  **Dictation does not start:** keep YueKey running and enabled; fully release Ctrl between taps. Ctrl shortcuts do not start recording. Try a normal text editor first.
- **下載失敗：** 保留已下載檔案，稍後再按啟用語音；下載支援續傳及檢查碼核對。  
  **Download failure:** click Enable again later; verified files are reused and partial downloads resume.
- **移除速成：** 在粵鍵按「移除」，再於小狼毫重新部署。未修改的安裝檔案會還原；使用者後來修改的檔案及學習資料會保留。  
  **Remove typing:** click Remove in YueKey and redeploy Weasel. Unmodified installation files are restored; later user edits and learning are retained.
- **移除程式與模型：** 關閉粵鍵並刪除解壓的程式資料夾。模型另存於 `%LOCALAPPDATA%\YueKey\dictation\models`，可自行刪除。備份存於小狼毫資料夾內的 `yuekey-backups`。  
  **Remove the app/models:** close YueKey and delete its extracted folder. Models live separately at `%LOCALAPPDATA%\YueKey\dictation\models`; backups are in `yuekey-backups` inside the Weasel user folder.

## 從原始碼建置 · Build from source

先在 Ubuntu 按[建置指南](INSTALL.md#build)產生字典，執行 `python3 tools/prepare_windows_data.py`，把 `build/windows-data` 複製到 Windows checkout 的相同位置。然後在 Windows x64／Python 3.12 執行：

Generate the dictionary on Ubuntu using the [build guide](INSTALL.md#build), run `python3 tools/prepare_windows_data.py`, and copy `build/windows-data` to the same location in a Windows checkout. On Windows x64 with Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r desktop/windows/requirements.txt
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m pytest tests/test_windows.py -q
.\.venv\Scripts\python.exe tools/package_windows.py
```

CI 在 Windows runner 建置並檢查封裝後的程式、Win32 介面及 CPU 模型。真實 Windows 11 麥克風及各應用程式的完整使用測試仍須持續收集，不能將 CI 通過視為所有應用程式已驗證。

CI builds on a Windows runner and checks the packaged app, Win32 interfaces and CPU models. Real Windows 11 microphone and application compatibility testing remains ongoing; passing CI does not validate every application.
