; Shared Windows input-indicator branding. No Weasel binaries are modified.
; SPDX-License-Identifier: MIT
[Setup]
AppId=YueKey.KeyboardIcon
AppName=YueKey Keyboard Icon
AppVersion=1
AppPublisher=YueKey contributors
DefaultDirName={commoncf32}\YueKey\KeyboardIcon
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=admin
MinVersion=10.0.19041
OutputDir={#RepoRoot}\build\prerequisites
OutputBaseFilename=yuekey-keyboard-icon-installer
SetupIconFile={#RepoRoot}\desktop\icons\yuekey.ico
UninstallDisplayIcon={app}\YueKeyKeyboard.dll
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupMutex=Global\YueKey.KeyboardIcon.Setup
Uninstallable=yes

[Files]
; Retain until references have been restored, including externally edited ones.
Source: "{#RepoRoot}\build\windows-data\YueKeyKeyboard.dll"; DestDir: "{app}"; Flags: ignoreversion uninsneveruninstall

[Code]
const
  StateKey = 'Software\YueKey\KeyboardIcon';
  TipBase = 'Software\Microsoft\CTF\TIP\{A3F4CDED-B1E9-41EE-9CA6-7B4D0DE6CB0A}\LanguageProfile\0x0000';
  TipGuid = '\{3D02CAB6-2B8E-4781-BA20-1C9267529467}';

type
  TIconValues = record
    FileKind, IndexKind, IconIndex: Cardinal;
    IconFile: String;
  end;
  TProfile = record
    Root: Integer;
    Key, Backup: String;
    Before: TIconValues;
  end;

var
  Profiles: array of TProfile;
  KeepResource: Boolean;

function RegGetValue(Root: LongWord; Subkey, Name: String; Flags: LongWord;
  var Kind: LongWord; Data: LongWord; var Size: LongWord): LongWord;
  external 'RegGetValueW@advapi32.dll stdcall';

procedure Require(OK: Boolean; const Message: String);
begin
  if not OK then RaiseException(Message);
end;

function ValueKind(Root: Integer; const Key, Name: String): Cardinal;
var
  Flags, Size, Error: Cardinal;
begin
  Flags := $1000FFFF; { RRF_NOEXPAND | RRF_RT_ANY }
  if Root = HKLM64 then Flags := Flags or $10000
  else Flags := Flags or $20000;
  Result := 0;
  Size := 0;
  Error := RegGetValue($80000002, Key, Name, Flags, Result, 0, Size);
  if Error = 2 then Result := 0
  else Require(Error = 0, 'Cannot read keyboard icon registration: ' + IntToStr(Error));
end;

function ReadIcon(Root: Integer; const Key: String): TIconValues;
begin
  Result.IconFile := '';
  Result.IconIndex := 0;
  Result.FileKind := ValueKind(Root, Key, 'IconFile');
  Result.IndexKind := ValueKind(Root, Key, 'IconIndex');
  Require((Result.FileKind = 0) or (Result.FileKind = 1) or (Result.FileKind = 2),
    'Unexpected IconFile type; leaving the keyboard registration unchanged.');
  Require((Result.IndexKind = 0) or (Result.IndexKind = 4),
    'Unexpected IconIndex type; leaving the keyboard registration unchanged.');
  if Result.FileKind <> 0 then
    Require(RegQueryStringValue(Root, Key, 'IconFile', Result.IconFile), 'Cannot read IconFile.');
  if Result.IndexKind <> 0 then
    Require(RegQueryDWordValue(Root, Key, 'IconIndex', Result.IconIndex), 'Cannot read IconIndex.');
end;

procedure WriteIcon(Root: Integer; const Key: String; Values: TIconValues);
begin
  { RegWriteStringValue preserves an existing REG_EXPAND_SZ value's type.
    Delete only when the requested type differs, so restore is exact. }
  if (Values.FileKind <> 0) and RegValueExists(Root, Key, 'IconFile') and
      (ValueKind(Root, Key, 'IconFile') <> Values.FileKind) then
    Require(RegDeleteValue(Root, Key, 'IconFile'), 'Cannot update IconFile type.');
  case Values.FileKind of
    0: if RegValueExists(Root, Key, 'IconFile') then
         Require(RegDeleteValue(Root, Key, 'IconFile'), 'Cannot restore missing IconFile.');
    1: Require(RegWriteStringValue(Root, Key, 'IconFile', Values.IconFile), 'Cannot write IconFile.');
    2: Require(RegWriteExpandStringValue(Root, Key, 'IconFile', Values.IconFile), 'Cannot write IconFile.');
  else RaiseException('Invalid icon backup.');
  end;
  if Values.IndexKind = 0 then begin
    if RegValueExists(Root, Key, 'IconIndex') then
      Require(RegDeleteValue(Root, Key, 'IconIndex'), 'Cannot restore missing IconIndex.');
  end else if Values.IndexKind = 4 then
    Require(RegWriteDWordValue(Root, Key, 'IconIndex', Values.IconIndex), 'Cannot write IconIndex.')
  else RaiseException('Invalid index backup.');
end;

function LoadBackup(const Key: String): TIconValues;
var
  Format: Cardinal;
begin
  Require(RegQueryDWordValue(HKLM32, Key, 'Format', Format) and (Format = 1), 'Missing keyboard icon backup.');
  Require(RegQueryDWordValue(HKLM32, Key, 'FileKind', Result.FileKind), 'Invalid icon backup.');
  Require(RegQueryDWordValue(HKLM32, Key, 'IndexKind', Result.IndexKind), 'Invalid icon backup.');
  Require(RegQueryStringValue(HKLM32, Key, 'IconFile', Result.IconFile), 'Invalid icon backup.');
  Require(RegQueryDWordValue(HKLM32, Key, 'IconIndex', Result.IconIndex), 'Invalid icon backup.');
  Require(((Result.FileKind = 0) or (Result.FileKind = 1) or (Result.FileKind = 2)) and
          ((Result.IndexKind = 0) or (Result.IndexKind = 4)), 'Invalid icon backup types.');
end;

procedure SaveBackup(Profile: TProfile);
var
  Existing: TIconValues;
begin
  if RegValueExists(HKLM32, Profile.Backup, 'Format') then begin
    Existing := LoadBackup(Profile.Backup);
    exit;
  end;
  Require(CompareText(Profile.Before.IconFile, ExpandConstant('{app}\YueKeyKeyboard.dll')) <> 0,
    'The previous keyboard icon backup is missing. Restore it before repairing this component.');
  Require(RegWriteDWordValue(HKLM32, Profile.Backup, 'FileKind', Profile.Before.FileKind) and
    RegWriteDWordValue(HKLM32, Profile.Backup, 'IndexKind', Profile.Before.IndexKind) and
    RegWriteStringValue(HKLM32, Profile.Backup, 'IconFile', Profile.Before.IconFile) and
    RegWriteDWordValue(HKLM32, Profile.Backup, 'IconIndex', Profile.Before.IconIndex) and
    RegWriteDWordValue(HKLM32, Profile.Backup, 'Format', 1), 'Could not back up keyboard icon registration.');
end;

procedure FindProfiles();
var
  Languages: TArrayOfString;
  View, L, N, Root: Integer;
  Key: String;
begin
  Languages := ['0404', '0804', '0c04', '1004', '1404'];
  SetArrayLength(Profiles, 0);
  for View := 0 to 1 do begin
    if (View = 0) or IsWin64 then begin
      if View = 0 then Root := HKLM32 else Root := HKLM64;
      for L := 0 to GetArrayLength(Languages) - 1 do begin
        Key := TipBase + Languages[L] + TipGuid;
        if RegKeyExists(Root, Key) then begin
          N := GetArrayLength(Profiles);
          SetArrayLength(Profiles, N + 1);
          Profiles[N].Root := Root;
          Profiles[N].Key := Key;
          Profiles[N].Backup := StateKey + '\Backup\' + IntToStr(View) + '\' + Languages[L];
          Profiles[N].Before := ReadIcon(Root, Key);
        end;
      end;
    end;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  I: Integer;
begin
  Result := '';
  try
    FindProfiles();
    Require(GetArrayLength(Profiles) > 0, 'Install Weasel before the YueKey keyboard icon.');
    for I := 0 to GetArrayLength(Profiles) - 1 do SaveBackup(Profiles[I]);
  except
    Result := GetExceptionMessage();
  end;
end;

procedure NotifyKeyboardChange();
begin
  SendBroadcastNotifyMessage($001A, 0, 0); { WM_SETTINGCHANGE, no Explorer restart }
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  I, J: Integer;
  Values: TIconValues;
begin
  if CurStep <> ssPostInstall then exit;
  Values.FileKind := 1;
  Values.IndexKind := 4;
  Values.IconIndex := 0;
  Values.IconFile := ExpandConstant('{app}\YueKeyKeyboard.dll');
  Require(CompareText(GetSHA256OfFile(Values.IconFile), '{#ResourceSHA256}') = 0, 'Keyboard icon checksum mismatch.');
  I := 0;
  try
    for I := 0 to GetArrayLength(Profiles) - 1 do
      WriteIcon(Profiles[I].Root, Profiles[I].Key, Values);
    Require(RegWriteStringValue(HKLM32, StateKey, 'IconFile', Values.IconFile) and
      RegWriteStringValue(HKLM32, StateKey, 'SHA256', '{#ResourceSHA256}'), 'Could not record keyboard icon installation.');
  except
    for J := 0 to GetArrayLength(Profiles) - 1 do
      WriteIcon(Profiles[J].Root, Profiles[J].Key, Profiles[J].Before);
    RaiseException(GetExceptionMessage());
  end;
  NotifyKeyboardChange();
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  I: Integer;
  Current, Original: TIconValues;
begin
  if CurUninstallStep = usUninstall then begin
    KeepResource := False;
    FindProfiles();
    { Validate every needed backup before restoring any registration. }
    for I := 0 to GetArrayLength(Profiles) - 1 do begin
      Current := Profiles[I].Before;
      if CompareText(Current.IconFile, ExpandConstant('{app}\YueKeyKeyboard.dll')) = 0 then begin
        if (Current.FileKind = 1) and (Current.IndexKind = 4) and (Current.IconIndex = 0) then
          Original := LoadBackup(Profiles[I].Backup)
        else KeepResource := True;
      end;
    end;
    for I := 0 to GetArrayLength(Profiles) - 1 do begin
      Current := Profiles[I].Before;
      if (CompareText(Current.IconFile, ExpandConstant('{app}\YueKeyKeyboard.dll')) = 0) and
          (Current.FileKind = 1) and (Current.IndexKind = 4) and (Current.IconIndex = 0) then
        WriteIcon(Profiles[I].Root, Profiles[I].Key, LoadBackup(Profiles[I].Backup));
    end;
    NotifyKeyboardChange();
  end;
  if CurUninstallStep = usPostUninstall then begin
    if not KeepResource then begin
      DeleteFile(ExpandConstant('{app}\YueKeyKeyboard.dll'));
      RegDeleteKeyIncludingSubkeys(HKLM32, StateKey);
    end;
    RemoveDir(ExpandConstant('{app}'));
  end;
end;
