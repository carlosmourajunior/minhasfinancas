#!/bin/bash

# Script para inicializar o Sistema de Contas

echo "🚀 Iniciando Sistema de Controle de Contas..."

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não está instalado. Por favor, instale o Docker primeiro."
    exit 1
fi

# Verificar se Docker Compose está instalado
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose não está instalado. Por favor, instale o Docker Compose primeiro."
    exit 1
fi

echo "✅ Docker e Docker Compose encontrados"

# Construir e iniciar os containers
echo "🏗️ Construindo e iniciando containers..."
docker-compose up --build -d

echo "⏳ Aguardando serviços iniciarem..."
sleep 10

echo "📊 Sistema iniciado com sucesso!"
echo ""
echo "🌐 Acesse a aplicação:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8000"
echo "   Documentação: http://localhost:8000/docs"
echo ""
echo "📝 Para parar o sistema:"
echo "   docker-compose down"
echo ""
echo "🔍 Para ver logs:"
echo "   docker-compose logs -f"