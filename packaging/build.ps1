#Requires -Version 5.1
<#
Builds the Windows installer: frontend, self-contained executable, Inno Setup installer.
Needs Python 3.14, Node.js 24 with npm and Inno Setup 6.7.1 (ISCC.exe) on the machine.
Result: packaging\build\installer\MacheCellVoltageReader-<version>-setup.exe
#>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$buildDir = Join-Path $PSScriptRoot 'build'
$pyinstallerDir = Join-Path $buildDir 'pyinstaller'
$appDir = Join-Path $pyinstallerDir 'dist\MacheCells'
$smokePort = '8765'

function Invoke-Native {
    param([string]$Command, [string[]]$Arguments)
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Command exited with code $LASTEXITCODE"
    }
}

function Find-InnoSetupCompiler {
    $onPath = Get-Command 'ISCC.exe' -ErrorAction SilentlyContinue
    if ($onPath) {
        return $onPath.Source
    }
    $installed = @(${env:ProgramFiles(x86)}, $env:ProgramFiles, "$env:LOCALAPPDATA\Programs") |
        Where-Object { $_ } |
        ForEach-Object { Join-Path $_ 'Inno Setup 6\ISCC.exe' } |
        Where-Object { Test-Path $_ }
    if (-not $installed) {
        throw 'Inno Setup 6 (ISCC.exe) was not found. Install it from https://jrsoftware.org/isdl.php'
    }
    return @($installed)[0]
}

function Test-ReaderAnswering {
    param([string]$Url)
    try {
        Invoke-RestMethod -Uri "${Url}api/ports" -TimeoutSec 2 | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Test-BuiltApplication {
    $env:MACHE_PORT = $smokePort
    $url = "http://127.0.0.1:$smokePort/"
    $exe = Join-Path $appDir 'MacheCells.exe'
    $server = Start-Process -FilePath $exe -PassThru -WindowStyle Minimized
    try {
        $deadline = (Get-Date).AddSeconds(30)
        while (-not (Test-ReaderAnswering $url) -and (Get-Date) -lt $deadline) {
            Start-Sleep -Seconds 1
        }
        if (-not (Test-ReaderAnswering $url)) {
            throw "The built application did not answer at $url"
        }
        if ((Invoke-WebRequest -Uri $url -UseBasicParsing).StatusCode -ne 200) {
            throw 'The built application does not serve the GUI'
        }
        $second = Start-Process -FilePath $exe -PassThru -WindowStyle Minimized
        if (-not $second.WaitForExit(30000) -or $second.ExitCode -ne 0) {
            $second | Stop-Process -Force -ErrorAction SilentlyContinue
            throw 'A second launch did not hand over to the running reader'
        }
    } finally {
        $server | Stop-Process -Force -ErrorAction SilentlyContinue
        Remove-Item Env:\MACHE_PORT
    }
}

Push-Location $root
try {
    $version = (& python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])")
    if ($LASTEXITCODE -ne 0) {
        throw 'Cannot read the version from pyproject.toml'
    }

    Push-Location 'frontend'
    try {
        Invoke-Native 'npm' @('ci')
        Invoke-Native 'npm' @('run', 'build')
    } finally {
        Pop-Location
    }
    $web = Join-Path $root 'src\mache_cells\web'
    Remove-Item -Recurse -Force $web -ErrorAction SilentlyContinue
    Copy-Item -Recurse (Join-Path $root 'frontend\dist') $web

    Remove-Item -Recurse -Force $buildDir -ErrorAction SilentlyContinue
    Invoke-Native 'python' @('-m', 'pip', 'install', '--require-hashes', '-r', (Join-Path $PSScriptRoot 'requirements-windows.txt'))
    Invoke-Native 'python' @('-m', 'pip', 'install', '--no-deps', '--no-build-isolation', '.')
    Invoke-Native 'python' @(
        '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--console',
        '--name', 'MacheCells',
        '--distpath', (Join-Path $pyinstallerDir 'dist'),
        '--workpath', (Join-Path $pyinstallerDir 'work'),
        '--specpath', $pyinstallerDir,
        '--collect-submodules', 'uvicorn',
        '--collect-submodules', 'websockets',
        '--collect-submodules', 'serial',
        '--add-data', "$web;mache_cells/web",
        (Join-Path $PSScriptRoot 'launcher.py')
    )

    Test-BuiltApplication

    Invoke-Native (Find-InnoSetupCompiler) @("/DAppVersion=$version", (Join-Path $PSScriptRoot 'mache-cells.iss'))
} finally {
    Pop-Location
}
