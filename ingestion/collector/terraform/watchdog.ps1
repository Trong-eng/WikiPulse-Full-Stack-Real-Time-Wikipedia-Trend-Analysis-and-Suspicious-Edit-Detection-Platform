param([Parameter(Mandatory=$true)][string]$RepoRoot,
      [Parameter(Mandatory=$true)][string]$RunId)
if ($RunId -notmatch '^[a-z0-9-]{6,24}$') { throw 'Invalid run ID' }
$ErrorActionPreference = 'Stop'
$TaskDir = Join-Path $RepoRoot 'artifacts/terraform/w4'
$env:TF_DATA_DIR = Join-Path $TaskDir 'tfdata'
$TaskModule = Join-Path $RepoRoot 'ingestion/collector/terraform'
$TaskDeadline = [DateTime]::UtcNow.AddMinutes(185)
while ([DateTime]::UtcNow -lt $TaskDeadline) {
    if (Test-Path -LiteralPath (Join-Path $TaskDir "$RunId.stop")) { exit 0 }
    Start-Sleep -Seconds 30
}
for ($TaskAttempt = 0; $TaskAttempt -lt 3; $TaskAttempt++) {
    if (Test-Path -LiteralPath (Join-Path $TaskDir "$RunId.stop")) { exit 0 }
    $TaskStateText = & terraform "-chdir=$TaskModule" state pull
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect Terraform state; refusing to destroy.' }
    $TaskState = $TaskStateText | ConvertFrom-Json
    $TaskResources = @($TaskState.resources | Where-Object { $_.mode -eq 'managed' })
    if ($TaskResources.Count -eq 0) { exit 0 }
    $TaskName = "wikipulse-thanh-w4-$RunId"
    foreach ($TaskResource in $TaskResources) {
        foreach ($TaskInstance in $TaskResource.instances) {
            $TaskAttributes = $TaskInstance.attributes
            $TaskMatches = switch ($TaskResource.type) {
                'aws_instance' { $TaskAttributes.tags.Name -eq $TaskName }
                'aws_security_group' { $TaskAttributes.name -eq $TaskName }
                'aws_iam_role' { $TaskAttributes.name -eq $TaskName }
                'aws_iam_instance_profile' { $TaskAttributes.name -eq $TaskName }
                'aws_iam_role_policy_attachment' { $TaskAttributes.role -eq $TaskName }
                default { $false }
            }
            if (-not $TaskMatches) { throw 'Terraform state does not match this run; refusing to destroy.' }
        }
    }
    if (Test-Path -LiteralPath (Join-Path $TaskDir "$RunId.stop")) { exit 0 }
    & terraform "-chdir=$TaskModule" destroy -auto-approve -input=false -no-color "-var=run_id=$RunId" *>> (Join-Path $TaskDir 'watchdog.log')
    if ($LASTEXITCODE -eq 0) { exit 0 }
    Start-Sleep -Seconds 30
}
exit 1
