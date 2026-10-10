param(
    [ValidateSet('demo', 'openai')][string]$Mode = 'demo',
    [string]$TicketId
)

$ErrorActionPreference = 'Stop'
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
    & $taskCandidate -c 'import sys, pydantic; assert sys.version_info >= (3, 11); assert int(pydantic.__version__.split(".")[0]) == 2' 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $taskPython = $taskCandidate; break }
}
if (-not $taskPython) {
    throw 'Python 3.11+ with Pydantic 2 was not found. Follow README setup instructions.'
}
$taskArguments = @('-m', 'triage', '--mode', $Mode, '--trace', '--output', (Join-Path $PSScriptRoot "runs\$Mode.json"))
if ($TicketId) { $taskArguments += @('--ticket-id', $TicketId) }
Push-Location -LiteralPath $PSScriptRoot
try {
    & $taskPython @taskArguments
    $taskExit = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $taskExit
