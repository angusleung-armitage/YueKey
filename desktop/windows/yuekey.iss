; YueKey per-user installer. SPDX-License-Identifier: MIT
; Build with tools/package_windows.py on Windows using Inno Setup 6.7+.
#ifndef AppVersion
  #error AppVersion is required
#endif
#ifndef RepoRoot
  #error RepoRoot is required
#endif

[Setup]
AppId=YueKey.Companion
AppName=YueKey
AppVersion={#AppVersion}
AppPublisher=YueKey contributors
AppPublisherURL=https://github.com/angusleung-armitage/YueKey
AppSupportURL=https://github.com/angusleung-armitage/YueKey/issues
AppUpdatesURL=https://github.com/angusleung-armitage/YueKey/releases
DefaultDirName={localappdata}\Programs\YueKey
DefaultGroupName=YueKey
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible and not arm64
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.22000
AppMutex=Local\YueKey.Companion
SetupMutex=Local\YueKey.Setup
CloseApplications=no
RestartApplications=no
UninstallDisplayIcon={app}\YueKey.exe
OutputDir={#RepoRoot}\dist
OutputBaseFilename=YueKey-{#AppVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
InfoBeforeFile={#RepoRoot}\desktop\windows\installer-info.txt

[Files]
Source: "{#RepoRoot}\build\windows-dist\YueKey\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\YueKey"; Filename: "{app}\YueKey.exe"; WorkingDir: "{app}"
Name: "{group}\Installation guide"; Filename: "{app}\docs\WINDOWS.md"
Name: "{userstartup}\YueKey"; Filename: "{app}\YueKey.exe"; Parameters: "--background"; WorkingDir: "{app}"; Tasks: startup

[Tasks]
Name: "startup"; Description: "Start YueKey at login / 登入時啟動粵鍵"; Flags: unchecked

[Run]
Filename: "{app}\YueKey.exe"; Description: "Open YueKey / 開啟粵鍵"; Flags: nowait postinstall skipifsilent

; Only installed application files are removed by Inno's uninstall log.
; Rime settings, learning, backups and downloaded models live outside {app}.
; Do not add wildcard [UninstallDelete] rules for user data or the app folder.
