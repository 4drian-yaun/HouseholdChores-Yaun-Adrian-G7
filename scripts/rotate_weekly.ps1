# Automated Weekly Chore Rotation Script for Windows Task Scheduler
# Schedules to run at 00:00 every Monday
#
# To register in Windows Task Scheduler:
#   $Action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -File C:\path\to\scripts\rotate_weekly.ps1"
#   $Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 00:00
#   Register-ScheduledTask -TaskName "HouseholdChoresRotation" -Action $Action -Trigger $Trigger

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$PythonExe = Join-Path $ProjectDir "venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

Set-Location $ProjectDir
& $PythonExe manage.py rotate_weekly
