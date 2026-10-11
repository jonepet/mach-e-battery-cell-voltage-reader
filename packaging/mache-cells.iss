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

[Tasks]
Name: "autostart"; Description: "Start the reader when I log on to Windows"; GroupDescription: "Startup:"; Flags: unchecked
Name: "network"; Description: "Allow other devices on my network to open the reader"; GroupDescription: "Network access (the reader has no login and no encryption: use this only on a trusted home network):"; Flags: unchecked

[InstallDelete]
Type: files; Name: "{app}\network-access.enabled"

[Files]
Source: "build\pyinstaller\dist\MacheCells\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "network-access.enabled"; DestDir: "{app}"; Flags: ignoreversion; Tasks: network

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\MacheCells.exe"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{userstartup}\{#AppName}"; Filename: "{app}\MacheCells.exe"; Tasks: autostart

[Run]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#AppName}"""; Flags: runhidden; Check: IsAdminInstallMode
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""{#AppName}"" dir=in action=allow program=""{app}\MacheCells.exe"" profile=private remoteip=localsubnet enable=yes"; Flags: runhidden; Tasks: network; Check: IsAdminInstallMode
Filename: "{app}\MacheCells.exe"; Description: "Start {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#AppName}"""; Flags: runhidden; RunOnceId: "RemoveFirewallRule"; Check: IsAdminInstallMode
