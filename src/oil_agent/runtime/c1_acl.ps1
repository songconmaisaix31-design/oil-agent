# Fixed Oil Agent path only. No private data is interpreted as script or arguments.
param([ValidateSet('prepare', 'verify')][string]$Mode = 'verify')
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$script:field = 'windows_acl'
try {
    # Do not inherit a PowerShell 7 parent's module search path in Windows PS 5.
    Import-Module (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Security\Microsoft.PowerShell.Security.psd1') -ErrorAction Stop
    $currentSid = [Security.Principal.WindowsIdentity]::GetCurrent().User
    $systemSid = [Security.Principal.SecurityIdentifier]::new('S-1-5-18')
    $localRoot = [Environment]::GetFolderPath('LocalApplicationData')
    $targetPath = [IO.Path]::GetFullPath((Join-Path $localRoot 'oil-agent\private\feishu-c1'))
    if ($targetPath -ne 'C:\Users\DW\AppData\Local\oil-agent\private\feishu-c1') { throw 'path' }

    # Inspect only the ancestry of the explicitly approved project directory.
    $ancestor = [IO.DirectoryInfo]::new($localRoot)
    while ($null -ne $ancestor) {
        if (-not $ancestor.Exists -or ($ancestor.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'path' }
        if (Test-Path -LiteralPath (Join-Path $ancestor.FullName '.git')) { throw 'path' }
        $ancestor = $ancestor.Parent
    }

    function Assert-PrivateAcl([string]$Path) {
        $script:field = 'path_attributes'
        $item = Get-Item -LiteralPath $Path -Force
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'path' }
        $script:field = 'owner'
        $acl = Get-Acl -LiteralPath $Path
        if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $currentSid.Value) { throw 'owner' }
        $script:field = 'access_rules'
        $rules = @($acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier]))
        $allowed = @($currentSid.Value, $systemSid.Value)
        if ($rules.Count -ne 2) { throw 'acl' }
        foreach ($rule in $rules) {
            if ($rule.IdentityReference.Value -notin $allowed -or
                $rule.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow -or
                $rule.FileSystemRights -ne [Security.AccessControl.FileSystemRights]::FullControl) { throw 'acl' }
        }
        $script:field = 'unique_access_rules'
        if (@($rules | ForEach-Object { $_.IdentityReference.Value } | Select-Object -Unique).Count -ne 2) { throw 'acl' }
    }

    function New-PrivateDirectory([string]$Path) {
        # Create with its restricted descriptor, never expose inherited broad access.
        $acl = [Security.AccessControl.DirectorySecurity]::new()
        $acl.SetOwner($currentSid)
        $acl.SetAccessRuleProtection($true, $false)
        foreach ($sid in @($currentSid, $systemSid)) {
            $rule = [Security.AccessControl.FileSystemAccessRule]::new(
                $sid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
            $acl.AddAccessRule($rule)
        }
        [IO.Directory]::CreateDirectory($Path, $acl) | Out-Null
        Assert-PrivateAcl $Path
    }

    $scopePath = $localRoot
    foreach ($segment in @('oil-agent', 'private', 'feishu-c1')) {
        $scopePath = Join-Path $scopePath $segment
        if (Test-Path -LiteralPath $scopePath) {
            # No repair of existing foreign or permissive ACLs; leave unknown work intact.
            if (-not (Get-Item -LiteralPath $scopePath -Force).PSIsContainer) { throw 'path' }
            Assert-PrivateAcl $scopePath
        } elseif ($Mode -eq 'prepare') {
            New-PrivateDirectory $scopePath
        } else { throw 'missing' }
    }
    $children = @(Get-ChildItem -LiteralPath $targetPath -Force)
    foreach ($child in $children) {
        if ($child.Name -notin @('config.json', 'c1-preview.json', 'c1-preview.html') -or $child.PSIsContainer) { throw 'unknown_file' }
        Assert-PrivateAcl $child.FullName
    }
    [Console]::Out.Write('PRIVATE_PATH_VERIFIED')
} catch {
    # No path, ACL identity, exception, private value, or file content is emitted.
    $field = $script:field + '_unverified'
    if ($_.Exception.Message -in @('path', 'owner', 'acl', 'missing', 'unknown_file')) {
        $field = $_.Exception.Message
    }
    [Console]::Out.Write('PRIVATE_PATH_UNVERIFIED:' + $field)
    exit 2
}
