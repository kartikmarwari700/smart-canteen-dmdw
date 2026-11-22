# Fallback for Power BI's "cyclic reference" error on Refresh:
# loads every table one-by-one into the Power BI file that is currently open (CanteenDW).
# Usage: open CanteenDW.pbip in Power BI Desktop, then run  .\powerbi_refresh.ps1
$ErrorActionPreference = "Stop"
$dll = "C:\Program Files\Microsoft Power BI Desktop\bin\Microsoft.PowerBI.AdomdClient.dll"
Add-Type -Path $dll
$ws = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\Power BI Desktop\AnalysisServicesWorkspaces" -Directory | Sort-Object LastWriteTime -Descending
$port = $null
foreach ($w in $ws) {
    $f = Join-Path $w.FullName "Data\msmdsrv.port.txt"
    if (Test-Path $f) {
        $p = [int](Get-Content $f -Encoding Unicode)
        if (Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue) { $port = $p; break }
    }
}
if (-not $port) { throw "Open CanteenDW.pbip in Power BI Desktop first." }
$cn = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$port"); $cn.Open()
$cmd = $cn.CreateCommand(); $cmd.CommandText = "SELECT [CATALOG_NAME] FROM `$SYSTEM.DBSCHEMA_CATALOGS"
$r = $cmd.ExecuteReader(); $r.Read() | Out-Null; $db = $r[0]; $r.Close(); $cn.Close()
$cn = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$port;Initial Catalog=$db"); $cn.Open()
$tables = "dim_date","dim_meal_slot","dim_category","dim_cuisine","dim_item","dim_student","fact_sales","fact_waste","fact_inventory",
          "association_rules","cluster_profiles","recommendations","fact_real_canteen_waste","fact_kitchen_waste","waste_anomalies"
foreach ($t in $tables) {
    $c = $cn.CreateCommand(); $c.CommandTimeout = 600
    $c.CommandText = '{"refresh":{"type":"full","objects":[{"database":"' + $db + '","table":"' + $t + '"}]}}'
    $c.ExecuteNonQuery() | Out-Null
    Write-Host "loaded $t"
}
$cn.Close()
Write-Host "Done. Now press File > Save in Power BI (do NOT press Refresh)."
