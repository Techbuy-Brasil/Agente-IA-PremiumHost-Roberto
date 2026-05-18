@echo off
echo ============================================
echo  Agente de Hospedagem Inteligente
echo  Deploy completo
echo ============================================
echo.

REM Verifica se o Docker esta instalado
docker --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Docker nao encontrado. Instale Docker Desktop:
    echo https://docs.docker.com/desktop/setup/install/windows-install/
    pause
    exit /b 1
)

REM Copia .env se nao existir
if not exist .env (
    echo [AVISO] Arquivo .env nao encontrado.
    echo [INFO] Copiando .env.example para .env - edite com suas configuracoes.
    copy .env.example .env
)

echo [1/4] Parando containers antigos...
docker compose down 2>nul

echo [2/4] Construindo imagens...
docker compose build

echo [3/4] Subindo servicos...
docker compose up -d

echo [4/4] Aguardando inicio...
timeout /t 5 /nobreak >nul

echo.
echo ============================================
echo  Sistema disponivel em:
echo  API:         http://localhost:8000
echo  WebChat:     http://localhost:8000/webchat
echo  WhatsApp:    http://localhost:8080
echo  Health:      http://localhost:8000/health
echo ============================================
echo.
echo Para ver logs: docker compose logs -f
echo Para parar:    docker compose down
echo.

pause
