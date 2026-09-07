# Loads key=value pairs from the repo-root .env into the current PowerShell session.
# Dot-source it so the variables stay set:   . .\scripts\load-env.ps1

$envPath = Join-Path $PSScriptRoot '..\.env'
if (-not (Test-Path $envPath)) {
    Write-Error "No .env found at $envPath"
    return
}

Get-Content $envPath |
    Where-Object { $_ -match '^\s*[^#].*=' } |
    ForEach-Object {
        $name, $value = $_ -split '=', 2
        [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), 'Process')
    }

Write-Host "Loaded .env into this session."
