param(
    [int]$Seconds = 60,
    [string]$Log = "results\request-loop.log",
    [int]$DelayMs = 200,
    [string]$Url = "http://emi.local/api/emi"
)

$body = '{"P":500000,"rate":12,"n":24}'
"timestamp,status,pod" | Out-File $Log -Encoding ascii
$end = (Get-Date).AddSeconds($Seconds)
$ok = 0
$fail = 0

while ((Get-Date) -lt $end) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
    try {
        $r = Invoke-WebRequest -Uri $Url -Method Post -ContentType 'application/json' -Body $body -UseBasicParsing -TimeoutSec 5
        $pod = ($r.Content | ConvertFrom-Json).servedBy.pod
        "$ts,$($r.StatusCode),$pod" | Out-File $Log -Append -Encoding ascii
        $ok++
    } catch {
        $code = "ERR"
        if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
        "$ts,$code," | Out-File $Log -Append -Encoding ascii
        $fail++
    }
    Start-Sleep -Milliseconds $DelayMs
}
Write-Host "Done. OK=$ok FAILED=$fail log=$Log"