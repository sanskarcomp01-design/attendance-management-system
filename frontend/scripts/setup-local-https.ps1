$ErrorActionPreference = "Stop"

$frontendDir = Split-Path -Parent $PSScriptRoot
$certificateDir = Join-Path $frontendDir "certs"
$pfxPath = Join-Path $certificateDir "attendance-local.pfx"
$pfxPasswordPath = Join-Path $certificateDir "attendance-local-password.txt"
$rootPath = Join-Path $certificateDir "attendance-local-root.cer"
$rootSubject = "CN=SPPU Attendance Local HTTPS Root"

$adapter = Get-NetIPConfiguration |
    Where-Object {
        $_.IPv4Address -and
        $_.IPv4Address.IPAddress -notlike "127.*" -and
        $_.IPv4Address.IPAddress -notlike "169.254.*" -and
        $_.NetAdapter.Status -eq "Up"
    } |
    Sort-Object {
        if ($_.InterfaceAlias -match "Wi-Fi|Wireless") { 0 } else { 1 }
    } |
    Select-Object -First 1

if (-not $adapter) {
    throw "No active LAN/Wi-Fi IPv4 address found. Connect the laptop to Wi-Fi or your phone hotspot and retry."
}
$ip = [System.Net.IPAddress]::Parse($adapter.IPv4Address.IPAddress)
if ($ip.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) {
    throw "The selected address is not IPv4."
}

New-Item -ItemType Directory -Force -Path $certificateDir | Out-Null

$root = Get-ChildItem Cert:\CurrentUser\My |
    Where-Object { $_.Subject -eq $rootSubject -and $_.HasPrivateKey -and $_.NotAfter -gt (Get-Date).AddDays(30) } |
    Sort-Object NotAfter -Descending |
    Select-Object -First 1

if (-not $root) {
    $root = New-SelfSignedCertificate `
        -Subject $rootSubject `
        -CertStoreLocation Cert:\CurrentUser\My `
        -KeyAlgorithm RSA `
        -KeyLength 3072 `
        -HashAlgorithm SHA256 `
        -KeyUsage CertSign, CRLSign, DigitalSignature `
        -TextExtension @("2.5.29.19={critical}{text}ca=1&pathlength=0") `
        -NotAfter (Get-Date).AddYears(5)
}

Export-Certificate -Cert $root -FilePath $rootPath -Force | Out-Null
Import-Certificate -FilePath $rootPath -CertStoreLocation Cert:\CurrentUser\Root | Out-Null

$leaf = $null
if (Test-Path -LiteralPath $pfxPath) {
    $existingPassword = if (Test-Path -LiteralPath $pfxPasswordPath) {
        (Get-Content -LiteralPath $pfxPasswordPath -Raw).Trim()
    } else {
        ""
    }
    if (-not $existingPassword) {
        $existingPassword = $null
    }
    $existingPfx = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new(
        $pfxPath,
        $existingPassword,
        [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::EphemeralKeySet
    )
    $san = $existingPfx.Extensions |
        Where-Object { $_.Oid.Value -eq "2.5.29.17" } |
        Select-Object -First 1
    if (
        $existingPfx.NotAfter -gt (Get-Date).AddDays(30) -and
        $existingPfx.Issuer -eq $root.Subject -and
        $san -and $san.Format($false).Contains($ip.ToString())
    ) {
        $leaf = $existingPfx
    }
}

if (-not $leaf) {
    $leaf = New-SelfSignedCertificate `
        -Subject "CN=$ip" `
        -Signer $root `
        -CertStoreLocation Cert:\CurrentUser\My `
        -KeyAlgorithm RSA `
        -KeyLength 2048 `
        -HashAlgorithm SHA256 `
        -KeyUsage DigitalSignature, KeyEncipherment `
        -TextExtension @("2.5.29.17={text}IPAddress=$ip&DNS=localhost&DNS=127.0.0.1") `
        -NotAfter (Get-Date).AddYears(1)
    $passwordBytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($passwordBytes)
    $passwordText = [Convert]::ToBase64String($passwordBytes)
    [System.IO.File]::WriteAllText($pfxPasswordPath, $passwordText)
    $password = ConvertTo-SecureString -String $passwordText -AsPlainText -Force
    Export-PfxCertificate -Cert $leaf -FilePath $pfxPath -Password $password -Force | Out-Null
}

Write-Host ""
Write-Host "Local HTTPS certificate is ready for $ip."
Write-Host "Presentation URL: https://${ip}:5173"
Write-Host "Teacher sign-in: https://${ip}:5173/login"
Write-Host "Copy the phone certificate from: $rootPath"
$sha256 = [System.Security.Cryptography.SHA256]::Create()
$fingerprint = [BitConverter]::ToString($sha256.ComputeHash([System.IO.File]::ReadAllBytes($rootPath))).Replace("-", "")
Write-Host "Certificate SHA-256: $fingerprint"
