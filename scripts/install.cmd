@echo off
rem Worldbuilder Canon sidecar installer — double-click launcher.
rem Calls PowerShell with policy bypass so the script always runs.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
