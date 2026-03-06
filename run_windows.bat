@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  set "PY_CMD=py"
  set "PY_ARG=-3"
) else (
  set "PY_CMD=python"
  set "PY_ARG="
)

if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe app.py
  goto :eof
)

echo [NewsCleanroom] Keine vorhandene virtuelle Umgebung gefunden - versuche Setup...
if defined PY_ARG (
  %PY_CMD% %PY_ARG% -m venv .venv
) else (
  %PY_CMD% -m venv .venv
)

if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [NewsCleanroom] Setup/Paketinstallation fehlgeschlagen - starte im Offline-Modus.
    if defined PY_ARG (
      %PY_CMD% %PY_ARG% app.py --offline
    ) else (
      %PY_CMD% app.py --offline
    )
  ) else (
    .venv\Scripts\python.exe app.py
  )
) else (
  echo [NewsCleanroom] Virtuelle Umgebung konnte nicht erstellt werden - starte direkt im Offline-Modus.
  if defined PY_ARG (
    %PY_CMD% %PY_ARG% app.py --offline
  ) else (
    %PY_CMD% app.py --offline
  )
)
