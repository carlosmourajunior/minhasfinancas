@echo off
echo 🚀 Iniciando Sistema de Controle de Contas...

REM Verificar se Docker está instalado
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker não está instalado. Por favor, instale o Docker primeiro.
    pause
    exit /b 1
)

REM Verificar se Docker Compose está instalado
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose não está instalado. Por favor, instale o Docker Compose primeiro.
    pause
    exit /b 1
)

echo ✅ Docker e Docker Compose encontrados

REM Construir e iniciar os containers
echo 🏗️ Construindo e iniciando containers...
docker-compose up --build -d

echo ⏳ Aguardando serviços iniciarem...
timeout /t 10 /nobreak >nul

echo 📊 Sistema iniciado com sucesso!
echo.
echo 🌐 Acesse a aplicação:
echo    Frontend: http://localhost:3000
echo    Backend API: http://localhost:8000
echo    Documentação: http://localhost:8000/docs
echo.
echo 📝 Para parar o sistema:
echo    docker-compose down
echo.
echo 🔍 Para ver logs:
echo    docker-compose logs -f
echo.
pause