# Brightloop dev helper: one command for the whole upgrade / test / push loop.
#
# Usage (from anywhere):
#   powershell -ExecutionPolicy Bypass -File C:\dev\Odoo-hackathon\tools\dev.ps1 all "commit message"
#
# Commands:
#   test     upgrade the module + run its tests (log saved next to docker-compose.yml)
#   restart  restart the running Odoo so the browser uses the new code
#   push     git add, commit, pull --rebase, push
#   all      test -> restart -> push (push only if tests pass)
#
# Each teammate sets their own docker-compose folder once:
#   [Environment]::SetEnvironmentVariable("BRIGHTLOOP_COMPOSE", "C:\dev\odoo-docker", "User")

param(
    [ValidateSet("test", "restart", "push", "all")]
    [string]$Command = "all",
    [string]$Message = "update"
)

$Repo = Split-Path -Parent $PSScriptRoot
$Compose = $env:BRIGHTLOOP_COMPOSE
if (-not $Compose) { $Compose = "C:\dev\brightloop\addons" }
$Log = Join-Path $Compose "last-test.log"
$Db = "brightloop"
$Module = "brightloop_subscription"

function Invoke-Tests {
    Write-Host "==> Upgrading $Module and running tests (log: $Log)" -ForegroundColor Cyan
    Push-Location $Compose
    try {
        docker compose exec -T odoo odoo -d $Db --db_host db --db_user odoo --db_password odoo `
            -u $Module --test-tags "/$Module" --stop-after-init --http-port 8071 2>&1 |
            Tee-Object -FilePath $Log | Out-Null
    } finally { Pop-Location }

    $summary = Select-String -Path $Log -Pattern "failed, \d+ error\(s\) of \d+ tests" | Select-Object -Last 1
    $loadError = Select-String -Path $Log -Pattern "CRITICAL|ParseError|Traceback" | Select-Object -First 1
    if ($summary -and $summary.Line -match " 0 failed, 0 error") {
        Write-Host "==> TESTS PASSED: $($summary.Line.Trim())" -ForegroundColor Green
        return $true
    }
    if ($summary) { Write-Host "==> TESTS FAILED: $($summary.Line.Trim())" -ForegroundColor Red }
    elseif ($loadError) { Write-Host "==> MODULE FAILED TO LOAD: $($loadError.Line.Trim())" -ForegroundColor Red }
    else { Write-Host "==> No test summary found; check the log." -ForegroundColor Red }
    return $false
}

function Restart-Odoo {
    Write-Host "==> Restarting Odoo" -ForegroundColor Cyan
    Push-Location $Compose
    try { docker compose restart odoo | Out-Null } finally { Pop-Location }
    Write-Host "==> Odoo restarted. Give it ~15 seconds." -ForegroundColor Green
}

function Push-Code {
    Write-Host "==> Committing and pushing: $Message" -ForegroundColor Cyan
    git -C $Repo add -A
    git -C $Repo commit -m $Message
    git -C $Repo pull --rebase
    git -C $Repo push
    Write-Host "==> Pushed. Latest commit:" -ForegroundColor Green
    git -C $Repo log --oneline -1
}

switch ($Command) {
    "test"    { [void](Invoke-Tests) }
    "restart" { Restart-Odoo }
    "push"    { Push-Code }
    "all" {
        $ok = Invoke-Tests
        Restart-Odoo
        if ($ok) { Push-Code }
        else { Write-Host "==> Not pushing because tests did not pass." -ForegroundColor Yellow }
    }
}
