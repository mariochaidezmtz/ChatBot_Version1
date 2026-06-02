"""
Script de diagnóstico y verificación para el sistema RAG multidocumento
Ejecuta: python test_setup.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

print("\n" + "="*70)
print("TEST DE CONFIGURACIÓN - SISTEMA RAG MULTIDOCUMENTO DGSP")
print("="*70 + "\n")

# 1. Verificar .env y variables de entorno
print("1. Verificando variables de entorno...")
if os.path.exists(".env"):
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if api_key and api_key != "tu_clave_api_aqui":
        print("   [OK] GROQ_API_KEY configurada")
        env_ok = True
    else:
        print("   [WARNING] GROQ_API_KEY no válida - actualiza .env")
        env_ok = False
else:
    print("   [ERROR] Archivo .env no encontrado")
    env_ok = False

# 2. Verificar carpeta de documentos y escaneo dinámico
print("\n2. Verificando carpeta de documentos...")
documents_dir = "./documents"
SUPPORTED_EXTENSIONS = (".pdf", ".txt", ".md", ".docx")

if os.path.exists(documents_dir):
    print(f"   [OK] Carpeta '{documents_dir}' encontrada")
    
    # Escanear documentos
    found_files = []
    for ext in SUPPORTED_EXTENSIONS:
        for file_path in Path(documents_dir).glob(f"*{ext}"):
            found_files.append(file_path)
    
    # También buscar en subdirectorios
    for ext in SUPPORTED_EXTENSIONS:
        for file_path in Path(documents_dir).rglob(f"*{ext}"):
            if file_path not in found_files:
                found_files.append(file_path)
    
    if found_files:
        print(f"   [OK] {len(found_files)} documento(s) encontrado(s):")
        for file_path in found_files:
            size_mb = file_path.stat().st_size / (1024*1024)
            print(f"      - {file_path.name} ({size_mb:.2f} MB)")
        docs_ok = True
    else:
        print(f"   [WARNING] No se encontraron documentos en '{documents_dir}'")
        print(f"      Extensiones soportadas: {', '.join(SUPPORTED_EXTENSIONS)}")
        docs_ok = False
else:
    print(f"   [WARNING] Carpeta '{documents_dir}' no encontrada (se creará si se especifica)")
    docs_ok = False

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

deps_ok = len(missing) == 0

# 4. Verificar estructura de carpetas
print("\n4. Verificando estructura de carpetas...")
dirs_to_check = [
    ("./faiss_index", "Índice FAISS unificado (se crea automáticamente)"),
    ("./documents", "Carpeta de documentos multidocumento"),
]

dirs_ok = True
for dir_path, description in dirs_to_check:
    if os.path.exists(dir_path):
        print(f"   [OK] {dir_path} - {description}")
    else:
        print(f"   [INFO] {dir_path} - {description} (se creará si es necesario)")

# 5. Verificar índice FAISS si existe
print("\n5. Verificando índice FAISS unificado...")
if os.path.exists("./faiss_index"):
    try:
        from vector_store import VectorStoreManager
        vsm = VectorStoreManager()
        loaded = vsm.load_vector_store()
        if loaded:
            print("   [OK] Índice FAISS unificado cargado correctamente")
            faiss_ok = True
        else:
            print("   [WARNING] Índice FAISS existe pero no se pudo cargar")
            faiss_ok = False
    except Exception as e:
        print(f"   [WARNING] Error al verificar índice FAISS: {e}")
        faiss_ok = False
else:
    print("   [INFO] Índice FAISS no existe (se creará al ejecutar el agente)")
    faiss_ok = True  # No es error si no existe aún

# 6. Prueba de inicialización del agente (opcional)
print("\n6. Verificando inicialización del agente...")
try:
    from dgsp_agent import DGSPAgent
    print("   [OK] Módulo dgsp_agent importado correctamente")
    
    # Intentar inicializar sin crear sesión
    try:
        from document_loader import prepare_documents
        print("   [OK] Módulo document_loader importado correctamente")
        loader_ok = True
    except Exception as e:
        print(f"   [ERROR] Error al importar document_loader: {e}")
        loader_ok = False
        
    agent_ok = loader_ok
except Exception as e:
    print(f"   [ERROR] Error al importar dgsp_agent: {e}")
    agent_ok = False

# 7. Resumen
print("\n" + "="*70)
print("RESUMEN DEL SISTEMA")
print("="*70)

checklist = [
    ("Variables de entorno", env_ok),
    ("Documentos en carpeta", docs_ok),
    ("Dependencias instaladas", deps_ok),
    ("Estructura de carpetas", dirs_ok),
    ("Índice FAISS", faiss_ok),
    ("Módulos del agente", agent_ok),
]

all_ok = all(status for _, status in checklist)

for item, status in checklist:
    icon = "[OK]" if status else "[ERROR]"
    print(f"{icon} {item}")

print("\n" + "="*70)

if all_ok:
    print("[OK] TODO LISTO - Puedes ejecutar: python dgsp_agent.py")
    print("\nEl sistema está configurado para:")
    print("   - Escanear automáticamente la carpeta ./documents/")
    print("   - Crear un índice FAISS unificado con todos los documentos")
    print("   - Responder preguntas sobre múltiples documentos institucionales")
else:
    print("[WARNING] FALTAN PASOS:")
    if not env_ok:
        print("   - Configurar GROQ_API_KEY en .env")
    if not docs_ok:
        print("   - Agregar documentos a la carpeta ./documents/")
    if not deps_ok:
        print(f"   - Instalar dependencias: pip install -r requirements.txt")
    if not agent_ok:
        print("   - Verificar que los módulos del agente estén correctos")

print("="*70 + "\n")
