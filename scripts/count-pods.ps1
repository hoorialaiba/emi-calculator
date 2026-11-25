param(
    [int]$Count = 30,
    [string]$Url = "http://emi.local/api/emi"
)

$body = '{"P":500000,"rate":12,"n":24}'
$pods = @()
$failed = 0

1..$Count | ForEach-Object {
    try {
        $r = Invoke-RestMethod -Uri $Url -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 10
        $pods += $r.servedBy.pod
    } catch {
        $failed++
    }
}

$pods | Group-Object | Sort-Object Name | Select-Object @{n='Pod';e={$_.Name}}, Count | Format-Table -AutoSize | Out-String | Write-Host
Write-Host "Total OK: $($pods.Count)  Failed: $failed"