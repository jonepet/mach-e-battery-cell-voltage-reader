#ifndef AppVersion
  #error Pass the version on the command line: ISCC /DAppVersion=1.2.3 mache-cells.iss
#endif

#define AppName "Mach-E Cell Voltage Reader"

[Setup]
AppId={{136E3C66-4D84-43F9-A143-495CB34D8EE9}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=build\installer
OutputBaseFilename=MacheCellVoltageReader-{#AppVersion}-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "build\pyinstaller\dist\MacheCells\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\MacheCells.exe"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\MacheCells.exe"; Description: "Start {#AppName}"; Flags: nowait postinstall skipifsilent
