粵鍵 YueKey 0.6.9 修正 Windows 右邊的鍵盤識別：以「中」取代小狼毫的 W。英文鍵盤在這個位置顯示 ENG；左邊「港／A」的輸入模式圖示及「粵」應用程式圖示維持不變。

YueKey 0.6.9 replaces the Windows keyboard identifier W with 中, in the position where an English keyboard displays ENG. The separate 港/A input-mode icons and 粵 application logo are unchanged.

- **安裝 / Install:** close YueKey and run the new setup EXE. Approve the administrator prompt for the bundled **YueKey Keyboard Icon** component. It changes the shared Windows Weasel profile icon registration and backs up the original values; no Weasel binaries are modified. Existing matching installations are reused. The portable ZIP includes the same component through **Set up typing**.
- **顯示 / Display:** switch to another keyboard and back after installation. If Windows retains a cached icon, sign out and back in when convenient. YueKey never restarts Explorer or ends your session automatically. Win + Space retains the registered Weasel name.
- **還原 / Restore:** uninstall **YueKey Keyboard Icon** from Windows Installed apps to restore the original icons. Later customizations are preserved. Removing the per-user YueKey app retains the shared icon component and Weasel engine for other users.
- **驗證 / Validation:** Windows installer CI checks the actual 中 resource at 16, 20, 24, 32, 40 and 48 pixels on x64, x86 and ARM64, installation and repair, exact restoration of registry value types and missing values, and preservation of later customizations. Existing typing, candidate layout and CPU dictation checks also run.
- **Windows downloads:** choose the `windows-x64`, `windows-x86` or `windows-arm64` setup EXE. Weasel is included; voice models download on first enable. Portable ZIPs are also available.
- **Ubuntu / Kubuntu 26.04:** packages are provided for amd64 and arm64. This Windows keyboard-icon change does not require an Ubuntu update. Existing GNOME extension updates still require a new login to load refreshed JavaScript.
- **Limits:** no Linux i386/ARM32 packages or universal DEB for older distributions. Windows x86 is tested under WOW64. Hardware microphones and individual applications still need hands-on checks; Windows packages are not code-signed.
- **授權 / License:** original YueKey code and artwork are MIT. Weasel is GPL-3.0; dictionaries, models and runtimes retain their licenses. [Weasel binary and corresponding upstream source](https://github.com/angusleung200/YueKey/blob/v0.6.9/docs/WEASEL.md).

[Linux 中英指南 / Guide](https://github.com/angusleung200/YueKey/blob/v0.6.9/docs/INSTALL.md) · [Windows guide](https://github.com/angusleung200/YueKey/blob/v0.6.9/docs/WINDOWS.md) · [標點對照 / Symbols](https://github.com/angusleung200/YueKey/blob/v0.6.9/docs/PUNCTUATION.md)
