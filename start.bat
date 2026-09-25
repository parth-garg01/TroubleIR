@echo off
cd /d "C:\Users\parth\Desktop\New folder"
set PYTHONPATH=src
py -m uvicorn troubleir.api.main:app --host 0.0.0.0 --port 8000
