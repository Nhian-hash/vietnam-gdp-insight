param(
    [switch]$SkipSourceDownload
)

$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$Description
    )
    Write-Host "`n== $Description ==" -ForegroundColor Cyan
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Bước '$Description' thất bại với exit code $LASTEXITCODE."
    }
}

try {
    if (-not $SkipSourceDownload) {
        Invoke-Step -Command 'node' -Arguments @('build_extended_data.mjs') -Description 'Tải và chuẩn hóa nguồn dữ liệu mới'
        Invoke-Step -Command 'node' -Arguments @('refresh_expanded_data.mjs') -Description 'Tải bảng NSO mở rộng và World Bank Pink Sheet'
    }
    Invoke-Step -Command 'python' -Arguments @('extract_monthly_official.py') -Description 'Trích xuất các bảng tháng từ workbook nguồn'
    Invoke-Step -Command 'python' -Arguments @('analyze_observed_data.py') -Description 'Phân tích, rolling backtest, dự báo và QA'
    Invoke-Step -Command 'python' -Arguments @('analyze_expanded_data.py') -Description 'Chuẩn hóa và phân tích các động lực GDP mở rộng'
    Invoke-Step -Command 'python' -Arguments @('snapshot_data.py') -Description 'Tạo phiên bản dữ liệu bất biến gồm bộ mở rộng'
    Invoke-Step -Command 'python' -Arguments @('build_dashboard.py') -Description 'Dựng dashboard GDP ngoại tuyến'
    Write-Host "`nHoàn tất. Mở dashboard.html trong thư mục $PSScriptRoot" -ForegroundColor Green
}
finally {
    Pop-Location
}
