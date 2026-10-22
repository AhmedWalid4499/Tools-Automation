; GOLD Express setup wizard (Inno Setup 6). Built by build_release.py, which passes
; AppVersion, AppPublisher and AppSource (the PyInstaller app folder) on the command line.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef AppPublisher
  #define AppPublisher "GOLD Express"
#endif
#ifndef AppCopyright
  #define AppCopyright "Copyright (c) 2026 Ahmed El-Bourgy. All rights reserved."
#endif
#ifndef AppAuthor
  #define AppAuthor "Ahmed El-Bourgy"
#endif
#define AppName "GOLD Express"
#define AppExe "GOLD Express.exe"

[Setup]
; Never change AppId: it is how Windows recognises upgrades of the same app.
AppId={{829A9F21-FCD3-42DA-9E42-DF093674F3F9}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppCopyright={#AppCopyright}
VersionInfoCopyright={#AppCopyright}
VersionInfoCompany={#AppAuthor}
AppComments=Order overview with delivery status, look up GOLD orders, screenshots, documents, teams, Excel exports, bulk Revised Target Dates and bulk STM assignment.
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoDescription={#AppName} Setup
; Per-user install: no administrator rights needed ({autopf} = %LOCALAPPDATA%\Programs).
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableWelcomePage=no
InfoBeforeFile=before_install.txt
OutputBaseFilename=GOLD_Express_Setup_{#AppVersion}
SetupIconFile=..\gold_express.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
WizardStyle=modern
WizardSizePercent=110
WizardImageFile=wizard_large_100.bmp,wizard_large_125.bmp,wizard_large_150.bmp,wizard_large_200.bmp,wizard_large_250.bmp
WizardSmallImageFile=wizard_small_100.bmp,wizard_small_125.bmp,wizard_small_150.bmp,wizard_small_200.bmp,wizard_small_250.bmp
WizardImageStretch=no
Compression=lzma2/ultra64
SolidCompression=yes
; Close a running GOLD Express before upgrading it.
CloseApplications=yes
RestartApplications=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
WelcomeLabel1=Welcome to GOLD Express
WelcomeLabel2=This will install [name/ver] on your computer.%n%nGOLD Express gives you an overview of GOLD orders with their delivery status, looks up orders, takes screenshots, downloads order documents, shows order teams, exports tab data to Excel, and adds Revised Target Dates and assigns the STM on many orders at once.%n%nGOLD runs in Firefox in the background - no extra sign-in needed.%n%nCreated by {#AppAuthor}.%n{#AppCopyright}
FinishedHeadingLabel=GOLD Express is ready
FinishedLabel=GOLD Express has been installed. You can start it from the Start menu or the desktop shortcut.%n%n{#AppCopyright}

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "{#AppSource}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; Remove files of the previous version before copying the new one.
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
; AppUserModelID: lets GOLD Express show Windows notifications under its own name (gold_notify.py)
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; Comment: "GOLD order assistant"; AppUserModelID: "AhmedElBourgy.GOLDExpress"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon; Comment: "GOLD order assistant"

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
; In-app updates run this setup silently: start the updated app again afterwards.
Filename: "{app}\{#AppExe}"; Flags: nowait; Check: WizardSilent

[Code]
function FirefoxInstalled(): Boolean;
var
  Path: String;
begin
  Result :=
    FileExists(ExpandConstant('{commonpf64}\Mozilla Firefox\firefox.exe')) or
    FileExists(ExpandConstant('{commonpf32}\Mozilla Firefox\firefox.exe')) or
    FileExists(ExpandConstant('{localappdata}\Mozilla Firefox\firefox.exe')) or
    RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\firefox.exe', '', Path) or
    RegQueryStringValue(HKCU, 'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\firefox.exe', '', Path);
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  if not FirefoxInstalled() and not WizardSilent() then
    Result := MsgBox('Mozilla Firefox was not found on this computer.' + #13#10 + #13#10 +
      'GOLD Express uses Firefox to work with GOLD. Please install Firefox ' +
      '(from the Company Portal / Software Center) before using GOLD Express.' + #13#10 + #13#10 +
      'Continue installing anyway?', mbConfirmation, MB_YESNO) = IDYES;
end;
