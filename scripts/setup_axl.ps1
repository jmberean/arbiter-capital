# Arbiter Capital - AXL Mesh Launcher (PowerShell)
# Launches 5 AXL bridge nodes to form a local decentralized mesh.

$Ports = @(9001, 9002, 9003, 9004, 9005)
$NodeIds = @("Quant_Node_A", "Patriarch_Node_B", "Execution_Node_P3", "KeeperHub_Sim_P4", "Adversary_Node_Z")

$Root = Get-Location
$StateDir = Join-Path $Root "state"
$LogDir = Join-Path $StateDir "axl_logs"
$ConfigDir = Join-Path $StateDir "axl_configs"
$KeyDir = Join-Path $StateDir "axl_keys"

# Ensure directories exist
if (!(Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir }
if (!(Test-Path $ConfigDir)) { New-Item -ItemType Directory -Path $ConfigDir }

Write-Host "`nStarting Arbiter Capital AXL Mesh nodes..." -ForegroundColor Cyan

# Node 1 is the Hub
$HubPeer = "tls://127.0.0.1:9001"

for ($i = 0; $i -lt $Ports.Length; $i++) {
    $NodeId = $NodeIds[$i]
    $Port = $Ports[$i]
    $ConfigFile = Join-Path $ConfigDir "$NodeId.json"
    $KeyFile = Join-Path $KeyDir "$NodeId.pem"
    
    # Peers: Everyone connects to the hub (Node 0)
    if ($i -eq 0) {
        $Peers = "[]"
    } else {
        $Peers = "[`"$HubPeer`"]"
    }

    # Generate JSON config
    $ConfigJson = @"
{
  "PrivateKeyPath": "$($KeyFile.Replace('\', '/'))",
  "Listen": ["tls://127.0.0.1:$Port"],
  "Peers": $Peers
}
"@
    $ConfigJson | Out-File -FilePath $ConfigFile -Encoding utf8

    # Start the process in the background
    $OutFile = Join-Path $LogDir "$NodeId.out.log"
    $ErrFile = Join-Path $LogDir "$NodeId.err.log"
    Start-Process -FilePath ".\axl-node.exe" -ArgumentList "-config `"$ConfigFile`"" -RedirectStandardOutput $OutFile -RedirectStandardError $ErrFile -NoNewWindow
    
    Write-Host "  [+] Started $NodeId on port $Port" -ForegroundColor Green
}

Write-Host "`nAXL Mesh is active. Logs are in state/axl_logs/." -ForegroundColor Yellow
Write-Host "To stop the mesh: taskkill /F /IM axl-node.exe" -ForegroundColor Gray
