; GrabIt Downloader — Windows kurulum sihirbazı (Inno Setup 6)
; Derleme: ISCC.exe /DAppVersion=1.2.0 build\windows-setup.iss  → out\GrabIt-Downloader-Setup.exe
; Yönetici izni istemez; kullanıcının kendi Programlar klasörüne kurar.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "GrabIt Downloader"

[Setup]
AppId={{FD725B89-EF2A-44AC-9F8D-E767A7E299FD}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Hakan Toplu
AppPublisherURL=https://github.com/hakantoplu34/grabit-downloader
AppSupportURL=https://github.com/hakantoplu34/grabit-downloader
AppCopyright=© 2026 Hakan Toplu
DefaultDirName={localappdata}\Programs\{#AppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
OutputDir=..\out
OutputBaseFilename=GrabIt-Downloader-Setup
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\icon.ico
UninstallDisplayName={#AppName}
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
CloseApplications=yes

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\src\*"; DestDir: "{app}"; Excludes: "*.command,__pycache__\*,.venv\*"; Flags: recursesubdirs ignoreversion
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\GrabIt-Baslat.bat"; WorkingDir: "{app}"; IconFilename: "{app}\icon.ico"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\GrabIt-Baslat.bat"; WorkingDir: "{app}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\GrabIt-Baslat.bat"; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: postinstall nowait skipifsilent shellexec

[UninstallDelete]
; İlk açılışta oluşturulan Python ortamı
Type: filesandordirs; Name: "{app}\.venv"
