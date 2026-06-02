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

# 2. Verificar documentos
print("\n2. Verificando documentos...")
DOCUMENT_PATHS = [
    "./manual_dgsp.pdf",
    # Agrega más rutas aquí si tienes más documentos
]
SUPPORTED_EXTENSIONS = (".pdf", ".txt", ".md", ".docx")

any_found = False
for doc_path in DOCUMENT_PATHS:
    if os.path.exists(doc_path):
        size_mb = os.path.getsize(doc_path) / (1024*1024)
        ext = os.path.splitext(doc_path)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            print(f" [OK] {doc_path} ({size_mb:.2f} MB)")
        else:
            print(f" [WARNING] {doc_path} - formato no soportado ({ext})")
        any_found = True
    else:
        print(f" [ERROR] No encontrado: {doc_path}")

if not any_found:
    print(" Debes agregar al menos un documento en DOCUMENT_PATHS")
# 3. Verificar dependencias
print("\n3. Verificando dependencias...")
required_packages = [
    "langchain",
    "langchain_community",
    "langchain_groq",
    "faiss",
    "dotenv",
    "pydantic",
    "pypdf",
    "sentence_transformers",
    "groq",
    "docx",
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

if not missing and any_found and os.getenv("GROQ_API_KEY"):
    print("[OK] TODO LISTO - Puedes ejecutar: python dgsp_agent.py")
else:
    print("[WARNING] FALTAN PASOS:")
    if missing:
        print(f"   - Instalar: pip install {' '.join(missing)}")
    if not any_found:
        print(f"   - Agregar al menos un documento en DOCUMENT_PATHS")
    if not os.getenv("GROQ_API_KEY"):
        print(f"   - Configurar GROQ_API_KEY en .env")

print("\n")
