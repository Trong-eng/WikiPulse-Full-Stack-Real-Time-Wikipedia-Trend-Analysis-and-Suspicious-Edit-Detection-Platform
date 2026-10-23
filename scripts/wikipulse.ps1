<#
.SYNOPSIS
Bản thay thế `make` cho Windows (PowerShell 5.1 trở lên).

.DESCRIPTION
Trên Windows thường không có `make`, và Makefile dùng đường dẫn kiểu Linux
(`.venv/bin/python`, `python3`), nên chạy không được (BL-THANH-06). Script này có
các target tương ứng Makefile (thêm `help` liệt kê target), gọi đúng các lệnh
`docker compose` và `.venv\Scripts\python` tương ứng; riêng `install` không tạo `.venv`.

Script không tạo `.venv`: cần tạo trước ở thư mục gốc repo (vd. `python -m venv .venv`
bằng Python 3.11/3.12), sau đó `install` cài thư viện vào đó. Target cần `.venv` sẽ báo
lỗi rõ ràng nếu chưa có. Riêng `smoke` đặt `PYTHONUTF8=1` trong lúc chạy để tránh lỗi
mã hoá cp1252 trên Windows (BL-THANH-11).

Script tự chuyển vào thư mục gốc của repo nên gọi được từ bất kỳ đâu. Mã thoát của
lệnh bị lỗi được trả nguyên ra ngoài; target không tồn tại hoặc thiếu `.venv` trả mã 2,
không tìm thấy chương trình (vd. `docker`) trả mã 127.

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts\wikipulse.ps1 test
Windows mặc định chặn chạy file .ps1; `-ExecutionPolicy Bypass` chỉ bỏ chặn cho lần gọi này.

.EXAMPLE
.\scripts\wikipulse.ps1 up
Gọi trực tiếp, khi execution policy của máy đã cho phép (vd. RemoteSigned).
#>
param(
    [Parameter(Position = 0)]
    [string]$Target = "help"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$VenvRuff = Join-Path $RepoRoot ".venv\Scripts\ruff.exe"
$Targets = "help", "install", "build", "up", "init", "replay", "down", "logs", "config",
    "test", "test-spark", "lint", "smoke"

function Invoke-Native {
    <# Chạy một chương trình ngoài; nếu mã thoát khác 0 thì thoát script với đúng mã đó. #>
    param([string]$Exe, [string[]]$Arguments = @())
    if (-not (Get-Command $Exe -ErrorAction SilentlyContinue)) {
        # Không có chương trình thì `$LASTEXITCODE` giữ giá trị cũ; thoát 127 như shell Unix.
        Write-Host "Command not found: $Exe" -ForegroundColor Red
        exit 127
    }
    Write-Host "> $Exe $($Arguments -join ' ')" -ForegroundColor DarkGray
    # PowerShell 5.1: khi output bị chuyển hướng (vd. `*> file`), stderr của docker/pytest
    # thành lỗi; với "Stop" script sẽ dừng giữa chừng. Chỉ dựa vào mã thoát để phát hiện lỗi.
    $ErrorActionPreference = "Continue"
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

function Assert-Venv {
    <# Thoát mã 2 với hướng dẫn khi chưa có .venv ở thư mục gốc repo. #>
    if (-not (Test-Path $VenvPython)) {
        Write-Host "Missing .venv in repo root; create it first: python -m venv .venv" -ForegroundColor Red
        exit 2
    }
}

Push-Location $RepoRoot
try {
    switch ($Target) {
        "help" {
            Write-Host "Usage: .\scripts\wikipulse.ps1 <target>"
            Write-Host ("Targets: " + ($Targets -join " | "))
        }
        "install" {
            Assert-Venv
            Invoke-Native $VenvPython @("-m", "pip", "install", "-e", ".[dev]", "-r", "dashboard/requirements.txt")
        }
        "build" { Invoke-Native "docker" @("compose", "build", "api", "spark", "dashboard", "replay") }
        "up" { Invoke-Native "docker" @("compose", "up", "-d", "--build", "api", "spark", "dashboard") }
        "init" {
            Invoke-Native "docker" @("compose", "run", "--rm", "init-topics")
            Invoke-Native "docker" @("compose", "run", "--rm", "init-cassandra")
        }
        "replay" { Invoke-Native "docker" @("compose", "run", "--rm", "replay") }
        "down" { Invoke-Native "docker" @("compose", "down") }
        "logs" { Invoke-Native "docker" @("compose", "logs", "--tail=100", "-f") }
        "config" { Invoke-Native "docker" @("compose", "config", "--quiet") }
        "test" {
            Assert-Venv
            Invoke-Native $VenvPython @("-m", "pytest", "-q", "-m", "not integration and not spark")
        }
        "test-spark" {
            Invoke-Native "docker" @("compose", "run", "--rm", "--no-deps", "spark", "python", "-m", "pytest", "processing/spark/tests", "-q")
        }
        "lint" {
            Assert-Venv
            Invoke-Native $VenvRuff @("check", ".")
        }
        "smoke" {
            Assert-Venv
            $previous = $env:PYTHONUTF8
            $env:PYTHONUTF8 = "1"
            try {
                Invoke-Native $VenvPython @("scripts/smoke_test.py")
            }
            finally {
                $env:PYTHONUTF8 = $previous
            }
        }
        default {
            Write-Host "Unknown target '$Target'. Targets: $($Targets -join ' | ')" -ForegroundColor Red
            exit 2
        }
    }
}
finally {
    Pop-Location
}
