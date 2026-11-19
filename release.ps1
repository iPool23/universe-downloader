# Publica una versión: compila el instalador, genera SHA256SUMS.txt, etiqueta el código y sube
# la release a GitHub. Las apps instaladas la detectan solas (aviso «Hay una versión nueva»).
#   powershell -ExecutionPolicy Bypass -File release.ps1 [-Notes "qué cambió"] [-SkipBuild]
# Antes: subir APP_VERSION en src\version.py y hacer commit en la rama desktop (el script la sube).
# La app de escritorio se publica desde la rama desktop: main es la web y cada push ahí la despliega
# a producción, así que este script nunca toca main.
# Requisitos: gh auth login, Inno Setup 6.
# La etiqueta v<versión> también dispara el build de macOS (GitHub Actions), que adjunta su .dmg
# a la misma release.
param([string]$Notes = "", [switch]$SkipBuild)
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

Write-Host "== SHA256SUMS.txt"
$line = "{0}  {1}" -f (Get-FileHash $setup -Algorithm SHA256).Hash.ToLower(), (Split-Path $setup -Leaf)
[IO.File]::WriteAllText((Join-Path $PSScriptRoot "dist\SHA256SUMS.txt"), $line + "`n")
$line

if (-not $Notes) {
    $last = git tag --list "v*" --sort=-v:refname | Where-Object { $_ -ne $tag } | Select-Object -First 1
    $range = if ($last) { "$last..HEAD" } else { "HEAD" }
    $Notes = (git log $range --pretty=format:"- %s" | Where-Object { $_ -notmatch "^- (Merge|wip)" }) -join "`n"
    if (-not $Notes) { $Notes = "Versión $version" }
}
$notesFile = Join-Path $env:TEMP "universe-downloader-release-notes.md"
[IO.File]::WriteAllText($notesFile, "## Universe Downloader $version`n`n$Notes`n`n**UniverseDownloader-Setup-$version.exe**: Windows 10/11, sin administrador. Las versiones instaladas se actualizan solas desde la app.`n")

Write-Host "== Etiqueta $tag"
if (-not (git tag --list $tag)) {
    git tag -a $tag -m "Universe Downloader $version"
    Push-Origin $tag
    if ($LASTEXITCODE -ne 0) { throw "no se pudo subir la etiqueta $tag" }
}

Write-Host "== Release $tag en $repo"
$existing = @(gh release list --repo $repo --json tagName --jq ".[].tagName" 2>$null)
if ($existing -contains $tag) {
    # el build de macOS pudo crearla antes: solo se adjuntan los archivos de Windows
    gh release upload $tag --repo $repo --clobber $setup dist\SHA256SUMS.txt
} else {
    gh release create $tag --repo $repo --title "Universe Downloader $version" --notes-file $notesFile $setup dist\SHA256SUMS.txt
}
if ($LASTEXITCODE -ne 0) { throw "gh release falló" }
gh release view $tag --repo $repo --json url --jq ".url"
gh release view $tag --repo $repo --json assets --jq ".assets[] | .name"
Write-Host "== Listo. Las apps instaladas verán la versión $version al abrirse (o con «Versión…» en la barra lateral)."
