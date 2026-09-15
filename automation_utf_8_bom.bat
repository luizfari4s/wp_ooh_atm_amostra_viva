@echo off
chcp 65001 >nul
set LOGIN=%USERNAME%

cd /d "C:\Users\%LOGIN%\OneDrive - Numerator International\Área de Trabalho\Workspace\PROD\wp_central_atm"
"C:/Program Files/Python314/python.exe" "C:\Users\%LOGIN%\OneDrive - Numerator International\Área de Trabalho\Workspace\PROD\\wp_central_atm\app.py"