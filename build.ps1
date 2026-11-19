# Compila UniverseDownloader.exe, lo comprueba y arma el instalador (Inno Setup).
#   powershell -ExecutionPolicy Bypass -File build.ps1   -> dist\UniverseDownloader-Setup-<ver>.exe
#   -Full:    incluye las funciones de IA (quitar fondo, outpaint). Por defecto se compila la edición
#             ligera, que es la que se publica: las de IA pesan varios GB.
#   -Install: además instala el resultado en esta PC (silencioso).
#   -Fast:    compresión rápida del instalador, para probar (sale más grande; no es para publicar).
# El instalador es por usuario (sin administrador): %LOCALAPPDATA%\Programs\UniverseDownloader, accesos
# directos en escritorio y menú Inicio, y desinstalador en "Aplicaciones instaladas".
# La versión sale de APP_VERSION en src\version.py.
param([switch]$Full, [switch]$Install, [switch]$Fast)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$version = (Select-String -Path src\version.py -Pattern 'APP_VERSION = "([^"]+)"').Matches[0].Groups[1].Value
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
          "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Falta Inno Setup 6: winget install JRSoftware.InnoSetup" }
if (-not (Test-Path public\imgs\favicon.ico)) { throw "Falta public\imgs\favicon.ico" }

function Self-Test($exe) {
    $f = Join-Path $env:LOCALAPPDATA "UniverseDownloader\selftest.txt"
    if (Test-Path $f) { [IO.File]::Delete($f) }
    $p = Start-Process $exe -ArgumentList "--selftest" -PassThru
    if (-not $p.WaitForExit(180000)) { $p.Kill(); throw "La autocomprobación no terminó: $exe" }
    if (-not (Test-Path $f)) { throw "La app no escribió su autocomprobación: $exe" }
    $st = Get-Content $f -Encoding utf8
    $st | ForEach-Object { Write-Host "   $_" }
    if (-not ($st -join " " | Select-String -Quiet "Listo")) { throw "La app no arrancó bien: $exe" }
}

Write-Host "1/4 Herramientas que van dentro de la app (FFmpeg y deno)..."
if (-not ((Test-Path bin\ffmpeg.exe) -and (Test-Path bin\ffprobe.exe))) {
    python scripts\setup_ffmpeg.py
    if (-not (Test-Path bin\ffmpeg.exe)) { throw "No se pudo obtener FFmpeg (scripts\setup_ffmpeg.py)" }
}
if (-not (Test-Path bin\deno.exe)) {
    python scripts\setup_deno.py
    if (-not (Test-Path bin\deno.exe)) { Write-Host "   (sin deno: YouTube solo funcionará en PCs que tengan Node instalado)" }
}

$out = "build_out"
if ($Full) { Remove-Item Env:UNIVERSE_LITE_BUILD -ErrorAction SilentlyContinue; $edition = "completa (con IA)" }
else { $env:UNIVERSE_LITE_BUILD = "1"; $edition = "ligera" }
Write-Host "2/4 Compilando la versión $version, edición $edition..."
$ErrorActionPreference = "Continue"   # PyInstaller escribe su progreso por stderr
python -m PyInstaller youtubedpl.spec --noconfirm --distpath $out --workpath "${out}_tmp" 2>&1 |
    Out-File -Encoding utf8 "${out}_pyinstaller.log"
$code = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($code -ne 0) { Get-Content "${out}_pyinstaller.log" -Tail 30; throw "PyInstaller falló ($code): ver ${out}_pyinstaller.log" }
$exe = Join-Path $PSScriptRoot "$out\UniverseDownloader\UniverseDownloader.exe"
if (-not (Test-Path $exe)) { throw "No se generó $exe" }

Write-Host "3/4 Comprobando que la app compilada arranca..."
Self-Test $exe

Write-Host "4/4 Armando el instalador..."
New-Item -ItemType Directory -Force dist | Out-Null
$isccArgs = @("installer.iss", "/Qp", "/DMyAppVersion=$version", "/DSourceDir=$out\UniverseDownloader")
if ($Fast) { $isccArgs += "/DFast" }
& $iscc @isccArgs
if ($LASTEXITCODE -ne 0) { throw "Inno Setup falló ($LASTEXITCODE)" }
$setup = Get-Item "dist\UniverseDownloader-Setup-$version.exe"
Write-Host "Instalador: $($setup.FullName) ($([math]::Round($setup.Length / 1MB)) MB)"

if (-not $Install) { exit 0 }
if (Get-Process UniverseDownloader -ErrorAction SilentlyContinue) {
    Write-Host "Universe Downloader está abierto: ciérralo y ejecuta $($setup.FullName), o deja que la app se actualice sola."
    exit 0
}
Write-Host "Instalando en esta PC (silencioso)..."
$p = Start-Process $setup.FullName -ArgumentList "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /CLOSEAPPLICATIONS /MERGETASKS=desktopicon" -PassThru -Wait
if ($p.ExitCode -ne 0) { throw "El instalador devolvió $($p.ExitCode)" }
$installed = Join-Path $env:LOCALAPPDATA "Programs\UniverseDownloader\UniverseDownloader.exe"
Self-Test $installed
Write-Host "Listo: $installed"
