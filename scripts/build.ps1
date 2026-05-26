$root    = Split-Path $PSScriptRoot -Parent
$release = "$root\release"

Set-Location $root

Write-Host "Building..."
& "$root\.venv\Scripts\pyinstaller.exe" --clean `
    --distpath "$root\dist" `
    --workpath "$root\build" `
    "$root\tacet.spec"
if ($LASTEXITCODE -ne 0) { Write-Host "Build failed."; exit 1 }

Write-Host "Stopping any running instance..."
Get-Process -Name "TacetHealthCare" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1

Write-Host "Copying to release folder..."
if (Test-Path $release) { Remove-Item $release -Recurse -Force }
New-Item -ItemType Directory -Path $release | Out-Null
Copy-Item -Path "$root\dist\TacetHealthCare\*" -Destination $release -Recurse

Write-Host "Cleaning up build artifacts..."
Remove-Item "$root\build", "$root\dist" -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Done. Release folder: $release"
