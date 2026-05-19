"""
Script de prueba para verificar la configuración del agente
Ejecuta: python test_setup.py
"""

import os
import sys
from dotenv import load_dotenv

print("\n" + "="*60)
print("TEST DE CONFIGURACION - AGENTE DGSP")
print("="*60 + "\n")

# 1. Verificar .env
print("1. Verificando archivo .env...")
if os.path.exists(".env"):
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if api_key and api_key != "tu_clave_api_aqui":
        print("   [OK] GROQ_API_KEY configurada")
    else:
        print("   [WARNING] GROQ_API_KEY no válida - actualiza .env")
else:
    print("   [ERROR] Archivo .env no encontrado")

# 2. Verificar PDF
print("\n2. Verificando archivo PDF...")
pdf_path = "./manual_dgsp.pdf"
if os.path.exists(pdf_path):
    size_mb = os.path.getsize(pdf_path) / (1024*1024)
    print(f"   [OK] PDF encontrado ({size_mb:.2f} MB)")
else:
    print(f"   [ERROR] PDF no encontrado en: {pdf_path}")
    print(f"      Debes colocar tu manual aquí")

# 3. Verificar dependencias
print("\n3. Verificando dependencias...")
required_packages = [
    "langchain",
    "langchain_groq",
    "langchain_community",
    "faiss",
    "pypdf",
    "dotenv"
]

missing = []
for package in required_packages:
    try:
        __import__(package)
        print(f"   [OK] {package}")
    except ImportError:
        print(f"   [ERROR] {package} (instala: pip install -r requirements.txt)")
        missing.append(package)

# 4. Verificar directorios
print("\n4. Verificando estructura de carpetas...")
dirs_to_check = [
    ("./faiss_index", "Indice FAISS (se crea automatico)"),
]

for dir_path, description in dirs_to_check:
    if os.path.exists(dir_path):
        print(f"   [OK] {dir_path} - {description}")
    else:
        print(f"   [INFO] {dir_path} - {description} (se creará al ejecutar)")

# 5. Resumen
print("\n" + "="*60)
print("RESUMEN")
print("="*60)

if not missing and os.path.exists(pdf_path) and os.getenv("GROQ_API_KEY"):
    print("[OK] TODO LISTO - Puedes ejecutar: python dgsp_agent.py")
else:
    print("[WARNING] FALTAN PASOS:")
    if missing:
        print(f"   - Instalar: pip install {' '.join(missing)}")
    if not os.path.exists(pdf_path):
        print(f"   - Agregar PDF en: {pdf_path}")
    if not os.getenv("GROQ_API_KEY"):
        print(f"   - Configurar GROQ_API_KEY en .env")

print("\n")
