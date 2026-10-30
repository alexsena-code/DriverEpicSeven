param([string]$Python = "python", [switch]$WithOcr)
$ErrorActionPreference = "Stop"
$taskRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $taskRoot
try {
    $taskPython = $Python
    if (Test-Path -LiteralPath '.venv/Scripts/python.exe') {
        $taskPython = '.venv/Scripts/python.exe'
    }
    & $taskPython -c "import sys, struct; sys.exit(0 if sys.platform == 'win32' and (3, 11) <= sys.version_info[:2] < (3, 13) and struct.calcsize('P') == 8 else 'Requer Windows e Python 3.11 ou 3.12 de 64 bits.')"
    if ($LASTEXITCODE -ne 0) { throw "Python incompatível. Informe o caminho do Python 3.11/3.12 de 64 bits em -Python." }
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
