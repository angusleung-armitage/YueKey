# 粵鍵 YueKey

**在 Ubuntu 和 Windows 打速成，講廣東話。**  
**Quick typing. Cantonese dictation. For Ubuntu and Windows.**

粵鍵是一套為香港用字及廣東話日常輸入而設的開源輸入工具。用熟悉的速成首尾碼打字，或連按兩次 Ctrl，直接講出你想寫的內容。打字和語音辨識都在電腦本機處理。

YueKey is an open-source input tool for Hong Kong Chinese and everyday Cantonese. Type with first-and-last Cangjie codes, or double-tap Ctrl and dictate. Both typing and speech recognition run locally on your computer.

[免費下載 · Free downloads](https://github.com/angusleung-armitage/YueKey/releases) · [Ubuntu 安裝](docs/INSTALL.md) · [Windows installation](docs/WINDOWS.md) · [開始使用 · Get started](#get-started) · [語音輸入 · Dictation](#dictation) · [常見問題 · Troubleshooting](docs/INSTALL.md#troubleshooting)

## 為甚麼用粵鍵？ · Why YueKey?

| 功能 | 中文 | English |
| --- | --- | --- |
| ⌨️ 速成輸入 · Quick input | 首尾碼打字、數字選字、空白鍵確認，支援一碼及兩碼。 | One- and two-letter Quick codes, numbered candidates and Space to confirm. |
| 🇭🇰 香港用字 · Hong Kong characters | 支援嘅、喺、唔、冇、咗、啲、嚟、㗎、𨋢等字。 | Includes characters used in everyday Hong Kong Chinese and Cantonese. |
| 💬 關聯字 · Word continuations | 按廣東話詞頻提供候選字及關聯字，並在本機學習你的選字習慣。 | Cantonese frequency data, related-word suggestions and local candidate learning. |
| 🎙️ 廣東話語音 · Cantonese dictation | GNOME／Windows 下連按兩次 Ctrl 開始／停止，輸出香港繁體字，可加入標點。 | Double Ctrl starts/stops dictation on GNOME and Windows, with HK Traditional output and optional punctuation. |
| 🖥️ 純 CPU · CPU only | 使用 SenseVoice Small Yue INT8，無需 GPU 或雲端語音帳戶。 | SenseVoice Small Yue INT8 runs on the CPU, without a GPU or cloud speech account. |
| 🎨 可調校外觀 · Your preferred layout | 候選字橫排／直排、字體大小、每頁字數及淺色／深色主題。 | Adjust candidate orientation, font size, page size and light/dark appearance. |

### 用你的方式輸入 · Choose how to write

```text
速成 Quick        hi → 選擇／select 我
香港用字 HK       rf → 選擇／select 喺
標點 Punctuation  zb → ，    zd → 。    zi → ？    zj → ！
語音 Dictation    Ctrl × 2 → 講廣東話／speak → Ctrl × 2 → 插入文字／insert text
```

速成碼可能對應多個字，選字次序會受詞頻及個人學習影響。語音例子只說明操作方式；辨識結果會隨錄音而異。

Quick codes can match several characters; frequency data and personal learning affect their order. The dictation example describes the interaction, not a guaranteed transcript.

## 支援平台 · Supported platforms

| 平台 · Platform | 速成、學習及關聯字 · Typing, learning & suggestions | 語音輸入 · Dictation |
| --- | --- | --- |
| Ubuntu 26.04 amd64 · GNOME Shell 50 · IBus | ✓ | ✓ · 選配／Optional |
| Kubuntu 26.04 amd64 · KDE · Fcitx5 | ✓ | 尚未提供／Not available yet |
| Windows 11 x64 · Weasel 0.17.4 | 速成及學習；暫無關聯字／Typing and learning; no continuations yet | 初期支援 · Initial support |

目前為 **0.3.0 開發版本**。語音辨識、專有名詞及中英夾雜內容可能出錯；其他系統版本及個別應用程式仍需驗證。詳見[相容性紀錄](docs/compatibility.md)及[語音測試紀錄](docs/dictation-validation.md)。

This is the **0.3.0 development release**. Recognition may make mistakes, especially with names and mixed Cantonese/English speech. Other OS versions and individual applications need further validation. See the [compatibility record](docs/compatibility.md) and [dictation validation](docs/dictation-validation.md).

<a id="get-started"></a>
## 開始使用 · Get started

Windows：下載並執行 `YueKey-0.3.0-windows-x64-setup.exe`，從開始功能表開啟 YueKey，按照 **[Windows 雙語指南](docs/WINDOWS.md)** 安裝小狼毫及啟用語音。

Windows: run `YueKey-0.3.0-windows-x64-setup.exe`, open YueKey from the Start Menu, and follow the **[Windows guide](docs/WINDOWS.md)** for Weasel and dictation setup. No separate Python installation is needed. A portable ZIP is also available.

Ubuntu 完整步驟見 **[中英雙語安裝指南](docs/INSTALL.md)**，包括從原始碼建置、GNOME／KDE 安裝、語音設定及首次免登出啟用。

Follow the **[bilingual installation guide](docs/INSTALL.md)** for source builds, GNOME/KDE installation, speech setup and first-time activation without signing out.

由 Releases 下載所需 `.deb` 到 `dist/` 資料夾，或自行建置後，可執行以下 GNOME 安裝指令：

Download the required `.deb` files from Releases into a `dist/` folder, or build them from source, then run:

```bash
sudo apt install ./dist/quick-hk-core_0.3.0-1_all.deb \
  ./dist/quick-hk-predict_0.3.0-1_amd64.deb \
  ./dist/quick-hk-gnome_0.3.0-1_all.deb
quick-hk setup --frontend ibus
```

在 **設定 → 鍵盤 → 輸入來源** 加入 **Chinese (Rime)**，切換至 Rime，點選文字欄後按 **F4**，選擇 **港式速成**。設定介面可用以下指令開啟：

Add **Chinese (Rime)** under **Settings → Keyboard → Input Sources**. Switch to Rime, focus a text field, press **F4**, and select **港式速成**. Open the settings window with:

```bash
quick-hk configure
```

> **名稱與相容性 · Naming and compatibility**  
> 產品名稱為 **粵鍵 YueKey**。現有套件及指令沿用 `quick-hk`，Rime 選單中的方案名稱沿用 **港式速成**，讓既有設定及學習資料繼續使用。  
> The product is **YueKey**. Package names and commands remain `quick-hk`, and the Rime scheme remains **港式速成**, preserving compatibility with existing settings and learned data.

<a id="dictation"></a>
## 用廣東話講出來 · Say it in Cantonese

在 GNOME 安裝[選配語音套件及模型](docs/INSTALL.md#dictation-setup)後：

For Windows, follow the [companion setup](docs/WINDOWS.md#3-廣東話語音--cantonese-dictation). The steps below describe Ubuntu.

After installing the [optional speech package and models](docs/INSTALL.md#dictation-setup) on GNOME:

1. 選擇 **港式速成**，點選文字欄，完成未確認的速成碼。  
   Select **港式速成**, focus a text field and finish any pending character code.
2. 連按兩次 **左 Ctrl**，看到收音提示後開始講話。  
   Double-tap **Left Ctrl** and speak when the recording indicator appears.
3. 再連按兩次 **左 Ctrl**，停止錄音並插入辨識文字。  
   Double-tap **Left Ctrl** again to stop and insert the transcript.
4. 按 **Esc** 取消；切換文字欄或按其他打字鍵亦會取消。  
   Press **Esc** to cancel. Changing fields or typing another key also cancels.

每次最多錄音兩分鐘。可在設定選擇麥克風、左右 Ctrl 及自動標點；如左 Ctrl 已用作中英切換，語音會改用右 Ctrl。

Each recording lasts up to two minutes. Choose the microphone, Ctrl key and automatic punctuation in settings. If Left Ctrl already switches Chinese/English, dictation uses Right Ctrl.

## 本機處理，保留私隱 · Local by design

- 打字、選字學習及語音辨識均在本機進行；首次下載套件、執行環境及模型需要網絡。  
  Typing, candidate learning and recognition are local. Initial package, runtime and model downloads require Internet access.
- 語音錄音及待插入的辨識文字只在記憶體暫存，工具不會將它們寫入記錄檔。  
  Captured audio and pending transcripts stay in memory; the tool does not log them.
- 無按鍵遙測，無網絡預測。部署會備份設定；解除部署會保留學習資料及使用者修改。  
  No keystroke telemetry or network prediction. Deployment backs up configuration; removal preserves learned data and user edits.

## 一起改善粵鍵 · Help improve YueKey

歡迎分享錯碼、用字建議、安裝問題及不同應用程式的使用結果。回報時請附上系統版本、桌面環境、應用程式名稱、重現步驟及以下診斷結果；貼出前先檢查是否包含個人路徑。

Contributions and reports are welcome: incorrect codes, vocabulary suggestions, installation problems and application compatibility. Include your OS, desktop, application, reproduction steps and the diagnostics below. Review personal paths before sharing the output.

```bash
quick-hk doctor --frontend ibus
quick-hk dictation status --json
```

KDE 使用者可把 `ibus` 改成 `fcitx5`；語音診斷只適用於有安裝語音功能的 GNOME 系統。  
KDE users can replace `ibus` with `fcitx5`; speech diagnostics apply to GNOME installations with dictation enabled.

如果粵鍵幫到你，歡迎 Star 專案、分享給有需要的朋友，或一起貢獻程式與用字資料。  
If YueKey helps you, star the project, share it with someone who needs Cantonese input, or contribute code and vocabulary improvements.

## 開源與鳴謝 · Open source and credits

粵鍵使用 Rime、IBus、Fcitx5、公開倉頡／速成／粵語資料，以及 sherpa-onnx、SenseVoice、Silero VAD、CT-Transformer 和 OpenCC。原創程式碼採用 **MIT**；字典並非 MIT，各項第三方程式、模型及資料保留原有授權。

YueKey builds on Rime, IBus, Fcitx5, open Cangjie/Quick/Cantonese data, sherpa-onnx, SenseVoice, Silero VAD, CT-Transformer and OpenCC. Original code is licensed under **MIT**. The dictionaries are not MIT; third-party code, models and data retain their respective licenses.

[授權 · License](LICENSE) · [來源與鳴謝 · Attribution](THIRD_PARTY.md) · [架構 · Architecture](docs/architecture.md) · [測試 · Validation](docs/compatibility.md)
