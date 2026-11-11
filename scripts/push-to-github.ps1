#requires -Version 5.1
# Erstellt ein privates GitHub-Repo und pusht main plus alle Versionstags.
$ErrorActionPreference = 'Stop'
$owner = 'Florian1404'
$repo = 'ahnenforschung-suite'
$full = "$owner/$repo"
$remote = "https://github.com/$full.git"
function Assert-OK([string]$step) { if ($LASTEXITCODE -ne 0) { throw "$step fehlgeschlagen (Exit $LASTEXITCODE)" } }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git fehlt: winget install --id Git.Git --exact' }
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw 'GitHub CLI fehlt: winget install --id GitHub.cli --exact' }
Push-Location (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
try {
    if ((& git branch --show-current).Trim() -ne 'main') { throw 'Erwarteter Git-Branch main fehlt.' }
    if (& git status --porcelain) { throw 'Git hat lokale Aenderungen. Bitte vor dem Push sichern/committen.' }
    & gh auth status 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) { & gh auth login --hostname github.com --git-protocol https --web; Assert-OK 'Login' }
    $login = (& gh api user --jq '.login').Trim(); Assert-OK 'Accountpruefung'
    if ($login -ine $owner) { throw "Eingeloggt als $login statt $owner. Mit gh auth switch Konto wechseln." }
    & gh repo view $full --json name --jq '.name' 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) { & gh repo create $full --private --description 'Ahnenforschung: Matricula-Tools und Ahnenarchiv'; Assert-OK 'Repo-Erstellung' }
    $vis = (& gh repo view $full --json visibility --jq '.visibility').Trim(); Assert-OK 'Sichtbarkeitspruefung'
    if ($vis -ne 'PRIVATE') { throw "Abbruch: GitHub-Repo ist $vis statt PRIVATE." }
    $origin = & git remote get-url origin 2>$null
    if ($LASTEXITCODE -ne 0) { & git remote add origin $remote; Assert-OK 'Remote anlegen' }
    elseif (($origin.Trim() -replace '\.git$', '') -ne ($remote -replace '\.git$', '')) { throw "Remote origin zeigt auf falsches Ziel: $origin" }
    & gh auth setup-git; Assert-OK 'Git-Authentifizierung'
    & git push -u origin main; Assert-OK 'Branch-Push'
    & git push origin --tags; Assert-OK 'Versions-Tags'
    Write-Host "FERTIG: https://github.com/$full" -ForegroundColor Green
} finally { Pop-Location }
