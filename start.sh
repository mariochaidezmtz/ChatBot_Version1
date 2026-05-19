#!/bin/bash

# Script para iniciar el agente DGSP

echo "=========================================="
echo "AGENTE DGSP HERMOSILLO"
echo "=========================================="
echo ""

# Verificar si existe .env
if [ ! -f ".env" ]; then
    echo "[ERROR] Archivo .env no encontrado"
    echo "Por favor configura tu GROQ_API_KEY en .env"
    exit 1
fi

# Verificar si existe venv
if [ ! -d "venv" ]; then
    echo "[SETUP] Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar venv
echo "[SETUP] Activando entorno virtual..."
source venv/bin/activate

# Instalar dependencias si es necesario
if ! python -c "import langchain" 2>/dev/null; then
    echo "[SETUP] Instalando dependencias..."
    pip install -q -r requirements.txt
fi

# Ejecutar test
echo ""
echo "[TEST] Ejecutando test de configuración..."
python test_setup.py

echo ""
echo "[STARTING] Iniciando agente..."
echo ""

# Ejecutar agente
python dgsp_agent.py
