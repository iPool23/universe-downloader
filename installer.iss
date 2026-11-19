; Instalador de Universe Downloader (Inno Setup 6). Lo compila build.ps1:
;   ISCC.exe installer.iss /DMyAppVersion=3.0.0 /DSourceDir=build_out\UniverseDownloader
; Instala por usuario (sin administrador) en %LOCALAPPDATA%\Programs\UniverseDownloader, con acceso
; directo en el escritorio (opcional), menú Inicio y desinstalador en "Aplicaciones instaladas".

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "build_out\UniverseDownloader"
#endif
#define MyAppName "Universe Downloader"
#define MyAppExe "UniverseDownloader.exe"
; mismo AppUserModelID que declara la app (src/version.py): la barra de tareas agrupa y permite anclar
#define MyAppId "iPool23.UniverseDownloader"
; el actualizador busca este nombre en la release (src/services/updater.py): no cambiarlo
#define MyOutputName "UniverseDownloader-Setup-" + MyAppVersion

[Setup]
; El AppId no se cambia nunca: es lo que hace que una versión nueva actualice la instalada en su lugar.
AppId={{FB130D6B-937F-4036-A6C7-9487443297F6}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=Pool Deza
AppPublisherURL=https://github.com/iPool23/universe-downloader
AppSupportURL=https://github.com/iPool23/universe-downloader/issues
AppUpdatesURL=https://github.com/iPool23/universe-downloader/releases
DefaultDirName={localappdata}\Programs\UniverseDownloader
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=dist
OutputBaseFilename={#MyOutputName}
SetupIconFile=public\imgs\favicon.ico
UninstallDisplayIcon={app}\{#MyAppExe}
UninstallDisplayName={#MyAppName}
WizardStyle=modern
; build.ps1 -Fast: compresión rápida para probar el instalador (sale más grande; no es para publicar)
#ifdef Fast
Compression=lzma2/fast
#else
Compression=lzma2/ultra64
#endif
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=4
; Si la app está abierta, la cierra antes de copiar. La app que lanza su propia actualización ya se
; cierra sola y el .cmd del actualizador la reabre, así que aquí no se reinicia nada.
CloseApplications=yes
RestartApplications=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; limpia restos de la versión anterior (módulos que ya no se usan, yt-dlp viejo, etc.)
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"; AppUserModelID: "{#MyAppId}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"; Tasks: desktopicon; AppUserModelID: "{#MyAppId}"

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
; NO se borra %LOCALAPPDATA%\UniverseDownloader (registro y archivos de trabajo): lo que el usuario
; guardó con «Guardar como» está donde él lo puso.

[Messages]
spanish.BeveledLabel=Universe Downloader
