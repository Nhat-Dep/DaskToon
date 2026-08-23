; -- DaskToon Official Windows Installer Script --

#define MyAppName "DaskToon"
#define MyAppVersion "5.2.0"
#define MyAppPublisher "DaskToon Team"
#define MyAppURL "https://dasktoon.org"
#define MyAppExeName "DaskToon-launcher.exe"
#define MyAppConsoleExeName "DaskToon.exe"
#define SourceDir "D:\build_windows_x64_vc17_Release\bin\Release"
#define IconFile "d:\DaskToon\release\windows\icons\winblender.ico"

[Setup]
; Unique AppId for DaskToon
AppId={{D45A700N-A719-4A9B-89E2-6C91E5B42D1A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion} (Anime Engine)
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=d:\DaskToon\release\dist
OutputBaseFilename=DaskToon-5.2.0-Windows-Setup
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=auto
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; All Release Binaries & Datafiles
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu Shortcuts
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Comment: "DaskToon Anime Production Suite"
Name: "{group}\{#MyAppName} (Command Line)"; Filename: "{app}\{#MyAppConsoleExeName}"; IconFilename: "{app}\{#MyAppConsoleExeName}"; Comment: "DaskToon Console Mode"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
; Desktop Shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "DaskToon Anime Production Suite"

[Run]
; Option to launch DaskToon after installation finishes
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
