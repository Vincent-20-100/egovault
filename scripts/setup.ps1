Write-Host "=== Setup pkm-vault-app ===" -ForegroundColor Cyan

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv non trouvé. Installation..." -ForegroundColor Yellow
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
}

uv sync --dev
Copy-Item config.yaml.example config.yaml

Write-Host ""
Write-Host "Setup terminé. Éditer config.yaml :" -ForegroundColor Green
Write-Host "  vault:"
Write-Host "    data_path: `"../pkm-vault-data`""
