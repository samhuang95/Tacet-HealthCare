$root = Split-Path $PSScriptRoot -Parent
& "$root\.venv\Scripts\python.exe" "$root\main.py"
