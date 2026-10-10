param(
    [ValidateSet('demo', 'openai')][string]$Mode = 'demo',
    [string]$TicketId
)

$ErrorActionPreference = 'Stop'
function Test-TaskPython {
    param([string]$Executable, [string]$ProbePath)
    try {
        # An unavailable interpreter may write stderr under Windows PowerShell.
        # A failed candidate is expected here; continue to the next candidate.
        & $Executable $ProbePath 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

$taskProbePath = Join-Path $PSScriptRoot 'scripts\check_runtime.py'
$taskCandidates = [System.Collections.Generic.List[string]]::new()
$taskVenv = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $taskVenv) { $taskCandidates.Add($taskVenv) }
foreach ($taskCommand in @('python', 'py')) {
    $taskFound = Get-Command $taskCommand -ErrorAction SilentlyContinue
    if ($taskFound) { $taskCandidates.Add($taskFound.Source) }
}
$taskBundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (Test-Path -LiteralPath $taskBundledPython) { $taskCandidates.Add($taskBundledPython) }
$taskPython = $null
foreach ($taskCandidate in $taskCandidates) {
    if (Test-TaskPython -Executable $taskCandidate -ProbePath $taskProbePath) {
        $taskPython = $taskCandidate
        break
    }
}
if (-not $taskPython) {
    throw 'Python 3.11+ with Pydantic 2 was not found. Follow README setup instructions.'
}
$taskArguments = @('-m', 'triage', '--mode', $Mode, '--trace', '--output', (Join-Path $PSScriptRoot "runs\$Mode.json"))
if ($TicketId) { $taskArguments += @('--ticket-id', $TicketId) }
Push-Location -LiteralPath $PSScriptRoot
$taskSavedErrorPreference = $ErrorActionPreference
$taskSavedNativePreference = $PSNativeCommandUseErrorActionPreference
$taskSavedConsoleEncoding = [Console]::OutputEncoding
$taskSavedOutputEncoding = $OutputEncoding
try {
    # Python emits UTF-8. Decode its native output with the same encoding.
    [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
    $OutputEncoding = [Console]::OutputEncoding
    # Present application stderr as readable text and preserve its exit code.
    $ErrorActionPreference = 'Continue'
    $PSNativeCommandUseErrorActionPreference = $false
    & $taskPython @taskArguments 2>&1 | ForEach-Object { Write-Output $_.ToString() }
    $taskExit = $LASTEXITCODE
} finally {
    $ErrorActionPreference = $taskSavedErrorPreference
    $PSNativeCommandUseErrorActionPreference = $taskSavedNativePreference
    [Console]::OutputEncoding = $taskSavedConsoleEncoding
    $OutputEncoding = $taskSavedOutputEncoding
    Pop-Location
}
exit $taskExit
