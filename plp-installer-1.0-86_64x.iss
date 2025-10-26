[Setup]
AppName=Pars Local Player
AppVersion=2.2
AppPublisher=ParrotHat Foundation
AppPublisherURL=https://parrothat.com/plp
AppSupportURL=https://parrothat.com/support
AppUpdatesURL=https://parrothat.com/plp/download
DefaultDirName={pf}\Pars Local Player
DefaultGroupName=Pars Local Player
OutputDir=dist
OutputBaseFilename=PLP_2.2_Setup
SetupIconFile=plp.ico
Compression=lzma
SolidCompression=yes

[Languages]
Name: "slovak"; MessagesFile: "compiler:Languages\Slovak.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\plp2.2.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\*"; DestDir: "{app}\assets"; Flags: recursesubdirs

[Icons]
Name: "{group}\Pars Local Player"; Filename: "{app}\plp2.2.exe"
Name: "{commondesktop}\Pars Local Player"; Filename: "{app}\plp2.2.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\plp2.2.exe"; Description: "{cm:LaunchProgram,Pars Local Player}"; Flags: nowait postinstall skipifsilent
