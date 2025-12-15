$base = "http://127.0.0.1:9000"
$hdr  = @{ "x-auth" = $env:AUTH_TOKEN; "accept"="application/json" }
if (-not $hdr["x-auth"]) { $hdr["x-auth"] = "mysupersecrettoken" }

"== Ping =="
Invoke-RestMethod "$base/api/health"  -Headers $hdr | Format-List

"== Version/config =="
Invoke-RestMethod "$base/api/version" -Headers $hdr | Format-List
Invoke-RestMethod "$base/api/config"  -Headers $hdr | ConvertTo-Json -Depth 6

"== Export (in-process memory) =="
$resp = Invoke-RestMethod "$base/api/export/all" -Method POST -Headers $hdr -Body '{}' -ContentType 'application/json'
$resp | ConvertTo-Json -Depth 6

"== Files (first 5) =="
Invoke-RestMethod "$base/api/files?limit=5&offset=0" -Headers $hdr | ConvertTo-Json -Depth 6

"== Metrics =="
Invoke-RestMethod "$base/metrics" -Headers $hdr
