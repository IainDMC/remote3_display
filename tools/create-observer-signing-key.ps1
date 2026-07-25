# Creates the private Android signing key used by GitHub releases.
# Run once, keep the generated JKS file and passwords in a secure backup,
# then add the four printed values as GitHub Actions repository secrets.

$ErrorActionPreference = "Stop"
$keytool = Get-Command keytool.exe -ErrorAction Stop
$output = Join-Path $PSScriptRoot "observer-release.jks"

if (Test-Path -LiteralPath $output) {
    throw "Signing key already exists at $output. It was not overwritten."
}

$storePassword = Read-Host "Create a keystore password"
$keyPassword = Read-Host "Create a key password"
$alias = "tivimate-observer"

if ($storePassword.Length -lt 6 -or $keyPassword.Length -lt 6) {
    throw "Android keystore passwords must contain at least six characters."
}

& $keytool.Source `
    -genkeypair `
    -keystore $output `
    -storepass $storePassword `
    -keypass $keyPassword `
    -alias $alias `
    -keyalg RSA `
    -keysize 3072 `
    -validity 10000 `
    -dname "CN=TiviMate Observer, O=Remote 3 Media Display"

if ($LASTEXITCODE -ne 0) {
    throw "keytool could not create the signing key."
}

$base64 = [Convert]::ToBase64String(
    [System.IO.File]::ReadAllBytes($output)
)

Write-Host ""
Write-Host "Add these GitHub Actions repository secrets:"
Write-Host "OBSERVER_KEYSTORE_BASE64=$base64"
Write-Host "OBSERVER_KEYSTORE_PASSWORD=$storePassword"
Write-Host "OBSERVER_KEY_ALIAS=$alias"
Write-Host "OBSERVER_KEY_PASSWORD=$keyPassword"
Write-Host ""
Write-Host "Back up this file securely and never commit it:"
Write-Host $output
