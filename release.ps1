# Publica una versión: compila el instalador, genera SHA256SUMS.txt, etiqueta el código y sube
# la release a GitHub. Las apps instaladas la detectan solas (aviso «Hay una versión nueva»).
#   powershell -ExecutionPolicy Bypass -File release.ps1 [-Notes "qué cambió"] [-SkipBuild] [-SkipMac]
# Antes: subir APP_VERSION en src\version.py y hacer commit en la rama desktop (el script la sube).
# La app de escritorio se publica desde la rama desktop: main es la web y cada push ahí la despliega
# a producción, así que este script nunca toca main.
# Requisitos: gh auth login, Inno Setup 6.
# La release lleva el instalador de Windows, el zip de Mac y SHA256SUMS.txt con los dos. El zip lo
# compila y prueba GitHub Actions (.github/workflows/mac.yml) con cada push a desktop: el script
# espera la compilación de este mismo commit y solo publica si pasó. -SkipMac publica solo Windows.
param([string]$Notes = "", [switch]$SkipBuild, [switch]$SkipMac)
# "Continue": en PowerShell 5 cualquier mensaje de git/gh por stderr sería un error fatal con "Stop";
# los fallos se comprueban con $LASTEXITCODE.
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
$repo = "iPool23/universe-downloader"
$branch = "desktop"
$version = (Select-String -Path src\version.py -Pattern 'APP_VERSION = "([^"]+)"').Matches[0].Groups[1].Value
$tag = "v$version"

if (git status --porcelain) { throw "Hay cambios sin confirmar: haz commit y push antes de publicar $tag" }
# Sube una rama o etiqueta con la sesión de gh como credencial, solo para ese comando: el almacén de
# credenciales de Windows puede tener guardada otra cuenta de GitHub y el push daría 403.
function Push-Origin($ref) {
    git -c credential.helper= -c "credential.helper=!gh auth git-credential" push -q origin $ref
}

if ((git branch --show-current) -ne $branch) { throw "Estás en otra rama: la app de escritorio se publica desde $branch" }
Push-Origin $branch   # commits pendientes de desktop; main no se toca nunca
if ($LASTEXITCODE -ne 0) { throw "no se pudo subir la rama $branch" }
git fetch -q origin
if ((git rev-parse HEAD) -ne (git rev-parse "origin/$branch")) { throw "HEAD no coincide con origin/${branch}: revisa la rama antes de publicar $tag" }

if (-not $SkipBuild) {
    Write-Host "== Compilando..."
    powershell -ExecutionPolicy Bypass -File build.ps1
    if ($LASTEXITCODE -ne 0) { throw "build falló" }
}
$setup = "dist\UniverseDownloader-Setup-$version.exe"
if (-not (Test-Path $setup)) { throw "Falta $setup" }
$files = @($setup)

function Get-MacZip {
    $sha = git rev-parse HEAD
    $zip = "dist\UniverseDownloader-$version-mac-arm64.zip"
    Remove-Item $zip -ErrorAction SilentlyContinue
    $deadline = (Get-Date).AddMinutes(45)
    while ($true) {
        $runs = ((gh run list --repo $repo --workflow mac.yml --branch $branch --limit 20 --json databaseId,headSha,status,conclusion) -join "`n") | ConvertFrom-Json
        $run = $runs | Where-Object { $_.headSha -eq $sha } | Select-Object -First 1
        if ($run -and $run.status -eq "completed") { break }
        if ((Get-Date) -gt $deadline) { throw "la compilación de Mac del commit $sha no terminó a tiempo" }
        $state = if ($run) { $run.status } else { "sin empezar" }
        Write-Host "   esperando la compilación de Mac ($state)..."
        Start-Sleep -Seconds 30
    }
    if ($run.conclusion -ne "success") {
        throw "la compilación de Mac falló: https://github.com/$repo/actions/runs/$($run.databaseId) (con -SkipMac se publica solo Windows)"
    }
    gh run download $run.databaseId --repo $repo --name UniverseDownloader-mac-arm64 --dir dist | Out-Host
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $zip)) { throw "no se pudo bajar $zip de la compilación de Mac" }
    return $zip
}

if (-not $SkipMac) {
    Write-Host "== Mac (GitHub Actions)"
    $files += Get-MacZip
}

Write-Host "== SHA256SUMS.txt"
$lines = $files | ForEach-Object { "{0}  {1}" -f (Get-FileHash $_ -Algorithm SHA256).Hash.ToLower(), (Split-Path $_ -Leaf) }
[IO.File]::WriteAllText((Join-Path $PSScriptRoot "dist\SHA256SUMS.txt"), ($lines -join "`n") + "`n")
$lines

if (-not $Notes) {
    $last = git tag --list "v*" --sort=-v:refname | Where-Object { $_ -ne $tag } | Select-Object -First 1
    $range = if ($last) { "$last..HEAD" } else { "HEAD" }
    $Notes = (git log $range --pretty=format:"- %s" | Where-Object { $_ -notmatch "^- (Merge|wip)" }) -join "`n"
    if (-not $Notes) { $Notes = "Versión $version" }
}
$notesFile = Join-Path $env:TEMP "universe-downloader-release-notes.md"
$downloads = "**UniverseDownloader-Setup-$version.exe**: Windows 10/11, sin administrador."
if (-not $SkipMac) { $downloads += "`n`n**UniverseDownloader-$version-mac-arm64.zip**: Mac con chip Apple (M1 o posterior), macOS 13 o más nuevo." }
[IO.File]::WriteAllText($notesFile, "## Universe Downloader $version`n`n$Notes`n`n$downloads`n`nLas versiones instaladas se actualizan solas desde la app.`n")

Write-Host "== Etiqueta $tag"
if (-not (git tag --list $tag)) {
    git tag -a $tag -m "Universe Downloader $version"
    Push-Origin $tag
    if ($LASTEXITCODE -ne 0) { throw "no se pudo subir la etiqueta $tag" }
}

Write-Host "== Release $tag en $repo"
$existing = @(gh release list --repo $repo --json tagName --jq ".[].tagName" 2>$null)
if ($existing -contains $tag) {
    # la release ya existe (se repite la publicación): se reemplazan sus archivos
    gh release upload $tag --repo $repo --clobber @files dist\SHA256SUMS.txt
} else {
    gh release create $tag --repo $repo --title "Universe Downloader $version" --notes-file $notesFile @files dist\SHA256SUMS.txt
}
if ($LASTEXITCODE -ne 0) { throw "gh release falló" }
gh release view $tag --repo $repo --json url --jq ".url"
gh release view $tag --repo $repo --json assets --jq ".assets[] | .name"
Write-Host "== Listo. Las apps instaladas verán la versión $version al abrirse (o con «Versión…» en la barra lateral)."
