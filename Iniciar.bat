@echo off
title NVIDIA CT Server - Debug
color 0A
cd /d "%~dp0"

echo ========================================
echo  NVIDIA CT Server - Verificando...
echo ========================================
echo.

REM Verificar se nvidia_server.py existe
if not exist nvidia_server.py (
    echo [ERRO] Arquivo nvidia_server.py nao encontrado!
    echo.
    pause
    exit /b 1
)

REM Verificar Python
echo [1/3] Verificando Python...
python --version
if errorlevel 1 (
    echo [ERRO] Python nao instalado!
    pause
    exit /b 1
)
echo Python OK!
echo.

REM Instalar dependências
echo [2/3] Verificando bibliotecas...
python -c "import pystray" >nul 2>&1
if errorlevel 1 (
    echo Instalando bibliotecas...
    python -m pip install pillow pystray requests
)
echo Bibliotecas OK!
echo.

REM Iniciar servidor
echo [3/3] Iniciando servidor...
echo O icone verde deve aparecer na bandeja.
echo Se nao aparecer, veja o erro abaixo:
echo.
python nvidia_server.py

echo.
echo ========================================
echo Servidor encerrado ou deu erro acima!
echo ========================================
pause