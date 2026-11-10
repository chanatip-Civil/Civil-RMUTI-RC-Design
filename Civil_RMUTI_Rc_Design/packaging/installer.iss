; Inno Setup script for Civil RMUTI Rc Design (Inno Setup 6.x).
; Built by packaging\build_installer.bat, which passes /DAppVersion=x.y.z.
;
; Never change AppId: Windows uses it to recognise upgrades and uninstall.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "Civil RMUTI Rc Design"
#define AppExe "CivilRMUTIRcDesign.exe"
#define AppPublisher "RMUTI Civil Engineering"
#define SourceDir "..\dist\CivilRMUTIRcDesign"

[Setup]
AppId={{09F93DD0-FEDF-4FF6-A16D-6450A6956E16}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; Lets a user without administrator rights install for themselves only.
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist_installer
OutputBaseFilename=CivilRMUTIRcDesign_Setup_{#AppVersion}
SetupIconFile=build\app.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ChangesAssociations=yes
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "fileassoc"; Description: "Open .rcproj project files with {#AppName}"; GroupDescription: "File types:"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; .rcproj -> Civil RMUTI Rc Design (HKA = per-machine or per-user, matching the install mode)
Root: HKA; Subkey: "Software\Classes\.rcproj"; ValueType: string; ValueName: ""; ValueData: "CivilRMUTIRcDesign.Project"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\CivilRMUTIRcDesign.Project"; ValueType: string; ValueName: ""; ValueData: "{#AppName} Project"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\CivilRMUTIRcDesign.Project\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExe},0"; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\CivilRMUTIRcDesign.Project\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: fileassoc

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

; User data (settings, material library, logs) lives in %USERPROFILE%\.civil_rmuti_rc_design
; and is intentionally kept on uninstall so projects and materials are not lost.
