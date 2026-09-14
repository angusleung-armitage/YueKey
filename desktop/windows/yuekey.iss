; YueKey per-user installer. SPDX-License-Identifier: MIT
; Build with tools/package_windows.py on Windows using Inno Setup 6.7+.
#ifndef AppVersion
  #error AppVersion is required
#endif
#ifndef RepoRoot
  #error RepoRoot is required
#endif
#ifndef AppArch
  #error AppArch is required
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
#if AppArch == "arm64"
ArchitecturesAllowed=arm64
ArchitecturesInstallIn64BitMode=arm64
MinVersion=10.0.22000
#elif AppArch == "x64"
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0.19041
#elif AppArch == "x86"
ArchitecturesAllowed=x86compatible and not arm64
; Keep the same uninstall registry view on 64-bit Windows during x86/x64 upgrades.
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0.19041
#else
  #error Unsupported AppArch
#endif
AppMutex=Local\YueKey.Companion
SetupMutex=Local\YueKey.Setup
CloseApplications=no
RestartApplications=no
UninstallDisplayIcon={app}\YueKey.exe
OutputDir={#RepoRoot}\dist
OutputBaseFilename=YueKey-{#AppVersion}-windows-{#AppArch}-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile={#RepoRoot}\desktop\icons\yuekey.ico
InfoBeforeFile={#RepoRoot}\desktop\windows\installer-info.txt

[Files]
Source: "{#RepoRoot}\build\windows-dist\YueKey\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#RepoRoot}\build\prerequisites\{#WeaselName}"; Flags: dontcopy
Source: "{#RepoRoot}\build\prerequisites\{#KeyboardName}"; Flags: dontcopy

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

[Code]
function ExistingWeaselRoot(): String;
begin
  Result := '';
  if not RegQueryStringValue(HKLM32, 'Software\Rime\Weasel', 'WeaselRoot', Result) then
    if IsWin64 then
      RegQueryStringValue(HKLM64, 'Software\Rime\Weasel', 'WeaselRoot', Result);
end;

function KeyboardIconReady(): Boolean;
var
  IconFile, Current, Key: String;
  Languages: TArrayOfString;
  View, L, Root, Count: Integer;
  Index: Cardinal;
begin
  Result := False;
  if not RegQueryStringValue(HKLM32, 'Software\YueKey\KeyboardIcon', 'IconFile', IconFile) then exit;
  if not FileExists(IconFile) then exit;
  if CompareText(GetSHA256OfFile(IconFile), '{#KeyboardResourceSHA256}') <> 0 then exit;
  Languages := ['0404', '0804', '0c04', '1004', '1404'];
  Count := 0;
  for View := 0 to 1 do begin
    if (View = 0) or IsWin64 then begin
      if View = 0 then Root := HKLM32 else Root := HKLM64;
      for L := 0 to GetArrayLength(Languages) - 1 do begin
        Key := 'Software\Microsoft\CTF\TIP\{A3F4CDED-B1E9-41EE-9CA6-7B4D0DE6CB0A}\LanguageProfile\0x0000' +
               Languages[L] + '\{3D02CAB6-2B8E-4781-BA20-1C9267529467}';
        if RegKeyExists(Root, Key) then begin
          Count := Count + 1;
          if not RegQueryStringValue(Root, Key, 'IconFile', Current) then exit;
          if CompareText(Current, IconFile) <> 0 then exit;
          if not RegQueryDWordValue(Root, Key, 'IconIndex', Index) then exit;
          if Index <> 0 then exit;
        end;
      end;
    end;
  end;
  Result := Count > 0;
end;

function PrepareKeyboardIcon(): String;
var
  Installer: String;
  ResultCode: Integer;
begin
  Result := '';
  if KeyboardIconReady() then exit;
  ExtractTemporaryFile('{#KeyboardName}');
  Installer := ExpandConstant('{tmp}\{#KeyboardName}');
  if CompareText(GetSHA256OfFile(Installer), '{#KeyboardSHA256}') <> 0 then begin
    Result := 'Keyboard icon checksum verification failed. Download YueKey again. / 鍵盤圖示安裝檔驗證失敗。';
    exit;
  end;
  if not ShellExec('runas', Installer, '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-', '',
                   SW_SHOWNORMAL, ewWaitUntilTerminated, ResultCode) then begin
    Result := 'Approve the administrator prompt to set the keyboard identifier to 中. / 請允許管理員提示以設定鍵盤識別「中」。';
    exit;
  end;
  if (ResultCode <> 0) or not KeyboardIconReady() then
    Result := 'Keyboard icon setup did not complete. Retry YueKey setup. / 鍵盤圖示設定未完成，請重試。';
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Root, Installer: String;
  ResultCode: Integer;
begin
  Result := '';
  Root := ExistingWeaselRoot();
  if Root <> '' then begin
    if not FileExists(AddBackslash(Root) + 'WeaselDeployer.exe') or
       not FileExists(AddBackslash(Root) + 'WeaselServer.exe') or
       not FileExists(AddBackslash(Root) + 'WeaselSetup.exe') or
       not FileExists(AddBackslash(Root) + 'rime.dll') then
      Result := 'The existing Weasel installation needs repair. / 現有小狼毫需要修復。'
    else
      Log('Reusing existing Weasel installation: ' + Root);
    if Result = '' then Result := PrepareKeyboardIcon();
    exit;
  end;
  ExtractTemporaryFile('{#WeaselName}');
  Installer := ExpandConstant('{tmp}\{#WeaselName}');
  if CompareText(GetSHA256OfFile(Installer), '{#WeaselSHA256}') <> 0 then begin
    Result := 'Weasel checksum verification failed. Download YueKey again. / 安裝檔驗證失敗，請重新下載。';
    exit;
  end;
  Log('Installing verified bundled Weasel prerequisite.');
  if not ShellExec('runas', Installer, '/S /T', '', SW_SHOWNORMAL, ewWaitUntilTerminated, ResultCode) then begin
    Result := 'Typing support was not installed. Retry and approve the Windows administrator prompt. / 請重試並允許 Windows 管理員提示。 ' + SysErrorMessage(ResultCode);
    exit;
  end;
  if (ResultCode <> 0) or (ExistingWeaselRoot() = '') then
    Result := 'Weasel installation did not complete. Please retry. / 小狼毫安裝未完成，請重試。'
  else Result := PrepareKeyboardIcon();
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then begin
    WizardForm.StatusLabel.Caption := 'Setting up Cantonese Quick typing... / 正在設定港式速成…';
    if not Exec(ExpandConstant('{app}\YueKey.exe'), '--setup-typing', '', SW_HIDE,
                ewWaitUntilTerminated, ResultCode) then
      RaiseException('Could not start typing setup: ' + SysErrorMessage(ResultCode));
    if ResultCode <> 0 then
      RaiseException('Typing setup needs attention. Open YueKey and choose Set up typing. Details: %LOCALAPPDATA%\YueKey\setup-report.json / 請開啟粵鍵並按「設定速成」重試。');
  end;
end;
