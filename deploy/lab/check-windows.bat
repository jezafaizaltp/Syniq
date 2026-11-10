@echo off
rem Double-click before each lab period to check SYNiq is ready. Changes nothing.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0check.ps1"
