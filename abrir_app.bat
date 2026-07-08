@echo off
chcp 65001 >nul
title APP_REGISTROS_JUDICIALESYCEM
color 0A

echo ============================================
echo  INICIANDO APP_REGISTROS_JUDICIALESYCEM
echo ============================================
echo.

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado.
    echo Descargalo de: https://python.org
    pause
    exit /b 1
)

REM Crear entorno virtual si no existe
if not exist "venv" (
    echo [1/4] Creando entorno virtual...
    python -m venv venv
)

REM Activar entorno
echo [2/4] Activando entorno virtual...
call venv\Scripts\activate.bat

REM Instalar dependencias
echo [3/4] Verificando dependencias...
pip install -q -r requirements.txt

REM Verificar .env
if not exist ".env" (
    echo [4/4] Creando configuracion...
    (
        echo SUPABASE_URL=https://lbqichqgufkpataypqqs.supabase.co
        echo SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxicWljaHFndWZrcGF0YXlwcXFzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODMxMDUwMzYsImV4cCI6MjA5ODY4MTAzNn0.2lKC8i-K7YC_ksqK3_A-Ly4HFxKuss4pFlCLHUzt1PI
        echo SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxicWljaHFndWZrcGF0YXlwcXFzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MzEwNTAzNiwiZXhwIjoyMDk4NjgxMDM2fQ.-4wkOZNJPhDIzakWMBC572-kW5nAPba6c03x9OfrU-A
        echo SECRET_KEY=clave-secreta-app-pacientes-2026
    ) > .env
) else (
    echo [4/4] Configuracion OK.
)

echo.
echo ============================================
echo  SERVIDOR INICIADO
echo ============================================
echo.
echo La aplicacion se abrira automaticamente...
echo.

REM Abrir navegador despues de 3 segundos
timeout /t 3 /nobreak >nul
start http://localhost:5000

REM Iniciar Flask
set FLASK_APP=api\index.py
set FLASK_ENV=development
python -m flask run --host=0.0.0.0 --port=5000
