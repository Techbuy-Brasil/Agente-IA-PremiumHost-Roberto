#!/bin/bash
echo "============================================"
echo " Agente de Hospedagem Inteligente"
echo " Deploy completo (Linux/Mac)"
echo "============================================"
echo ""

# Verifica Docker
if ! command -v docker &> /dev/null; then
    echo "[ERRO] Docker nao encontrado."
    exit 1
fi

# Copia .env se nao existir
if [ ! -f .env ]; then
    echo "[AVISO] .env nao encontrado. Criando a partir de .env.example"
    cp .env.example .env
fi

echo "[1/4] Parando containers antigos..."
docker compose down 2>/dev/null

echo "[2/4] Construindo imagens..."
docker compose build

echo "[3/4] Subindo servicos..."
docker compose up -d

echo "[4/4] Aguardando inicio..."
sleep 5

echo ""
echo "============================================"
echo " Sistema disponivel em:"
echo " API:         http://localhost:8000"
echo " WebChat:     http://localhost:8000/webchat"
echo " WhatsApp:    http://localhost:8080"
echo " Health:      http://localhost:8000/health"
echo "============================================"
echo ""
echo "Logs: docker compose logs -f"
echo "Parar: docker compose down"
