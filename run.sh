#!/bin/bash

# Script para instalar y ejecutar el agente DGSP con manejo de errores

set -e  # Exit on error

echo "=========================================="
echo "AGENTE DGSP HERMOSILLO"
echo "=========================================="
echo ""

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 no está instalado"
    echo "Instala Python 3.10+ desde https://www.python.org/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "[CHECK] Python version: $PYTHON_VERSION"

# Verificar si existe .env
if [ ! -f ".env" ]; then
    echo "[ERROR] Archivo .env no encontrado"
    echo "Por favor configura tu GROQ_API_KEY en .env"
    echo ""
    echo "Ejemplo:"
    echo "  GROQ_API_KEY=gsk_tu_clave_aqui"
    exit 1
fi

# Verificar si GROQ_API_KEY está configurada
if ! grep -q "GROQ_API_KEY=" .env; then
    echo "[ERROR] GROQ_API_KEY no está en .env"
    exit 1
fi

# Crear venv si no existe
if [ ! -d "venv" ]; then
    echo "[SETUP] Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar venv
echo "[SETUP] Activando entorno virtual..."
source venv/bin/activate

# Actualizar pip
echo "[SETUP] Actualizando pip..."
pip install --upgrade pip --quiet

# Instalar dependencias con reintentos
echo "[SETUP] Instalando dependencias..."
echo "[INFO] Esto puede tomar 2-5 minutos en primera ejecución..."

pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "[OK] Dependencias instaladas"
else
    echo "[ERROR] Error instalando dependencias"
    exit 1
fi

# Ejecutar test
echo ""
echo "[TEST] Ejecutando verificación..."
python test_setup.py

if [ $? -ne 0 ]; then
    echo "[WARNING] Algunos checks fallaron, pero continuando..."
fi

echo ""
echo "[STARTING] Iniciando agente..."
echo ""

# Ejecutar agente
python dgsp_agent.py
