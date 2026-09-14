粵鍵 YueKey 0.6.7 將 Ubuntu／Kubuntu 設定視窗改成與 Windows 相同的四頁版面：深綠導覽列、白色設定卡片、「粵」圖示及固定的儲存按鈕。

YueKey 0.6.7 brings the Windows settings layout to Ubuntu and Kubuntu: the same four pages, dark green sidebar, white cards, 粵 icon and persistent Save changes button.

- **總覽 / Overview:** typing setup status, Set up typing, a practice field and a shortcut to voice settings.
- **輸入 / Typing:** all candidate, learning, continuation, punctuation and language-key preferences. Switching pages preserves unsaved values.
- **語音 / Voice:** enable or disable dictation, verify or prepare CPU models, choose a microphone and the double-Ctrl shortcut. An unplugged microphone stays selected. Ubuntu/Kubuntu speech runs in the background after Settings closes.
- **進階 / Advanced:** open the appropriate IBus/Fcitx5 folder, back up and reset learning, remove the typing profile while preserving learned data, and open the installation guide. Active learning databases remain protected by the existing reset checks.
- **共用介面 / Shared design:** Linux and Windows use one palette and page-title definition, alongside the existing shared 13 preferences and bilingual option labels. System window borders, native controls and activation instructions still follow the platform.
- **驗證 / Validation:** real GTK tests cover all 13 controls, four pages at two window sizes, long microphone names, saved and unsaved settings, setup, enable/disable, deployment failure and close protection. A 200% scale check also runs with a dark system theme. Windows retains its installer and real UI checks on x64, x86 and ARM64.
- **Ubuntu / Kubuntu 26.04:** choose `yuekey_0.6.7-1_amd64.deb` or `yuekey_0.6.7-1_arm64.deb`. Install with `sudo apt install ./yuekey_0.6.7-1_$(dpkg --print-architecture).deb`, then reopen **粵鍵 YueKey** or run `quick-hk configure`. The new Settings window needs no sign-out. Existing users keep their preferences and learned words. The all-in-one DEB includes CPU speech models; APT resolves system dependencies.
- **Windows:** choose the `windows-x64`, `windows-x86` or `windows-arm64` setup EXE. The installer includes Weasel and preserves user settings. Voice models download on first enable; ZIPs are also available.
- **保留功能 / Existing features:** case-insensitive Quick codes, list-only continuations, traditional Z-code punctuation and the green microphone near the caret remain available. This release does not change GNOME's microphone extension JavaScript. An older extension still cached from before 0.6.6 loads its new microphone at the next login.
- **Limits:** no Linux i386/ARM32 packages or universal DEB for older distributions. Windows x86 is tested under WOW64. Hardware microphones and individual applications still need hands-on checks; Windows packages are not code-signed.
- **授權 / License:** original YueKey code and artwork are MIT. Weasel is GPL-3.0; dictionaries, models and runtimes retain their licenses. [Weasel binary and corresponding upstream source](https://github.com/angusleung200/YueKey/blob/v0.6.7/docs/WEASEL.md).

[Linux 中英指南 / Guide](https://github.com/angusleung200/YueKey/blob/v0.6.7/docs/INSTALL.md) · [Windows guide](https://github.com/angusleung200/YueKey/blob/v0.6.7/docs/WINDOWS.md) · [標點對照 / Symbols](https://github.com/angusleung200/YueKey/blob/v0.6.7/docs/PUNCTUATION.md)
