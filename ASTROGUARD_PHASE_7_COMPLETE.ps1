#requires -Version 5.1
<#
ASTROGUARD - PHASE 7 COMPLETE RELEASE VALIDATION
PowerShell 5.1 compatible
Project: C:\Users\PC\source\AstroGuard

Safety:
- No git reset, clean, stash, commit or push.
- No package installation or package manifest modification.
- No source code modification.
- Existing .next is backed up before release build.
- Existing server is stopped only after explicit confirmation.
- Failed build attempts to restore the previous .next.
- Sequential execution; no parallel builds.
#>

[CmdletBinding()]
param(
    [string]$ProjectRoot = "C:\Users\PC\source\AstroGuard",
    [int]$Port = 3000,
    [switch]$RunReleasePipeline,
    [switch]$SkipBrowser,
    [switch]$SkipStaticChecks
)

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

$ErrorCount = 0
$PassCount = 0
$WarnCount = 0
$Results = New-Object System.Collections.ArrayList

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Artifact = Join-Path $ProjectRoot "artifacts\phase7_complete_$Stamp"
$Logs = Join-Path $Artifact "logs"
$Reports = Join-Path $Artifact "reports"
$Screenshots = Join-Path $Artifact "screenshots"
$Backup = Join-Path $Artifact "backup"
$Browser = Join-Path $Artifact "browser"

$Frontend = Join-Path $ProjectRoot "frontend"
$NextDir = Join-Path $Frontend ".next"
$Package = Join-Path $Frontend "package.json"
$Lock = Join-Path $Frontend "package-lock.json"

$OldNext = ""
$OldServerPID = 0
$NewServerPID = 0
$BuildSucceeded = $false
$ServerStarted = $false
$NodeExe = ""
$NpmCli = ""

foreach ($d in @($Artifact,$Logs,$Reports,$Screenshots,$Backup,$Browser)) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}

function Record {
    param(
        [string]$Status,
        [string]$Stage,
        [string]$Name,
        [string]$Detail
    )

    $item = [pscustomobject]@{
        Time = (Get-Date).ToString("o")
        Status = $Status
        Stage = $Stage
        Name = $Name
        Detail = $Detail
    }

    [void]$script:Results.Add($item)

    switch ($Status) {
        "PASS" { $script:PassCount++ }
        "FAIL" { $script:ErrorCount++ }
        "WARN" { $script:WarnCount++ }
    }

    $color = "Gray"
    if ($Status -eq "PASS") { $color = "Green" }
    if ($Status -eq "FAIL") { $color = "Red" }
    if ($Status -eq "WARN") { $color = "Yellow" }

    Write-Host "[$Status] [$Stage] $Name : $Detail" -ForegroundColor $color
}

function SaveText {
    param([string]$Path,[string]$Text)

    $parent = Split-Path -Parent $Path
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }

    [System.IO.File]::WriteAllText(
        $Path,
        $Text,
        (New-Object System.Text.UTF8Encoding($false))
    )
}

function GetListener {
    param([int]$TargetPort)

    try {
        $items = @(Get-NetTCPConnection -State Listen -LocalPort $TargetPort -ErrorAction Stop)
        if ($items.Count -gt 0) {
            return $items[0]
        }
    }
    catch {}

    return $null
}

function GetProcessInfo {
    param([int]$Id)

    try {
        return Get-CimInstance Win32_Process -Filter "ProcessId=$Id" -ErrorAction Stop
    }
    catch {
        return $null
    }
}

function TestEndpoint {
    param(
        [int]$TargetPort,
        [string]$Route,
        [string]$Label
    )

    $url = "http://127.0.0.1:$TargetPort$Route"
    $code = 0
    $body = ""
    $timer = [Diagnostics.Stopwatch]::StartNew()

    try {
        $request = [Net.HttpWebRequest]::Create($url)
        $request.Method = "GET"
        $request.Timeout = 15000
        $request.ReadWriteTimeout = 15000
        $request.AllowAutoRedirect = $false

        try {
            $response = $request.GetResponse()
        }
        catch [Net.WebException] {
            if ($_.Exception.Response) {
                $response = $_.Exception.Response
            }
            else {
                throw
            }
        }

        $code = [int]$response.StatusCode
        $stream = $response.GetResponseStream()

        if ($stream) {
            $reader = New-Object System.IO.StreamReader($stream)
            $body = $reader.ReadToEnd()
            $reader.Dispose()
        }

        $response.Close()
    }
    catch {
        $body = $_.Exception.ToString()
    }

    $timer.Stop()

    SaveText (Join-Path $Logs "$Label.txt") $body

    if ($code -ge 200 -and $code -lt 400) {
        Record "PASS" "HTTP" $Route "HTTP $code; $([math]::Round($timer.Elapsed.TotalMilliseconds,2)) ms"
    }
    else {
        Record "FAIL" "HTTP" $Route "HTTP $code; $body"
    }

    return [pscustomobject]@{
        Route = $Route
        URL = $url
        StatusCode = $code
        DurationMs = [math]::Round($timer.Elapsed.TotalMilliseconds,2)
    }
}

function InvokeCommand {
    param(
        [string]$Name,
        [string]$Executable,
        [string[]]$Arguments,
        [string]$WorkingDirectory
    )

    $stdout = Join-Path $Logs "$Name.stdout.log"
    $stderr = Join-Path $Logs "$Name.stderr.log"

    Record "WARN" "COMMAND" $Name "Starting command. Exit code will determine result."

    $old = Get-Location
    $exitCode = 9009
    $exception = ""

    try {
        Set-Location -LiteralPath $WorkingDirectory

        $quoted = @()
        foreach ($arg in $Arguments) {
            $v = [string]$arg
            $v = $v.Replace('"','\"')
            $quoted += ('"' + $v + '"')
        }

        $argLine = $quoted -join " "

        $p = Start-Process `
            -FilePath $Executable `
            -ArgumentList $argLine `
            -WorkingDirectory $WorkingDirectory `
            -Wait `
            -PassThru `
            -NoNewWindow `
            -RedirectStandardOutput $stdout `
            -RedirectStandardError $stderr

        $exitCode = [int]$p.ExitCode
    }
    catch {
        $exception = $_.Exception.ToString()
        SaveText $stderr $exception
    }
    finally {
        Set-Location $old
    }

    if ($exitCode -eq 0) {
        Record "PASS" "COMMAND" $Name "Exit code 0"
    }
    else {
        Record "FAIL" "COMMAND" $Name "Exit code $exitCode. $exception"
    }

    return $exitCode
}

function GetHash {
    param([string]$Path)

    if (Test-Path -LiteralPath $Path) {
        return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
    }

    return "MISSING"
}

function GetGitStatus {
    $git = Get-Command git -ErrorAction SilentlyContinue
    if (-not $git) {
        return @("GIT_NOT_AVAILABLE")
    }

    $output = @(& git -C $ProjectRoot status --short 2>&1)
    return $output
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "ASTROGUARD PHASE 7 COMPLETE RELEASE VALIDATION" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Project: $ProjectRoot"
Write-Host "Artifacts: $Artifact"
Write-Host ""

# STAGE 00 - PROJECT PREFLIGHT

if (-not (Test-Path $ProjectRoot)) {
    Record "FAIL" "PREFLIGHT" "Project root" "Project root not found."
    throw "Invalid project root."
}
else {
    Record "PASS" "PREFLIGHT" "Project root" $ProjectRoot
}

if (-not (Test-Path $Frontend)) {
    Record "FAIL" "PREFLIGHT" "Frontend directory" "frontend directory missing."
    throw "Frontend directory missing."
}
else {
    Record "PASS" "PREFLIGHT" "Frontend directory" $Frontend
}

if (-not (Test-Path $Package)) {
    Record "FAIL" "PREFLIGHT" "package.json" "package.json missing."
    throw "package.json missing."
}

try {
    $PackageData = Get-Content $Package -Raw | ConvertFrom-Json
    Record "PASS" "PREFLIGHT" "package.json JSON" "Valid JSON."
}
catch {
    Record "FAIL" "PREFLIGHT" "package.json JSON" $_.Exception.Message
    throw
}

$LockValidation = $false
if (Test-Path $Lock) {
    try {
        $null = Get-Content $Lock -Raw | ConvertFrom-Json
        $LockValidation = $true
        Record "PASS" "PREFLIGHT" "package-lock JSON" "Valid JSON."
    }
    catch {
        Record "FAIL" "PREFLIGHT" "package-lock JSON" $_.Exception.Message
    }
}
else {
    Record "WARN" "PREFLIGHT" "package-lock" "Not present."
}

$Disk = Get-PSDrive -Name (Get-Item $ProjectRoot).PSDrive.Name
$FreeGB = [math]::Round($Disk.Free / 1GB,2)
Record "PASS" "PREFLIGHT" "Free disk" "$FreeGB GB"

if ($FreeGB -lt 5) {
    Record "FAIL" "PREFLIGHT" "Disk capacity" "Less than 5 GB free. Release build blocked."
}
elseif ($FreeGB -lt 10) {
    Record "WARN" "PREFLIGHT" "Disk capacity" "Less than 10 GB free."
}

# STAGE 01 - NODE AND NPM DISCOVERY

$NodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
if ($NodeCommand) {
    $NodeExe = $NodeCommand.Source
    $NodeVersion = & $NodeExe --version 2>&1
    Record "PASS" "TOOLCHAIN" "Node.js" "$NodeVersion"
}
else {
    Record "FAIL" "TOOLCHAIN" "Node.js" "node.exe not found."
}

$NpmCandidates = @(
    "C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js",
    "$env:APPDATA\npm\node_modules\npm\bin\npm-cli.js"
)

foreach ($candidate in $NpmCandidates) {
    if ((Test-Path $candidate) -and $NodeExe) {
        $NpmCli = $candidate
        break
    }
}

if ($NpmCli) {
    $NpmVersion = & $NodeExe $NpmCli --version 2>&1
    Record "PASS" "TOOLCHAIN" "npm CLI" "$NpmVersion"
}
else {
    Record "FAIL" "TOOLCHAIN" "npm CLI" "Global npm-cli.js not found."
}

if (-not $NodeExe -or -not $NpmCli) {
    throw "Node/npm preflight failed. No project changes made."
}

# STAGE 02 - BASELINE INTEGRITY

$PackageHashBefore = GetHash $Package
$LockHashBefore = GetHash $Lock
$GitBefore = @(GetGitStatus)

SaveText (Join-Path $Reports "git_status_before.txt") ($GitBefore -join "`r`n")

$HashBefore = [pscustomobject]@{
    PackageJson = $PackageHashBefore
    PackageLock = $LockHashBefore
}

$HashBefore | ConvertTo-Json | Set-Content (Join-Path $Reports "hashes_before.json") -Encoding UTF8

Record "PASS" "INTEGRITY" "Baseline captured" "Package hashes and Git status recorded."

# STAGE 03 - CURRENT SERVER IDENTITY

$Listener = GetListener $Port
$ServerHealthy = $false

if ($Listener) {
    $OldServerPID = [int]$Listener.OwningProcess
    $ProcessInfo = GetProcessInfo $OldServerPID

    if ($ProcessInfo) {
        $CommandLine = [string]$ProcessInfo.CommandLine
        $ExecutablePath = [string]$ProcessInfo.ExecutablePath

        Write-Host "Port $Port PID: $OldServerPID"
        Write-Host "Command: $CommandLine"

        if ($CommandLine -match "next" -and $CommandLine -match "AstroGuard") {
            Record "PASS" "SERVER" "Server identity" "AstroGuard Next.js process identified."
        }
        else {
            Record "WARN" "SERVER" "Server identity" "Process identity not conclusively verified. It will not be stopped automatically."
        }
    }

    $probe = TestEndpoint $Port "/" "initial_home"
    if ($probe.StatusCode -ge 200 -and $probe.StatusCode -lt 400) {
        $ServerHealthy = $true
    }
}
else {
    Record "WARN" "SERVER" "Existing server" "No listener on port $Port."
}

# STAGE 04 - STATIC TESTS

if (-not $SkipStaticChecks) {
    $scripts = @{}
    foreach ($property in $PackageData.scripts.PSObject.Properties) {
        $scripts[$property.Name] = [string]$property.Value
    }

    if ($scripts.ContainsKey("test")) {
        InvokeCommand "frontend_tests" $NodeExe @($NpmCli,"run","test") $Frontend | Out-Null
    }
    else {
        Record "WARN" "STATIC" "Tests" "No test script defined."
    }

    if ($scripts.ContainsKey("lint")) {
        InvokeCommand "frontend_lint" $NodeExe @($NpmCli,"run","lint") $Frontend | Out-Null
    }
    else {
        Record "WARN" "STATIC" "ESLint" "No lint script defined."
    }

    if (Test-Path (Join-Path $Frontend "node_modules\.bin\tsc.cmd")) {
        InvokeCommand "typescript_check" `
            (Join-Path $Frontend "node_modules\.bin\tsc.cmd") `
            @("--noEmit") `
            $Frontend | Out-Null
    }
    else {
        Record "WARN" "STATIC" "TypeScript" "Local tsc.cmd not found."
    }
}
else {
    Record "WARN" "STATIC" "Static checks" "Skipped by user parameter."
}

# STAGE 05 - ROUTE DISCOVERY

$Routes = New-Object System.Collections.ArrayList
[void]$Routes.Add("/")

$KnownRoutes = @(
    "/anomalies",
    "/telemetry",
    "/investigations",
    "/models"
)

foreach ($route in $KnownRoutes) {
    [void]$Routes.Add($route)
}

$Manifest = Join-Path $NextDir "server\app-paths-manifest.json"

if (Test-Path $Manifest) {
    try {
        $manifestData = Get-Content $Manifest -Raw | ConvertFrom-Json
        foreach ($property in $manifestData.PSObject.Properties) {
            $route = [string]$property.Name
            $route = $route -replace "/page$",""
            $route = $route -replace "/route$",""

            if (-not $route) { $route = "/" }

            if ($route -match "\[") {
                continue
            }

            if ($Routes -notcontains $route) {
                [void]$Routes.Add($route)
            }
        }

        Record "PASS" "ROUTES" "Manifest discovery" "$($Routes.Count) route candidates."
    }
    catch {
        Record "WARN" "ROUTES" "Manifest discovery" $_.Exception.Message
    }
}
else {
    Record "WARN" "ROUTES" "Manifest" "No current Next.js app paths manifest."
}

$Routes = @($Routes | Select-Object -Unique)

# STAGE 06 - RELEASE BUILD

if ($RunReleasePipeline) {
    Write-Host ""
    Write-Host "RELEASE PIPELINE REQUESTED" -ForegroundColor Yellow

    if ($FreeGB -lt 5) {
        Record "FAIL" "BUILD" "Disk safety" "Build refused because disk space is below 5 GB."
    }
    else {
        if ($Listener) {
            Write-Host ""
            Write-Host "Port $Port currently belongs to PID $OldServerPID." -ForegroundColor Yellow
            Write-Host "Do not continue unless this is the AstroGuard server you intend to replace."
            $confirmation = Read-Host "Type STOP-3000 to stop the validated current server"

            if ($confirmation -ne "STOP-3000") {
                Record "WARN" "BUILD" "Server stop" "User declined server stop. Build skipped."
            }
            else {
                $currentListener = GetListener $Port

                if (-not $currentListener -or [int]$currentListener.OwningProcess -ne $OldServerPID) {
                    Record "FAIL" "BUILD" "Server identity recheck" "Port ownership changed. Refusing to stop any process."
                }
                else {
                    $currentInfo = GetProcessInfo $OldServerPID
                    $currentCommand = ""
                    if ($currentInfo) {
                        $currentCommand = [string]$currentInfo.CommandLine
                    }

                    if ($currentCommand -notmatch "next" -or $currentCommand -notmatch "AstroGuard") {
                        Record "FAIL" "BUILD" "Server identity recheck" "Current process is not conclusively AstroGuard. Refusing to stop."
                    }
                    else {
                        Stop-Process -Id $OldServerPID -ErrorAction Stop
                        Start-Sleep -Seconds 2

                        if (GetListener $Port) {
                            Record "FAIL" "BUILD" "Server shutdown" "Port still occupied. No further process will be killed."
                        }
                        else {
                            Record "PASS" "BUILD" "Server shutdown" "Validated server stopped."
                            $Listener = $null
                        }
                    }
                }
            }
        }

        if (-not (GetListener $Port)) {
            if (Test-Path $NextDir) {
                $OldNext = Join-Path $Backup "previous_next"
                try {
                    Move-Item -LiteralPath $NextDir -Destination $OldNext
                    Record "PASS" "BACKUP" ".next backup" $OldNext
                }
                catch {
                    Record "FAIL" "BACKUP" ".next backup" $_.Exception.Message
                    $OldNext = ""
                }
            }

            if (-not (Test-Path $NextDir) -and (-not (Test-Path $OldNext) -or $OldNext)) {
                $buildExit = InvokeCommand "production_build" $NodeExe @($NpmCli,"run","build") $Frontend

                if ($buildExit -eq 0 -and (Test-Path $NextDir)) {
                    $BuildSucceeded = $true
                    Record "PASS" "BUILD" "Production build" "Build succeeded and .next exists."
                }
                else {
                    Record "FAIL" "BUILD" "Production build" "Build failed or .next output missing."

                    if ($OldNext -and (Test-Path $OldNext) -and -not (Test-Path $NextDir)) {
                        try {
                            Move-Item -LiteralPath $OldNext -Destination $NextDir
                            Record "PASS" "ROLLBACK" "Restore old .next" "Previous build restored."
                        }
                        catch {
                            Record "FAIL" "ROLLBACK" "Restore old .next" $_.Exception.Message
                        }
                    }
                }
            }
        }
    }
}
else {
    Record "WARN" "BUILD" "Production build" "Not requested. Existing build output preserved."
}

# STAGE 07 - START PRODUCTION SERVER

if ($RunReleasePipeline -and $BuildSucceeded) {
    $current = GetListener $Port

    if ($current) {
        Record "FAIL" "SERVER_START" "Port availability" "Port is still occupied. No process will be killed."
    }
    else {
        $startOut = Join-Path $Logs "next_start.stdout.log"
        $startErr = Join-Path $Logs "next_start.stderr.log"

        try {
            $server = Start-Process `
                -FilePath $NodeExe `
                -ArgumentList @(
                    (Join-Path $Frontend "node_modules\next\dist\bin\next"),
                    "start",
                    "-H","127.0.0.1",
                    "-p",[string]$Port
                ) `
                -WorkingDirectory $Frontend `
                -PassThru `
                -RedirectStandardOutput $startOut `
                -RedirectStandardError $startErr

            $NewServerPID = [int]$server.Id
            $ServerStarted = $true

            $ready = $false
            for ($i=0; $i -lt 30; $i++) {
                Start-Sleep -Seconds 2
                $current = GetListener $Port

                if ($current) {
                    $check = TestEndpoint $Port "/" "post_build_home"
                    if ($check.StatusCode -ge 200 -and $check.StatusCode -lt 400) {
                        $ready = $true
                        break
                    }
                }

                if ($server.HasExited) {
                    break
                }
            }

            if ($ready) {
                Record "PASS" "SERVER_START" "Production server" "HTTP response received on port $Port."
            }
            else {
                Record "FAIL" "SERVER_START" "Production server" "Server did not become healthy. Review startup logs."
            }
        }
        catch {
            Record "FAIL" "SERVER_START" "Production server" $_.Exception.ToString()
        }
    }
}

# STAGE 08 - FINAL HTTP ROUTE TESTS

$finalListener = GetListener $Port
$HttpResults = New-Object System.Collections.ArrayList

if ($finalListener) {
    foreach ($route in $Routes) {
        $safeName = $route -replace '[^a-zA-Z0-9]','_'
        $probe = TestEndpoint $Port $route ("route_" + $safeName)
        [void]$HttpResults.Add($probe)
    }
}
else {
    Record "WARN" "HTTP" "Final server" "No listener on port $Port. HTTP route checks unavailable."
}

$HttpResults | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $Reports "http_routes.json") -Encoding UTF8

# STAGE 09 - PLAYWRIGHT PREFLIGHT

if (-not $SkipBrowser) {
    $PlaywrightPackage = Join-Path $Frontend "node_modules\playwright\package.json"

    if (Test-Path $PlaywrightPackage) {
        try {
            $pw = Get-Content $PlaywrightPackage -Raw | ConvertFrom-Json
            Record "PASS" "BROWSER" "Playwright package" ([string]$pw.version)

            $nodeScript = @'
const fs = require("fs");
const path = require("path");
const pw = require("playwright");
const chromium = pw.chromium;
const executable = chromium.executablePath();

console.log("PLAYWRIGHT_VERSION=" + require("playwright/package.json").version);
console.log("CHROMIUM_PATH=" + executable);
console.log("CHROMIUM_EXISTS=" + fs.existsSync(executable));

if (!fs.existsSync(executable)) process.exitCode = 2;
'@

            $runnerFile = Join-Path $Browser "browser_preflight.cjs"
            SaveText $runnerFile $nodeScript

            $env:NODE_PATH = Join-Path $Frontend "node_modules"
            $preflightOut = Join-Path $Logs "browser_preflight.stdout.log"
            $preflightErr = Join-Path $Logs "browser_preflight.stderr.log"

            $preflightExit = InvokeCommand `
                "browser_preflight" `
                $NodeExe `
                @($runnerFile) `
                $Frontend

            if ($preflightExit -eq 0) {
                Record "PASS" "BROWSER" "Chromium availability" "Playwright Chromium executable found."
            }
            else {
                Record "WARN" "BROWSER" "Chromium availability" "Browser executable missing or launch prerequisites unavailable."
            }
        }
        catch {
            Record "WARN" "BROWSER" "Playwright preflight" $_.Exception.Message
        }
    }
    else {
        Record "WARN" "BROWSER" "Playwright package" "Playwright not installed in frontend node_modules."
    }
}
else {
    Record "WARN" "BROWSER" "Browser QA" "Skipped by parameter."
}

# STAGE 10 - SOURCE INTEGRITY

$PackageHashAfter = GetHash $Package
$LockHashAfter = GetHash $Lock

if ($PackageHashBefore -eq $PackageHashAfter) {
    Record "PASS" "INTEGRITY" "package.json" "SHA256 unchanged."
}
else {
    Record "FAIL" "INTEGRITY" "package.json" "SHA256 changed."
}

if ($LockHashBefore -eq $LockHashAfter) {
    Record "PASS" "INTEGRITY" "package-lock.json" "SHA256 unchanged."
}
else {
    Record "FAIL" "INTEGRITY" "package-lock.json" "SHA256 changed."
}

$GitAfter = @(GetGitStatus)
SaveText (Join-Path $Reports "git_status_after.txt") ($GitAfter -join "`r`n")

$AddedGit = @($GitAfter | Where-Object { $GitBefore -notcontains $_ })
$RemovedGit = @($GitBefore | Where-Object { $GitAfter -notcontains $_ })

if ($AddedGit.Count -eq 0 -and $RemovedGit.Count -eq 0) {
    Record "PASS" "INTEGRITY" "Git worktree status" "No Git status delta."
}
else {
    Record "WARN" "INTEGRITY" "Git worktree status" "Git status changed. Review before accepting phase."
}

# STAGE 11 - REPORTS

$Summary = [pscustomobject]@{
    Phase = "7_COMPLETE_FRONTEND_RELEASE_VALIDATION"
    GeneratedAt = (Get-Date).ToString("o")
    ProjectRoot = $ProjectRoot
    Frontend = $Frontend
    Port = $Port
    ReleasePipelineRequested = [bool]$RunReleasePipeline
    BuildSucceeded = $BuildSucceeded
    ServerStarted = $ServerStarted
    OldServerPID = $OldServerPID
    NewServerPID = $NewServerPID
    PackageJsonUnchanged = ($PackageHashBefore -eq $PackageHashAfter)
    PackageLockUnchanged = ($LockHashBefore -eq $LockHashAfter)
    GitStatusDelta = ($AddedGit.Count -gt 0 -or $RemovedGit.Count -gt 0)
    Pass = $PassCount
    Fail = $ErrorCount
    Warn = $WarnCount
    Routes = $Routes
    ArtifactDirectory = $Artifact
}

$Summary | ConvertTo-Json -Depth 8 |
    Set-Content (Join-Path $Reports "phase_summary.json") -Encoding UTF8

$Results | Export-Csv `
    -LiteralPath (Join-Path $Reports "phase_results.csv") `
    -NoTypeInformation `
    -Encoding UTF8

$Markdown = @"
# AstroGuard Phase 7 — Final Validation

Generated: $($Summary.GeneratedAt)

## Execution

- Project: $ProjectRoot
- Frontend: $Frontend
- Port: $Port
- Release requested: $RunReleasePipeline
- Build succeeded: $BuildSucceeded
- Server started: $ServerStarted

## Results

- PASS: $PassCount
- FAIL: $ErrorCount
- WARN: $WarnCount

## Package integrity

- package.json unchanged: $($Summary.PackageJsonUnchanged)
- package-lock unchanged: $($Summary.PackageLockUnchanged)
- Git status delta: $($Summary.GitStatusDelta)

## Routes

$($Routes -join "`r`n")

## Artifact folders

- logs/
- reports/
- screenshots/
- browser/
- backup/

## Acceptance

A successful script exit does not automatically mean Phase 7 is accepted.
Review test output, lint, TypeScript, build logs, all HTTP routes, browser
evidence, screenshots, console errors and Git status before declaring completion.

No live NASA telemetry or external spacecraft integration is claimed by this
validation script.
"@

SaveText (Join-Path $Reports "PHASE_7_FINAL_REPORT.md") $Markdown

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PHASE 7 EXECUTION FINISHED" -ForegroundColor Cyan
Write-Host "PASS: $PassCount" -ForegroundColor Green
Write-Host "FAIL: $ErrorCount" -ForegroundColor Red
Write-Host "WARN: $WarnCount" -ForegroundColor Yellow
Write-Host "ARTIFACTS: $Artifact" -ForegroundColor Cyan
Write-Host "SUMMARY: $(Join-Path $Reports 'phase_summary.json')" -ForegroundColor Cyan
Write-Host "FINAL REPORT: $(Join-Path $Reports 'PHASE_7_FINAL_REPORT.md')" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if ($ErrorCount -gt 0) {
    Write-Host "PHASE 7 NOT ACCEPTED: Review failures." -ForegroundColor Red
}
else {
    Write-Host "No failed checks recorded. Review all evidence before acceptance." -ForegroundColor Green
}