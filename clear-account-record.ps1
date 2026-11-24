<#
.SYNOPSIS
    پاک‌سازی رکورد محلی Multiple Account Detection ویندسکرایب

.DESCRIPTION
    ویندسکرایب مشخصات حساب منقضی‌شده (username / user ID / تاریخ) را رمزگذاری‌شده
    در کلید رجیستری زیر ذخیره می‌کند:

        HKCU\Software\Microsoft\Windows\CurrentVersion\NetControlPort

    پیاده‌سازی آن در فایل زیر است:
        src/client/frontend/frontend-common/multipleaccountdetection/secretvalue_win.cpp

    این اسکریپت هر بار که اجرا شود از کلید بکاپ می‌گیرد و سپس آن را حذف می‌کند.
    توجه: برنامه در صورت مشاهده مجدد حساب منقضی، این کلید را دوباره می‌سازد.

.PARAMETER NoBackup
    بدون گرفتن بکاپ حذف کن.

.PARAMETER BackupDir
    مسیر ذخیره بکاپ‌ها. پیش‌فرض: پوشه backups کنار همین اسکریپت.

.PARAMETER KillClient
    قبل از حذف، پروسه Windscribe را ببند (در غیر این صورت ممکن است کلید دوباره نوشته شود).

.EXAMPLE
    .\clear-account-record.ps1
    .\clear-account-record.ps1 -KillClient
    .\clear-account-record.ps1 -NoBackup
#>

[CmdletBinding()]
param(
    [switch]$NoBackup,
    [string]$BackupDir,
    [switch]$KillClient
)

$ErrorActionPreference = 'Stop'

$KeyPath     = 'Software\Microsoft\Windows\CurrentVersion\NetControlPort'
$RegPath     = "HKCU\$KeyPath"
$PsRegPath   = "HKCU:\$KeyPath"
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Step($msg)  { Write-Host "  $msg" }
function Write-Ok($msg)    { Write-Host "  [OK] $msg"   -ForegroundColor Green }
function Write-Warn2($msg) { Write-Host "  [!]  $msg"   -ForegroundColor Yellow }
function Write-Err2($msg)  { Write-Host "  [X]  $msg"   -ForegroundColor Red }

Write-Host ""
Write-Host "Windscribe - Account Record Cleaner" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host "  target: $RegPath"
Write-Host ""

# --- 1. بستن کلاینت در صورت درخواست ---------------------------------------
if ($KillClient) {
    $procs = @(Get-Process -Name 'Windscribe' -ErrorAction SilentlyContinue)
    if ($procs.Count -gt 0) {
        Write-Step "بستن $($procs.Count) پروسه Windscribe ..."
        foreach ($p in $procs) {
            try { Stop-Process -Id $p.Id -Force -ErrorAction Stop } catch { Write-Warn2 "بستن PID $($p.Id) ناموفق: $($_.Exception.Message)" }
        }
        Write-Ok "کلاینت بسته شد."
    } else {
        Write-Step "کلاینت Windscribe در حال اجرا نیست."
    }
}

# --- 2. بررسی وجود کلید ----------------------------------------------------
if (-not (Test-Path $PsRegPath)) {
    Write-Ok "رکوردی وجود ندارد - سیستم از قبل تمیز است."
    Write-Host ""
    exit 0
}

Write-Step "رکورد پیدا شد. محتوای فعلی:"
try {
    $props = Get-ItemProperty -Path $PsRegPath
    foreach ($name in @('Version', 'State')) {
        if ($null -ne $props.$name) {
            $val = $props.$name
            if ($val -is [byte[]]) {
                $hex = ($val | ForEach-Object { $_.ToString('X2') }) -join ''
                if ($hex.Length -gt 64) { $hex = $hex.Substring(0, 64) + '...' }
                Write-Host "        $name = $hex ($($val.Length) bytes, encrypted)"
            } else {
                Write-Host "        $name = $val"
            }
        }
    }
} catch {
    Write-Warn2 "خواندن مقادیر ناموفق بود: $($_.Exception.Message)"
}

# --- 3. بکاپ ---------------------------------------------------------------
if (-not $NoBackup) {
    if ([string]::IsNullOrWhiteSpace($BackupDir)) {
        $BackupDir = Join-Path $ScriptDir 'backups'
    }
    if (-not (Test-Path $BackupDir)) {
        New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
    }

    $stamp      = (Get-Date).ToString('yyyyMMdd-HHmmss')
    $backupFile = Join-Path $BackupDir "netcontrolport-$stamp.reg"

    $null = reg.exe export $RegPath $backupFile /y 2>&1
    if ($LASTEXITCODE -eq 0 -and (Test-Path $backupFile)) {
        Write-Ok "بکاپ: $backupFile"
    } else {
        Write-Err2 "گرفتن بکاپ ناموفق بود. برای حذف بدون بکاپ از -NoBackup استفاده کنید."
        Write-Host ""
        exit 1
    }
} else {
    Write-Warn2 "بکاپ گرفته نشد (-NoBackup)."
}

# --- 4. حذف ----------------------------------------------------------------
$null = reg.exe delete $RegPath /f 2>&1
$deleteExit = $LASTEXITCODE

if (Test-Path $PsRegPath) {
    Write-Err2 "حذف ناموفق بود (exit=$deleteExit). کلید هنوز وجود دارد."
    Write-Host ""
    exit 1
}

Write-Ok "رکورد حذف شد."
Write-Host ""
Write-Host "  یادآوری: این پاک‌سازی فقط محلی است. اگر کلاینت دوباره حساب" -ForegroundColor DarkGray
Write-Host "  منقضی را ببیند، همین کلید را از نو می‌سازد. وضعیت سمت سرور" -ForegroundColor DarkGray
Write-Host "  ویندسکرایب با این کار تغییر نمی‌کند." -ForegroundColor DarkGray
Write-Host ""
exit 0
