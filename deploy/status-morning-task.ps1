# One dated task only; Render and Check have no registration or product effects.
[CmdletBinding()]
param(
    [ValidateSet('Render', 'Check', 'Register', 'VerifyRegistered')]
    [string]$Mode = 'Check',
    [string]$ExpectedCommit = ''
)

$ErrorActionPreference = 'Stop'
$worktree = 'C:\Users\DW\orca\workspaces\oil-agent\oil-v01-i'
$taskName = 'OilAgent-StatusMorning-20260913'
$launchAt = [DateTimeOffset]::Parse('2026-09-13T07:58:00+08:00')
$stopAt = [DateTimeOffset]::Parse('2026-09-13T08:15:00+08:00')
$registrationAttempted = $false

function New-MorningDefinition($service) {
    $definition = $service.NewTask(0)
    $definition.RegistrationInfo.Description = 'One dated personal nonmarket trial status; no repetition or catch-up.'
    $definition.Principal.UserId = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $definition.Principal.LogonType = 3 # Existing interactive token, no stored password.
    $definition.Principal.RunLevel = 0 # Least privilege.
    $definition.Settings.MultipleInstances = 2 # IgnoreNew.
    $definition.Settings.StartWhenAvailable = $false
    $definition.Settings.AllowDemandStart = $false
    $definition.Settings.WakeToRun = $true
    $definition.Settings.ExecutionTimeLimit = 'PT17M'
    $definition.Settings.RestartCount = 0
    $definition.Settings.DisallowStartIfOnBatteries = $false
    $definition.Settings.StopIfGoingOnBatteries = $false
    $definition.Settings.IdleSettings.StopOnIdleEnd = $false
    $trigger = $definition.Triggers.Create(1) # One TIME trigger, no repetition.
    $trigger.StartBoundary = '2026-09-13T07:58:00+08:00'
    $trigger.EndBoundary = '2026-09-13T08:00:00+08:00'
    $trigger.Enabled = $true
    $action = $definition.Actions.Create(0)
    $action.Path = Join-Path $worktree '.venv\Scripts\python.exe'
    $action.Arguments = '-I -B -m oil_agent.runtime.status_local morning'
    $action.WorkingDirectory = $worktree
    return $definition
}

function Assert-IntegratedSource {
    if ($ExpectedCommit -cnotmatch '\A[0-9a-f]{40}\z') {
        throw 'STATUS_EXPECTED_SOURCE_REQUIRED'
    }
    $head = & git -C $worktree rev-parse HEAD 2>$null
    if ($LASTEXITCODE -ne 0 -or $head -cne $ExpectedCommit) { throw 'STATUS_SOURCE_MISMATCH' }
    $branch = & git -C $worktree branch --show-current 2>$null
    if ($LASTEXITCODE -ne 0 -or $branch -cne 'songconmaisaix31-design/oil-v01-i') {
        throw 'STATUS_SOURCE_MISMATCH'
    }
    $dirty = & git -C $worktree status --porcelain 2>$null
    if ($LASTEXITCODE -ne 0 -or $dirty) { throw 'STATUS_SOURCE_DIRTY' }
    foreach ($relative in @('.venv\Scripts\python.exe', 'src\oil_agent\runtime\status_local.py')) {
        if (-not (Test-Path -LiteralPath (Join-Path $worktree $relative) -PathType Leaf)) {
            throw 'STATUS_ENTRY_UNAVAILABLE'
        }
    }
    # Presence is a deployment prerequisite, not acceptance of the module's behavior.
}

function Get-ExactTask($folder) {
    try { return $folder.GetTask($taskName) }
    catch {
        if ($_.Exception.HResult -eq -2147024894) { return $null } # Exact name not found.
        throw 'STATUS_TASK_QUERY_FAILED'
    }
}

function Assert-RegisteredDefinition($actual, $expected) {
    if (-not $actual -or -not $actual.Enabled) { throw 'STATUS_TASK_NOT_REGISTERED' }
    [xml]$actualXml = $actual.Xml
    [xml]$expectedXml = $expected.XmlText
    foreach ($section in @('Principals', 'Triggers', 'Actions', 'Settings')) {
        if ($actualXml.Task.$section.OuterXml -cne $expectedXml.Task.$section.OuterXml) {
            throw 'STATUS_TASK_MISMATCH'
        }
    }
}

try {
    $service = New-Object -ComObject 'Schedule.Service'
    $service.Connect()
    $definition = New-MorningDefinition $service
    if ($Mode -eq 'Render') {
        # Task Scheduler's actual in-memory COM definition; never RegisterTaskDefinition.
        $definition.XmlText
        exit 0
    }
    Assert-IntegratedSource
    $now = [DateTimeOffset]::UtcNow
    if ($now -lt $launchAt.AddHours(-8) -or $now -ge $stopAt) { throw 'STATUS_TIME_WINDOW' }
    $folder = $service.GetFolder('\')
    $existing = Get-ExactTask $folder
    if ($Mode -eq 'VerifyRegistered') {
        Assert-RegisteredDefinition $existing $definition
        @{ status = 'STATUS_TASK_DEFINITION_VERIFIED'; task = $taskName } | ConvertTo-Json -Compress
        exit 0
    }
    if ($existing) { throw 'STATUS_TASK_COLLISION' }
    if ($now -ge $launchAt) { throw 'STATUS_TIME_WINDOW' }
    if ($Mode -eq 'Register') {
        # TASK_CREATE (2) refuses a same-name race; no update, force, retry or manual Run.
        $registrationAttempted = $true
        $registered = $folder.RegisterTaskDefinition($taskName, $definition, 2, $null, $null, 3, $null)
        Assert-RegisteredDefinition $registered $definition
        @{ status = 'STATUS_TASK_REGISTERED'; task = $taskName } | ConvertTo-Json -Compress
    } else {
        @{ status = 'STATUS_TASK_PREREQUISITES_VERIFIED'; registered = $false; task = $taskName } |
            ConvertTo-Json -Compress
    }
    exit 0
} catch {
    $status = $_.Exception.Message
    if ($status -cnotmatch '\ASTATUS_[A-Z_]+\z') { $status = 'STATUS_TASK_FAILED' }
    # A failed registration/readback is not proof of absence; inspect this exact task before retry.
    if ($registrationAttempted) { $status = 'STATUS_TASK_EFFECT_UNKNOWN' }
    @{ status = $status } | ConvertTo-Json -Compress
    exit 2
}
