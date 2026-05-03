# deploy.ps1 -- Run from repo root: .\scripts\deploy.ps1
#
# Flags:
#   (none)              verify ThrottleHook + deploy ArbiterReceipt + update .env
#   -SkipVerifyHook     skip ThrottleHook verification
#   -SkipReceipt        skip ArbiterReceipt deployment
#   -VerifyReceipt      ONLY retry ArbiterReceipt Etherscan verification
param(
    [switch]$SkipVerifyHook,
    [switch]$SkipReceipt,
    [switch]$VerifyReceipt
)

Set-StrictMode -Off
$ErrorActionPreference = "Continue"
if ($env:PATH -notlike "*C:\foundry*") { $env:PATH += ";C:\foundry" }

function Read-EnvVar([string]$key) {
    $line = Get-Content .env | Where-Object { $_ -match "^${key}=" } | Select-Object -First 1
    if ($line) { return ($line -split '=', 2)[1].Trim() }
    return $null
}

# Quick path: just verify ArbiterReceipt
if ($VerifyReceipt) {
    Write-Host "[verify] Verifying ArbiterReceipt..." -ForegroundColor Cyan
    $receiptAddr  = Read-EnvVar 'ARBITER_RECEIPT_NFT'
    $safeAddr     = Read-EnvVar 'SAFE_ADDRESS'
    $etherscanKey = Read-EnvVar 'ETHERSCAN_API_KEY'
    $executorAddr = '0xba57aad97610F0415cfe6D5B017742350E328039'

    if (-not $receiptAddr) {
        Write-Host "ERROR: ARBITER_RECEIPT_NFT missing from .env" -ForegroundColor Red
        exit 1
    }

    $ctorArgs = & cast 'abi-encode' 'constructor(address,address)' $safeAddr $executorAddr
    & forge 'verify-contract' $receiptAddr `
        'contracts/ArbiterReceipt.sol:ArbiterReceipt' `
        '--chain' 'sepolia' `
        '--etherscan-api-key' $etherscanKey `
        '--constructor-args' $ctorArgs

    if ($LASTEXITCODE -eq 0) {
        Write-Host "ArbiterReceipt verified!" -ForegroundColor Green
    } else {
        Write-Host "Etherscan still indexing - wait 30s and retry." -ForegroundColor Yellow
    }
    exit 0
}

# Full flow
Write-Host "[1/3] Loading .env..." -ForegroundColor Cyan
$rpc          = Read-EnvVar 'SEPOLIA_RPC'
$deployer     = Read-EnvVar 'DEPLOYER_KEY'
$etherscan    = Read-EnvVar 'ETHERSCAN_API_KEY'
$hookAddr     = Read-EnvVar 'ARBITER_THROTTLE_HOOK'
$safeAddr     = Read-EnvVar 'SAFE_ADDRESS'
$executorAddr = '0xba57aad97610F0415cfe6D5B017742350E328039'

$required = @{ SEPOLIA_RPC=$rpc; DEPLOYER_KEY=$deployer; ETHERSCAN_API_KEY=$etherscan; ARBITER_THROTTLE_HOOK=$hookAddr; SAFE_ADDRESS=$safeAddr }
foreach ($k in $required.Keys) {
    if (-not $required[$k]) { Write-Host "ERROR: $k not set in .env" -ForegroundColor Red; exit 1 }
}
Write-Host "  All required vars present." -ForegroundColor DarkGray

# [2/3] Verify ArbiterThrottleHook
if (-not $SkipVerifyHook) {
    Write-Host "[2/3] Verifying ArbiterThrottleHook ($hookAddr)..." -ForegroundColor Cyan
    $ctorArgs = & cast 'abi-encode' 'constructor(address,address,uint32,uint32,uint128)' `
        '0x000000000004444c5dc75cb358380d2e3de08a90' $safeAddr '60' '3600' '10000000000000000000'
    & forge 'verify-contract' $hookAddr `
        'contracts/ArbiterThrottleHook.sol:ArbiterThrottleHook' `
        '--chain' 'sepolia' '--etherscan-api-key' $etherscan '--constructor-args' $ctorArgs
    if ($LASTEXITCODE -eq 0) {
        Write-Host "ThrottleHook verified!" -ForegroundColor Green
    } else {
        Write-Host "Verification failed (may already be verified). Continuing..." -ForegroundColor Yellow
    }
} else {
    Write-Host "[2/3] Skipping hook verification (-SkipVerifyHook)" -ForegroundColor Yellow
}

# [3/3] Deploy ArbiterReceipt
if (-not $SkipReceipt) {
    Write-Host "[3/3] Deploying ArbiterReceipt..." -ForegroundColor Cyan
    $output = & forge 'script' 'script/DeployArbiterReceipt.s.sol' `
        '--rpc-url' $rpc '--private-key' $deployer '--broadcast' '--verify' 2>&1
    Write-Host ($output -join "`n")

    $combined = $output -join "`n"
    $match = [regex]::Match($combined, 'ArbiterReceipt deployed: (0x[0-9a-fA-F]{40})')
    if ($match.Success) {
        $addr = $match.Groups[1].Value
        Write-Host "Deployed: $addr" -ForegroundColor Green
        $envContent = Get-Content .env -Raw -Encoding utf8
        if ($envContent -match 'ARBITER_RECEIPT_NFT=') {
            $envContent = [regex]::Replace($envContent, 'ARBITER_RECEIPT_NFT=\S+', "ARBITER_RECEIPT_NFT=$addr")
        } else {
            $envContent = $envContent.TrimEnd() + "`nARBITER_RECEIPT_NFT=$addr`n"
        }
        [System.IO.File]::WriteAllText((Resolve-Path .env), $envContent, [System.Text.Encoding]::UTF8)
        Write-Host "ARBITER_RECEIPT_NFT=$addr written to .env" -ForegroundColor Green
    } else {
        Write-Host "Could not parse address - add ARBITER_RECEIPT_NFT to .env manually." -ForegroundColor Yellow
    }
} else {
    Write-Host "[3/3] Skipping ArbiterReceipt deploy (-SkipReceipt)" -ForegroundColor Yellow
}

Write-Host "Done." -ForegroundColor Green
