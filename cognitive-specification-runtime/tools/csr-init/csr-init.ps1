#Requires -Version 5.1
<#
.SYNOPSIS
    CSR Onboarding - diagnostic et initialisation d'un dossier de travail.

.DESCRIPTION
    Phase 1 (diagnostic) : verifie Claude Code, Git, le plugin CSR et le chemin de travail.
    Phase 2 (initialisation) : cree la structure minimale runtime/ si elle est absente.

    Ce script est sans danger : il ne modifie jamais un dossier deja initialise,
    n'installe aucun logiciel, ne touche pas aux parametres systeme.

.PARAMETER WorkDir
    Chemin du dossier de travail CSR (dossier projet de l'utilisateur).
    Par defaut : repertoire courant.

.PARAMETER DiagOnly
    Si present, execute uniquement le diagnostic sans initialiser.

.EXAMPLE
    .\csr-init.ps1
    .\csr-init.ps1 -WorkDir "C:\Users\moi\Documents\Mon-Projet"
    .\csr-init.ps1 -DiagOnly

.NOTES
    Compatible Windows PowerShell 5.1 et PowerShell 7+.
    Version : 1.2.0  (CSR product 1.0.0)
    Codes retour : 0 = OK ; 1 = au moins un FAIL (y compris en -DiagOnly).
#>
[CmdletBinding()]
param(
    [string]$WorkDir = $PWD.Path,
    [switch]$DiagOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Exact plugin identity installed by the onboarding (plugin@marketplace).
$CSRPluginKey = "cognitive-specification-runtime@csr-private"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
}

function Write-Check {
    param([string]$Label, [string]$Status, [string]$Detail)
    $color = switch ($Status) {
        "PASS" { "Green"  }
        "WARN" { "Yellow" }
        "FAIL" { "Red"    }
        "INFO" { "White"  }
        default { "Gray"  }
    }
    if ($Detail) {
        $line = "  [$Status]  $Label  --  $Detail"
    } else {
        $line = "  [$Status]  $Label"
    }
    Write-Host $line -ForegroundColor $color
}

function Get-CSRPluginInstallPath {
    # Resolves actual install path from installed_plugins.json.
    # Returns the installPath string, or $null if not found.
    # Honour CLAUDE_CONFIG_DIR (isolated or relocated profiles) before the
    # default %USERPROFILE%\.claude location (issue #53).
    # Exact selection (issue #54): only the key
    # "cognitive-specification-runtime@csr-private", and only its user-scope
    # install (the scope the onboarding installs). A same-named plugin from
    # another marketplace, or a project-scope install belonging to another
    # folder, must never be reported as "the" CSR plugin.
    if ($env:CLAUDE_CONFIG_DIR) {
        $configDir = $env:CLAUDE_CONFIG_DIR
    } else {
        $configDir = Join-Path $env:USERPROFILE ".claude"
    }
    $installedJson = Join-Path $configDir "plugins\installed_plugins.json"
    if (-not (Test-Path $installedJson)) { return $null }
    try {
        $data = Get-Content $installedJson -Raw | ConvertFrom-Json
        $prop = $data.plugins.PSObject.Properties[$CSRPluginKey]
        if (-not $prop) { return $null }
        $userEntry = @($prop.Value) | Where-Object { $_.scope -eq "user" } | Select-Object -First 1
        if ($userEntry -and $userEntry.installPath) { return $userEntry.installPath }
    } catch { }
    return $null
}

function Get-CommandVersion {
    param([string]$Cmd, [string]$Arg)
    if (-not $Arg) { $Arg = "--version" }
    try {
        $out = & $Cmd $Arg 2>&1 | Select-Object -First 1
        return [string]$out
    } catch {
        return $null
    }
}

# ---------------------------------------------------------------------------
# Initialize-CSRWorkspace
#
# Fonction d'initialisation commune au script et au point d'entree CSR.
#
# - Recoit un chemin explicite
# - Idempotente : ne fait rien si runtime/workspaces.md existe deja
# - Cree uniquement : runtime/ et runtime/workspaces.md (tableau vide)
# - Ne cree jamais de projet par defaut, n'active rien
# - Retourne : "INITIALIZED", "ALREADY_PRESENT" ou "FAILED:<raison>"
# ---------------------------------------------------------------------------

function Initialize-CSRWorkspace {
    param([string]$Path)

    $runtimeDir   = Join-Path $Path "runtime"
    $registryFile = Join-Path $runtimeDir "workspaces.md"

    if (Test-Path $registryFile) {
        return "ALREADY_PRESENT"
    }

    if ((Test-Path $Path) -and (-not (Test-Path $Path -PathType Container))) {
        return "FAILED:WorkDir existe mais n'est pas un dossier"
    }

    try {
        if (-not (Test-Path $runtimeDir)) {
            New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
        }

        # Contenu canonique du registre (correspond au contrat runtime/workspaces.md)
        $header  = "# Workspace Registry"
        $blank   = ""
        $cols    = "| workspace_id | created | status | description | last_active | runtime_version | spec_template_version |"
        $sep     = "| ------------ | ------- | ------ | ----------- | ----------- | --------------- | --------------------- |"
        $content = $header + "`n" + $blank + "`n" + $cols + "`n" + $sep + "`n"

        [System.IO.File]::WriteAllText($registryFile, $content, [System.Text.UTF8Encoding]::new($false))

        return "INITIALIZED"
    } catch {
        return ("FAILED:" + $_.Exception.Message)
    }
}

# ---------------------------------------------------------------------------
# Phase 1 - Diagnostic
# ---------------------------------------------------------------------------

Write-Header "CSR Diagnostic"
Write-Host "  Dossier de travail : $WorkDir" -ForegroundColor Gray
Write-Host ""

$diagPassed = $true
$pluginFound = $false

# --- Check 1 : Claude Code CLI ---
$claudeVersion = Get-CommandVersion "claude"
if ($claudeVersion) {
    Write-Check "Claude Code CLI" "PASS" $claudeVersion
} else {
    Write-Check "Claude Code CLI" "FAIL" "introuvable dans le PATH - installez Claude Code puis relancez"
    $diagPassed = $false
}

# --- Check 1b : options de lancement recommandees (issue #57) ---
# Commande de lancement : claude --permission-mode auto --effort low
# Verifie seulement que la CLI connait ces options (aide locale, aucun appel reseau).
# Une politique (disableAutoMode) ou un refus du compte ne se voit qu'au demarrage :
# Claude Code demarre alors en mode manuel (voir guide-demarrage.md).
$launchCommand = "claude --permission-mode auto --effort low"
if ($claudeVersion) {
    $helpStr = ""
    try { $helpStr = (& claude --help 2>&1 | Out-String) } catch { }
    $autoKnown   = $helpStr -match '"auto"'
    $effortKnown = $helpStr -match '--effort'
    if ($autoKnown -and $effortKnown) {
        Write-Check "Lancement auto + effort low" "PASS" "options reconnues par cette version"
    } else {
        $missing = @()
        if (-not $autoKnown)   { $missing += "--permission-mode auto" }
        if (-not $effortKnown) { $missing += "--effort" }
        Write-Check "Lancement auto + effort low" "WARN" ("option(s) inconnue(s) : " + ($missing -join ", ") + " - mettez a jour Claude Code (claude update), sinon lancez simplement claude")
        $launchCommand = "claude"
    }
    $autoPolicy = @()
    if ($env:CLAUDE_CONFIG_DIR) { $profileDir = $env:CLAUDE_CONFIG_DIR } else { $profileDir = Join-Path $env:USERPROFILE ".claude" }
    foreach ($f in @((Join-Path $profileDir "settings.json"), "C:\Program Files\ClaudeCode\managed-settings.json")) {
        if (Test-Path -LiteralPath $f) {
            try {
                $raw = Get-Content -LiteralPath $f -Raw
                if ($raw -match '"disableAutoMode"\s*:\s*"disable"') { $autoPolicy += $f }
            } catch { }
        }
    }
    if ($autoPolicy.Count -gt 0) {
        Write-Check "Mode auto" "WARN" ("desactive par un reglage (" + ($autoPolicy -join ", ") + ") : Claude Code demarrera en mode manuel et demandera les autorisations techniques")
    }
}

# --- Check 2 : PATH utilisateur contient .local/bin ---
$userPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
$localBin  = Join-Path $env:USERPROFILE ".local\bin"
if ($userPath -and $userPath.Contains($localBin)) {
    Write-Check "PATH (.local/bin)" "PASS"
} else {
    if ($claudeVersion) {
        Write-Check "PATH (.local/bin)" "INFO" "absent du PATH utilisateur mais claude repond"
    } else {
        Write-Check "PATH (.local/bin)" "WARN" "$localBin absent du PATH - ajoutez-le si claude n'est pas trouve"
    }
}

# --- Check 3 : Git ---
$gitVersion = Get-CommandVersion "git"
if ($gitVersion) {
    Write-Check "Git" "PASS" $gitVersion
} else {
    Write-Check "Git" "WARN" "absent - requis pour l'installation du plugin via marketplace add"
}

# --- Check 4 : Plugin CSR ---
if ($claudeVersion) {
    try {
        $pluginListRaw = & claude plugin list 2>&1
        $pluginListStr = ($pluginListRaw | Out-String)
        if ($pluginListStr -match [regex]::Escape($CSRPluginKey)) {
            $pluginFound = $true
            $versionMatch = [regex]::Match($pluginListStr, [regex]::Escape($CSRPluginKey) + "\s+Version:\s*(\S+)")
            $resolvedPath = Get-CSRPluginInstallPath
            $detail = if ($versionMatch.Success) { "$CSRPluginKey " + $versionMatch.Groups[1].Value } else { $CSRPluginKey }
            if ($resolvedPath) {
                $detail += " -- $resolvedPath"
                Write-Check "Plugin CSR" "PASS" $detail
            } else {
                Write-Check "Plugin CSR" "WARN" ($detail + " -- installation de portee user introuvable dans installed_plugins.json du profil effectif")
            }
        } else {
            Write-Check "Plugin CSR" "FAIL" "non installe - voir guide-demarrage.md section Installation"
            $diagPassed = $false
        }
    } catch {
        Write-Check "Plugin CSR" "WARN" ("impossible de lister les plugins : " + $_.Exception.Message)
    }
} else {
    Write-Check "Plugin CSR" "INFO" "non verifie (Claude Code absent)"
}

# --- Check 5 : Dossier de travail ---
if (Test-Path $WorkDir -PathType Container) {
    Write-Check "Dossier de travail" "PASS" $WorkDir
} elseif (-not (Test-Path $WorkDir)) {
    Write-Check "Dossier de travail" "WARN" "absent - il sera cree a l'initialisation"
} else {
    Write-Check "Dossier de travail" "FAIL" ("chemin existe mais n'est pas un dossier : $WorkDir")
    $diagPassed = $false
}

# --- Check 6 : Registre projets ---
$runtimeDirCheck   = Join-Path $WorkDir "runtime"
$registryFileCheck = Join-Path $runtimeDirCheck "workspaces.md"

$workspacesDir = Join-Path $WorkDir "workspaces"
$hasWorkspaceFolders = (Test-Path $workspacesDir) -and (Get-ChildItem $workspacesDir -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0

if (-not (Test-Path $WorkDir)) {
    Write-Check "Registre projets" "INFO" "dossier absent - sera initialise"
} elseif (-not (Test-Path $registryFileCheck)) {
    if ($hasWorkspaceFolders) {
        Write-Check "Registre projets" "FAIL" "REGISTRE ABSENT mais workspaces/ contient des dossiers - diagnostic requis avant toute initialisation"
        Write-Host ""
        Write-Host "  ATTENTION : des dossiers de projets existent sous workspaces/ mais il n'y a pas" -ForegroundColor Red
        Write-Host "  de registre runtime/workspaces.md. Cela indique un etat incomplet ou corrompu." -ForegroundColor Red
        Write-Host "  Ne recreez PAS le registre manuellement. Contactez l'administrateur CSR." -ForegroundColor Red
        $diagPassed = $false
    } else {
        Write-Check "Registre projets" "INFO" "absent - sera cree a l'initialisation (espace neuf)"
    }
} else {
    try {
        $regContent = Get-Content $registryFileCheck -Raw -Encoding UTF8
        if ($regContent -match "\| workspace_id") {
            $rows = ($regContent -split "`n") | Where-Object {
                $_ -match "^\|" -and $_ -notmatch "workspace_id" -and $_ -notmatch "^[\| -]+$"
            }
            $count = ($rows | Measure-Object).Count
            Write-Check "Registre projets" "PASS" ("$count projet(s) existant(s) - espace deja initialise")
        } else {
            Write-Check "Registre projets" "FAIL" "format inattendu - le registre est corrompu, ne pas reinitialiser manuellement"
            Write-Host ""
            Write-Host "  ATTENTION : runtime/workspaces.md existe mais ne contient pas l'en-tete attendu." -ForegroundColor Red
            Write-Host "  Corrigez ou remplacez ce fichier avant de continuer." -ForegroundColor Red
            $diagPassed = $false
        }
    } catch {
        Write-Check "Registre projets" "FAIL" ("lecture impossible : " + $_.Exception.Message)
        $diagPassed = $false
    }
}

# --- Resume diagnostic ---
Write-Host ""
if ($diagPassed) {
    Write-Host "  Diagnostic : OK" -ForegroundColor Green
} else {
    Write-Host "  Diagnostic : ECHECS detectes - corrigez les points FAIL avant de continuer." -ForegroundColor Red
}

if ($DiagOnly) {
    Write-Host ""
    Write-Host "  Mode diagnostic seul (-DiagOnly) - initialisation ignoree." -ForegroundColor Gray
    # Issue #54: a FAIL must be visible in the exit code too, not only in the
    # text, so a caller checking $LASTEXITCODE stops on an inconsistent state.
    if (-not $diagPassed) { exit 1 }
    exit 0
}

if (-not $diagPassed) {
    Write-Host ""
    Write-Host "  Initialisation annulee. Corrigez les FAIL ci-dessus et relancez." -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------------------
# Phase 2 - Initialisation
# ---------------------------------------------------------------------------

Write-Header "CSR Initialisation"
Write-Host "  Dossier : $WorkDir" -ForegroundColor Gray
Write-Host ""

if (-not (Test-Path $WorkDir)) {
    try {
        New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null
        Write-Check "Creation du dossier" "PASS" $WorkDir
    } catch {
        Write-Check "Creation du dossier" "FAIL" $_.Exception.Message
        exit 1
    }
}

$initResult = Initialize-CSRWorkspace -Path $WorkDir

if ($initResult -eq "INITIALIZED") {
    Write-Check "Registre projets (runtime/workspaces.md)" "PASS" "cree"
} elseif ($initResult -eq "ALREADY_PRESENT") {
    Write-Check "Registre projets (runtime/workspaces.md)" "INFO" "deja present - espace existant preserve"
} else {
    $reason = $initResult.Substring(7)  # supprimer "FAILED:"
    Write-Check "Registre projets (runtime/workspaces.md)" "FAIL" $reason
    exit 1
}

# --- Resume final ---
Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Cyan
if ($initResult -eq "ALREADY_PRESENT") {
    Write-Host "  Espace deja initialise. Aucune modification." -ForegroundColor Green
} else {
    Write-Host "  Espace initialise avec succes." -ForegroundColor Green
}
Write-Host ""
Write-Host "  Prochaine etape :" -ForegroundColor White
if (-not $pluginFound) {
    Write-Host "    0. Installez le plugin CSR (voir docs/onboarding/guide-demarrage.md)" -ForegroundColor Yellow
}
Write-Host "    1. Dans PowerShell (meme profil Claude) :" -ForegroundColor White
Write-Host ("         Set-Location -LiteralPath '" + $WorkDir.Replace("'", "''") + "'") -ForegroundColor White
Write-Host ("         " + $launchCommand) -ForegroundColor White
Write-Host "    2. Dans Claude Code, tapez :" -ForegroundColor White
Write-Host "         /cognitive-specification-runtime:csr" -ForegroundColor White
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host ""
