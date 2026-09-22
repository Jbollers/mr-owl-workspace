@echo off
setlocal
set "MRMAK_LAUNCH_ROOT=%~dp0"
if exist "%LOCALAPPDATA%\Mr. Owl Workspace\mrowl-workspace.exe" (
  start "" "%LOCALAPPDATA%\Mr. Owl Workspace\mrowl-workspace.exe" --repo "%MRMAK_LAUNCH_ROOT%."
  exit /b 0
)
if exist "%MRMAK_LAUNCH_ROOT%src-tauri\target\release\mrowl-workspace.exe" (
  start "" "%MRMAK_LAUNCH_ROOT%src-tauri\target\release\mrowl-workspace.exe" --repo "%MRMAK_LAUNCH_ROOT%."
  exit /b 0
)
echo Build and install the customized Mr. Owl Workspace first.
echo Or build with: powershell -NoProfile -ExecutionPolicy Bypass -File Setup.ps1 -Mode Desktop
echo See docs\getting-started.md for agent-guided setup.
pause
