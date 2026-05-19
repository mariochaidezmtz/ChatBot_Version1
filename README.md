# Agente DGSP Hermosillo

Chatbot inteligente basado en el manual de organización de la Dirección General de Seguridad Pública de Hermosillo, Sonora.

## Características

- Responde preguntas solo basado en documentación oficial  
- Sin conexión a internet (completamente offline después de cargar)  
- Memoria persistente en SQLite  
- Búsqueda por similitud con FAISS  
- Contexto inteligente entre preguntas  
- Usando Llama 3.1 8B (Groq) para precisión  

## Instalación

### 1. Requisitos
- Python 3.10+
- pip

### 2. Crear entorno virtual
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar API Key
```bash
# Edita el archivo .env
GROQ_API_KEY=tu_clave_aqui
```

Obtén tu clave en: https://console.groq.com

### 5. Agregar el manual
Coloca tu PDF en la carpeta raíz:
```
manual_dgsp.pdf  <-- Tu archivo aquí
```

## Uso

### Opción 1: Chatbot interactivo
```bash
python dgsp_agent.py
```

Luego:
```
Tú: ¿Cuál es la estructura organizacional de la DGSP?
Agente: [Respuesta basada en el manual]

Tú: ¿Cuáles son sus funciones principales?
Agente: [Respuesta basada en contexto previo]

Tú: historial
Tú: salir
```

### Opción 2: Uso en código
```python
from dgsp_agent import DGSPAgent

# Crear agente
agent = DGSPAgent(
    pdf_path="./manual_dgsp.pdf",
    session_id="consulta_ciudadano_001"
)

# Hacer pregunta
respuesta = agent.ask("¿Cuáles son los horarios de atención?")

# Ver historial
agent.show_history()
```

## Estructura del proyecto

```
.
├── dgsp_agent.py          Agente principal
├── document_loader.py     Carga y procesa PDF
├── vector_store.py        FAISS para búsqueda
├── memory.py              SQLite para memoria
├── .env                   Configuración (API keys)
├── requirements.txt       Dependencias
├── manual_dgsp.pdf        Tu archivo PDF
├── faiss_index/           Indice vector (se crea automático)
└── agent_memory.db        Base de datos SQLite (se crea automático)
```

## Flujo del Agente

```
Usuario pregunta
    ↓
Agente busca en Vector Store (FAISS)
    ↓
Agente obtiene contexto previo (SQLite)
    ↓
Groq LLM genera respuesta
    ↓
Respuesta se guarda en memoria
    ↓
Usuario recibe respuesta
```

## ⚙️ Cómo funciona (paso a paso)

### 1️⃣ Primer uso (Inicialización)
- Se carga el PDF del manual
- Se divide en chunks de 1000 caracteres
- Se crean embeddings (HuggingFace)
- Se indexa con FAISS
- Se guarda índice en `faiss_index/`

### 2️⃣ Búsqueda
- Usuario pregunta algo
- FAISS busca los 3 chunks más similares
- Se envía contexto al LLM

### 3️⃣ Respuesta
- LLM genera respuesta precisa
- Se guarda en SQLite con metadata
- Se mantiene contexto para próximas preguntas

## Privacidad y Seguridad

- Offline: No envía el PDF a internet
- Local: Todo se procesa localmente
- Solo API: Solo conexión es con Groq API
- Auditable: Historial guardado localmente

## 📊 Estructura de la Base de Datos

### Tabla: conversations
```
id, session_id, timestamp, user_message, agent_response, context, source_documents
```

### Tabla: sessions
```
id, session_id, created_at, last_activity, topic
```

## 🛠️ Personalización

### Cambiar modelo
En `dgsp_agent.py`, línea ~128:
```python
model_name="llama-3.1-70b-versatile"  # Modelo más grande
```

### Ajustar temperatura
```python
temperature=0.3  # Más preciso (0-0.5)
temperature=0.7  # Más creativo (0.5-1.0)
```

### Cambiar tamaño de chunks
En `dgsp_agent.py`, línea ~82:
```python
chunk_size=2000  # Chunks más grandes
chunk_overlap=300
```

## ⚠️ Solución de problemas

### Error: "GROQ_API_KEY no está configurada"
- Verifica que `.env` existe
- Que contiene tu clave válida
- Que el archivo está en la raíz del proyecto

### Error: "No se encontró PDF"
- Coloca el PDF en la carpeta raíz
- Verifica el nombre: `manual_dgsp.pdf`
- O actualiza la ruta en `dgsp_agent.py`

### Respuestas vagas
- El PDF cargado no contiene detalles
- Necesitas un PDF más completo
- O ajusta el `chunk_size` en `document_loader.py`

## 📚 Referencias

- [LangChain Docs](https://python.langchain.com/)
- [Groq API](https://console.groq.com/docs)
- [FAISS](https://github.com/facebookresearch/faiss)
- [HuggingFace Embeddings](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)

## Próximas mejoras

- Soporte para múltiples PDFs
- Análisis de sentimiento
- Generación de reportes
- Web interface
- Integración con WhatsApp/Telegram
- Analytics y estadísticas

## 👨‍💻 Autor

Proyecto creativo de IA para el bien público | Hermosillo, Sonora 🇲🇽

---

¿Dudas? Revisa el código o edita según tus necesidades.
