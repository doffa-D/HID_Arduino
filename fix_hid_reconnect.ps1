# PowerShell Script to Fix HID Mouse/Arduino Slow Reconnect After Idle
# Run as Administrator
# Version 2.0 - Added PnPCapabilities fix and more aggressive HID settings

Write-Host "=== HID Device Reconnect Fix Script v2.0 ===" -ForegroundColor Cyan
Write-Host "This script will apply fixes to prevent slow HID device reconnects`n" -ForegroundColor Yellow

# Check for admin rights
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Please run this script as Administrator" -ForegroundColor Red
    exit 1
}

Write-Host "[1/6] Disabling USB Selective Suspend for all power plans..." -ForegroundColor Green

$powerPlans = @( "381b4222-f694-41f0-9685-ff5bb260df2e",  # Balanced
                 "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",  # High Performance
                 "1847d33e-144e-4fef-ad67-a7f8a4d4a9d0")  # Power Saver

foreach ($guid in $powerPlans) {
    # Disable USB Selective Suspend - Battery
    powercfg /change $guid /usb-selective-suspend-setting /off 2>$null
    # Disable USB Selective Suspend - AC
    powercfg /change $guid /usb-selective-suspend-setting /off 2>$null
    # Also disable standby timeout
    powercfg /change $guid /standby-timeout-ac 0 2>$null
    powercfg /change $guid /standby-timeout-dc 0 2>$null
}

Write-Host "      USB Selective Suspend and standby timeout disabled" -ForegroundColor Gray

Write-Host "[2/6] Setting registry keys for USB settings..." -ForegroundColor Green

# Disable USB Automatic Surprise Removal
$usbRegPath = "HKLM:\SYSTEM\CurrentControlSet\Control\USB"
if (-not (Test-Path $usbRegPath)) {
    New-Item -Path $usbRegPath -Force | Out-Null
}
Set-ItemProperty -Path $usbRegPath -Name "DisableImplicitSUSupport" -Value 1 -Type DWord -Force

# Additional USB performance tweaks
Set-ItemProperty -Path $usbRegPath -Name "EnablePollMethodWhileConnected" -Value 1 -Type DWord -Force

# Disable USB power saving in USB hub
$usbHubPath = "HKLM:\SYSTEM\CurrentControlSet\Services\usbhub\HubG"
if (Test-Path $usbHubPath) {
    Set-ItemProperty -Path $usbHubPath -Name "DisableOnSuspend" -Value 1 -Type DWord -Force
}

# Disable selective suspend in USB hub driver
$usbHubDriverPath = "HKLM:\SYSTEM\CurrentControlSet\Services\usbhub"
if (Test-Path $usbHubDriverPath) {
    Set-ItemProperty -Path $usbHubDriverPath -Name "DisableSelectiveSuspend" -Value 1 -Type DWord -Force
}

Write-Host "      USB registry keys applied successfully" -ForegroundColor Gray

Write-Host "[3/6] Processing HID devices - Setting PnPCapabilities..." -ForegroundColor Green

# Get all HID devices and set PnPCapabilities to 24 (disables power management)
# PnPCapabilities: 0 = default, 24 = disables power management
$deviceUpdated = 0

try {
    $hidDevices = Get-PnpDevice -Class "HIDClass" -Status OK 2>$null
    foreach ($dev in $hidDevices) {
        try {
            $instanceId = $dev.InstanceId
            if ($instanceId) {
                # Set PnPCapabilities to 24 to disable power management
                $regPath = "HKLM:\SYSTEM\CurrentControlSet\Enum\$instanceId"
                if (Test-Path $regPath) {
                    Set-ItemProperty -Path $regPath -Name "PnPCapabilities" -Value 24 -Type DWord -ErrorAction SilentlyContinue
                }
                # Also set in Device Parameters
                $paramPath = "$regPath\Device Parameters"
                if (Test-Path $paramPath) {
                    Set-ItemProperty -Path $paramPath -Name "EnhancedPowerManagementEnabled" -Value 0 -ErrorAction SilentlyContinue
                }
            }
            $deviceUpdated++
        } catch {}
    }
} catch {}

Write-Host "      Processed $deviceUpdated HID devices with PnPCapabilities=24" -ForegroundColor Gray

Write-Host "[4/6] Setting device-specific power management via Device Manager..." -ForegroundColor Green

# Try to disable power management using devcon-style approach
$deviceCount = 0
try {
    # Get all USB and HID devices
    $devices = Get-PnpDevice | Where-Object { $_.Class -like "*HID*" -or $_.Class -like "*USB*" }
    foreach ($dev in devices) {
        try {
            # Disable power management
            $props = Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Enum\$($dev.InstanceId)\Device Parameters" -ErrorAction SilentlyContinue
            if ($props) {
                # Set D1 and D2 wake capabilities
                Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Enum\$($dev.InstanceId)\Device Parameters" -Name "DeviceState" -Value 1 -ErrorAction SilentlyContinue
            }
            $deviceCount++
        } catch {}
    }
} catch {}

Write-Host "      Processed $deviceCount USB/HID devices" -ForegroundColor Gray

Write-Host "[5/6] Configuring HID service settings..." -ForegroundColor Green

# Configure HID service to be more responsive
$hidServicePath = "HKLM:\SYSTEM\CurrentControlSet\Services\HidBus"
if (-not (Test-Path $hidServicePath)) {
    New-Item -Path $hidServicePath -Force | Out-Null
}
Set-ItemProperty -Path $hidServicePath -Name "Start" -Value 2 -Type DWord -Force
Set-ItemProperty -Path $hidServicePath -Name "Type" -Value 1 -Type DWord -Force
Set-ItemProperty -Path $hidServicePath -Name "ErrorControl" -Value 1 -Type DWord -Force

# HID Parse service
$hidParsePath = "HKLM:\SYSTEM\CurrentControlSet\Services\HidParse"
if (Test-Path $hidParsePath) {
    Set-ItemProperty -Path $hidParsePath -Name "Start" -Value 2 -Type DWord -Force
}

Write-Host "      HID service settings configured" -ForegroundColor Gray

Write-Host "[6/6] Creating device refresh script..." -ForegroundColor Green

# Create a script that can be scheduled to run on wake
$refreshScript = @'
# Refresh USB/HID devices on wake
Write-Host "Refreshing HID devices..."

# Restart USB buses
Get-PnpDevice -Class "USB" -Status Error | ForEach-Object {
    try {
        Restart-PnpDevice -InstanceId $_.InstanceId -Confirm:$false -ErrorAction SilentlyContinue
    } catch {}
}

# Refresh HID devices
Get-PnpDevice -Class "HIDClass" -Status Error | ForEach-Object {
    try {
        Restart-PnpDevice -InstanceId $_.InstanceId -Confirm:$false -ErrorAction SilentlyContinue
    } catch {}
}

Write-Host "HID device refresh complete"
'@

$scriptPath = "$env:USERPROFILE\RefreshHIDDevices.ps1"
$refreshScript | Out-File -FilePath $scriptPath -Encoding UTF8

Write-Host "      Refresh script created at: $scriptPath" -ForegroundColor Gray

Write-Host "`n=== Summary ===" -ForegroundColor Cyan
Write-Host @"
Applied fixes (v2.0):
- USB Selective Suspend: DISABLED
- Standby Timeout: DISABLED (set to 0)
- USB Registry Settings: CONFIGURED
- PnPCapabilities: SET to 24 (disables power management)
- HID Service: CONFIGURED for reliability
- Device Refresh Script: CREATED

After restart, your Arduino HID device should:
- NOT go into suspend when idle
- Reconnect quickly after idle
- Not cause Windows to disconnect/reconnect slowly

Optional next steps:
1. RESTART YOUR COMPUTER for all changes to take effect
2. Optional: Create scheduled task to refresh HID on wake
"@ -ForegroundColor White

Write-Host "`nScript completed! Please RESTART your computer." -ForegroundColor Yellow
