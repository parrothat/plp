[Setup]
AppName=Pars Local Player
AppVersion=2.1.0
AppVerName=Pars Local Player 2.1.0
AppPublisher=ParrotHat Foundation
AppPublisherURL=https://parrothat.com
AppSupportURL=https://parrothat.com/support
AppUpdatesURL=https://parrothat.com/plp/download

DefaultDirName={pf}\Pars Local Player
DefaultGroupName=Pars Local Player

OutputDir=dist
OutputBaseFilename=plp-2.1.0-installer-x64

SetupIconFile=plp_logo.ico
WizardImageFile=plp_logo.bmp

Compression=lzma
SolidCompression=yes

VersionInfoVersion=2.1.0.0
VersionInfoCompany=ParrotHat Foundation
VersionInfoDescription=Pars Local Player Installer
VersionInfoTextVersion=2.1.0
VersionInfoProductName=Pars Local Player

WizardStyle=modern

LicenseFile=LICENSE.txt
InfoBeforeFile=README.txt

PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

ShowLanguageDialog=yes
DisableProgramGroupPage=no
UsePreviousAppDir=yes

UninstallDisplayIcon={app}\plp2.1.exe

; ================= LANGUAGES =================

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "slovak"; MessagesFile: "compiler:Languages\Slovak.isl"

; ================= TASKS =================

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startmenuicon"; Description: "Create Start Menu shortcut"; GroupDescription: "{cm:AdditionalIcons}"

; ================= FILES =================

[Files]
Source: "dist\plp2.1.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "plp_logo.ico"; DestDir: "{app}"; Flags: ignoreversion

; ================= ICONS =================

[Icons]
Name: "{group}\Pars Local Player"; Filename: "{app}\plp2.1.exe"; Tasks: startmenuicon
Name: "{commondesktop}\Pars Local Player"; Filename: "{app}\plp2.1.exe"; Tasks: desktopicon

; ================= RUN =================

[Run]
Filename: "{app}\plp2.1.exe"; Description: "{cm:LaunchProgram,Pars Local Player}"; Flags: nowait postinstall skipifsilent
