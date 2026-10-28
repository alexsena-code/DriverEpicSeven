param([string]$Python = "python", [switch]$WithOcr)
$ErrorActionPreference = "Stop"
$taskRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $taskRoot
try {
    if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
        & $Python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Falha ao criar o ambiente Python." }
    }
    & '.venv/Scripts/python.exe' -m pip install -e '.[dev]'
    if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar as dependências." }
    if ($WithOcr) {
        & '.venv/Scripts/python.exe' tools/install_ocr.py
        if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar o modelo OCR." }
    }
    & '.venv/Scripts/python.exe' -m driver_epic_seven validate
    if ($LASTEXITCODE -ne 0) { throw "Configuração de recursos inválida." }
} finally {
    Pop-Location
}
