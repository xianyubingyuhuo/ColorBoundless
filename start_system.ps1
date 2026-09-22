# start_system.ps1 · ColorBoundless 一键启动/停止
# 用法：
#   .\start_system.ps1            启动系统（后端已在运行则跳过）+ 就绪后打开浏览器
#   .\start_system.ps1 -NoBrowser 启动但不弹浏览器
#   .\start_system.ps1 -Stop      停止后端
param(
    [switch]$Stop,
    [switch]$NoBrowser
)
$ErrorActionPreference = "SilentlyContinue"
$ProgressPreference = "SilentlyContinue"   # 抑制 Invoke-WebRequest 进度条噪音
$Root = $PSScriptRoot
$Py   = "E:\作业\欧莱雅比赛项目\.venv\Scripts\python.exe"
$Port = 8000
$Url  = "http://127.0.0.1:$Port"

function Get-BackendPid {
    $c = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($c) { return $c[0].OwningProcess }
    return $null
}
function Test-Backend {
    try {
        $r = Invoke-WebRequest -Uri "$Url/" -UseBasicParsing -TimeoutSec 3
        return ($r.StatusCode -eq 200)
    } catch { return $false }
}

if ($Stop) {
    $bp = Get-BackendPid
    if ($bp) {
        Stop-Process -Id $bp -Force
        Write-Host "[OK] 后端已停止（pid=$bp）"
    } else {
        Write-Host "[--] 后端未在运行"
    }
    exit 0
}

$bp = Get-BackendPid
if ($bp) {
    Write-Host "[--] 后端已在运行（pid=$bp），跳过启动"
} else {
    Write-Host "[..] 启动后端（向量模型预热约 60s，请稍候）…"
    Start-Process -FilePath $Py `
        -ArgumentList "-m","uvicorn","main:app","--app-dir","app\backend","--host","127.0.0.1","--port","$Port" `
        -WorkingDirectory $Root `
        -RedirectStandardOutput "$Root\_backend.log" `
        -RedirectStandardError  "$Root\_backend_err.log" `
        -WindowStyle Hidden
}

# 就绪轮询（最多 100s：bge 预热约 60s + torch 导入约 10-20s）
$ready = $false
for ($i = 1; $i -le 50; $i++) {
    Start-Sleep -Seconds 2
    if (Test-Backend) { $ready = $true; break }
    if ($i % 5 -eq 0) { Write-Host "     …等待服务就绪（$($i * 2)s）" }
}
if ($ready) {
    Write-Host "[OK] 系统就绪：$Url"
    Write-Host "     主页   $Url/"
    Write-Host "     试妆页 $Url/tryon.html"
    Write-Host "     产品库 $Url/products.html"
    if (-not $NoBrowser) { Start-Process $Url }
} else {
    Write-Host "[!!] 100s 内未就绪——查看日志：$Root\_backend_err.log"
}