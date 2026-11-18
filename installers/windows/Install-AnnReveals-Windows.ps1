param(
    [string]$AppUrl
)

$ErrorActionPreference = 'Stop'
if (-not $AppUrl) {
    $AppUrl = Read-Host 'Enter your hosted Ann Reveals HTTPS address'
}

$address = $null
if (-not [Uri]::TryCreate($AppUrl.Trim(), [UriKind]::Absolute, [ref]$address) -or
    $address.Scheme -ne 'https' -or -not $address.Host -or $address.UserInfo) {
    throw 'Enter an HTTPS address without embedded credentials.'
}

$shortcutName = 'Ann Reveals AI Manager.url'
$shortcut = "[InternetShortcut]`r`nURL=$($address.AbsoluteUri)"
foreach ($folder in @(
    [Environment]::GetFolderPath('Desktop'),
    [Environment]::GetFolderPath('Programs')
)) {
    if (-not $folder) {
        throw 'Windows did not return the Desktop or Start Menu folder.'
    }
    Set-Content -LiteralPath (Join-Path $folder $shortcutName) -Value $shortcut -Encoding Ascii
}

Write-Host 'Ann Reveals shortcuts are available on the Desktop and Start menu.'
Start-Process -FilePath $address.AbsoluteUri
