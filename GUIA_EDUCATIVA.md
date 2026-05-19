# 🎓 GUÍA EDUCATIVA: Cómo funciona el Agente DGSP

Hola, aquí explico cada pieza del agente y cómo se conectan. Este es un proyecto que aprendemos **juntos**, así que cada módulo está comentado y es fácil de entender.

---

## Parte 1: Los 5 Módulos del Agente

### 1️⃣ **document_loader.py** - Carga el PDF
**¿Qué hace?**
Toma tu archivo PDF (manual de la DGSP) y lo convierte en texto.

**Proceso:**
```
PDF (archivo) 
    ↓
Leer página por página
    ↓
Extraer texto
    ↓
Dividir en chunks pequeños (1000 caracteres)
    ↓
Crear lista de documentos
```

**¿Por qué dividir en chunks?**
- El modelo LLM tiene límite de tokens
- Chunks pequeños son más fáciles de buscar
- Mejor precisión en búsqueda por similitud

**Ejemplo:**
```python
from document_loader import prepare_documents

# Una línea para cargar y procesar el PDF
documents = prepare_documents("manual_dgsp.pdf")

# Resultado: 
# [Document 1] "La DGSP es responsable de..."
# [Document 2] "El departamento de tránsito..."
# [Document 3] "Los horarios de atención..."
# ... (100+ documentos más)
```

---

### 2️⃣ **vector_store.py** - Busca por similitud
**¿Qué hace?**
Convierte el texto en números (embeddings) para poder buscar "cosas parecidas".

**Proceso:**
```
Texto en chunks
    ↓
Modelo HuggingFace (embeddings)
    ↓
Convierte en vectores numéricos (384 dimensiones)
    ↓
FAISS indexa esos vectores
    ↓
Crea "índice" guardado en disco
```

**¿Cómo funciona la búsqueda?**
Cuando el usuario pregunta: "¿Cuáles son los departamentos?"

1. Tu pregunta se convierte en vector (384 números)
2. FAISS compara tu vector con todos los del índice
3. Encuentra los 3 más parecidos
4. Los devuelve al agente

**Visualización:**
```
Tu pregunta: "¿Cuáles son los departamentos?"
    ↓
Vector: [0.12, 0.45, -0.33, 0.87, ... 384 números]
    ↓
FAISS busca los más cercanos
    ↓
Encuentra:
  - Chunk 45: "Departamento de Tránsito..."  (99% parecido)
  - Chunk 12: "Departamento de Seguridad..."  (98% parecido)
  - Chunk 67: "Estructura organizacional..."  (95% parecido)
```

**Código de uso:**
```python
from vector_store import VectorStoreManager

manager = VectorStoreManager()
manager.create_vector_store(documents)  # Crea índice
manager.save_vector_store()              # Guarda a disco

# Después, en otra sesión:
manager.load_vector_store()              # Carga índice guardado
results = manager.similarity_search("¿Qué hace seguridad vial?", k=3)
```

---

### 3️⃣ **memory.py** - Guarda la conversación
**¿Qué hace?**
Usa SQLite para guardar el historial de preguntas y respuestas.

**Base de datos (2 tablas):**

**Tabla: sessions**
```
session_id    | topic     | created_at          | last_activity
session_001   | General   | 2025-05-19 10:30:00 | 2025-05-19 10:45:00
session_002   | Tránsito  | 2025-05-19 11:00:00 | 2025-05-19 11:15:00
```

**Tabla: conversations**
```
id | session_id   | user_message              | agent_response        | timestamp
1  | session_001  | ¿Estructura org?          | La DGSP está dividida... | 2025-05-19 10:30:15
2  | session_001  | ¿Horarios?                | El horario es...        | 2025-05-19 10:35:22
3  | session_001  | ¿Quién es el jefe?        | El director es...       | 2025-05-19 10:40:10
```

**¿Por qué es útil?**
- El agente recuerda preguntas previas
- Puede mantener contexto ("¿y eso qué significa?")
- Permite auditar qué se preguntó
- Generar reportes

**Código de uso:**
```python
from memory import ConversationMemory

memory = ConversationMemory()

# Crear sesión nueva
memory.create_session("session_ciudadano_01", topic="Consulta sobre Tránsito")

# Guardar una interacción
memory.save_interaction(
    session_id="session_ciudadano_01",
    user_message="¿Cuáles son mis derechos?",
    agent_response="Según el manual, los ciudadanos tienen..."
)

# Ver historial
history = memory.get_session_history("session_ciudadano_01")
# Resultado: [
#   {"user": "¿Estructura?", "agent": "La DGSP...", "timestamp": "..."},
#   {"user": "¿Derechos?", "agent": "Según...", "timestamp": "..."}
# ]

# Obtener contexto para siguiente pregunta
context = memory.get_context_summary("session_ciudadano_01", last_n=3)
# Resultado: "📋 HISTORIAL:\n1. Pregunta: ¿Estructura?..."
```

---

### 4️⃣ **dgsp_agent.py** - El director de orquesta
**¿Qué hace?**
Es el "maestro" que coordina todo: recibe pregunta, busca documentos, obtiene contexto, llama al LLM, guarda resultado.

**Inicialización:**
```python
agent = DGSPAgent(pdf_path="./manual_dgsp.pdf", session_id="mi_sesion")
```

Esto automáticamente:
1. Carga la memoria (SQLite)
2. Carga el vector store (FAISS)
3. Inicializa el LLM (Groq Llama 3.1)
4. Crea las herramientas disponibles
5. Configura el prompt del agente

**Las herramientas disponibles:**
El agente solo puede hacer una cosa: **search_manual**
```python
def search_manual(query: str) -> str:
    """Busca en el vector store"""
    results = self.vector_store_manager.similarity_search(query, k=3)
    return "Contexto relevante del manual"
```

**El flujo cuando preguntas:**
```
agent.ask("¿Qué es la DGSP?")
    ↓
1. Obtener historial previo de memoria
2. Crear prompt: "Responde basándote en: [documentos] + [historial]"
3. Enviar a LLM: "Aquí hay documentos, aquí el contexto previo, responde"
4. LLM piensa: "Voy a usar search_manual para buscar"
5. Ejecuta search_manual("¿Qué es la DGSP?")
6. FAISS devuelve 3 chunks del manual
7. LLM genera respuesta basada en esos chunks
8. Guardar en SQLite
9. Devolver respuesta al usuario
```

**Código en detalle:**
```python
# Crear agente
agent = DGSPAgent(pdf_path="./manual_dgsp.pdf", session_id="user_123")

# Hacer pregunta
respuesta = agent.ask("¿Cuál es la misión de la DGSP?")

# Ver historial de esta sesión
agent.show_history()

# Ver todas las sesiones
agent.list_sessions()
```

---

## Parte 2: El Prompt Inteligente

Cuando haces una pregunta, el agente envía algo como esto al LLM:

```
SISTEMA:
"Eres un experto sobre la DGSP de Hermosillo, Sonora.
INSTRUCCIONES CRÍTICAS:
1. SOLO responde basándote en la documentación
2. SI no encuentras información, dilo claramente
3. NUNCA hagas suposiciones
4. Cita siempre de dónde obtuviste la info"

CONTEXTO PREVIO:
"📋 HISTORIAL:
1. Pregunta: ¿Qué es la DGSP?
   Respuesta: La DGSP es la dependencia municipal..."
2. Pregunta: ¿Cuántos departamentos tiene?
   Respuesta: Tiene 5 departamentos principales..."

DOCUMENTOS RELEVANTES:
"[Relevancia: 100%]
La DGSP es responsable de mantener el orden público...

[Relevancia: 75%]
El departamento de tránsito funciona de 06:00 a 22:00..."

PREGUNTA DEL USUARIO:
"¿Cuáles son los horarios de atención?"

RESPUESTA ESPERADA:
"Basándome en el manual, los horarios son..."
```

---

## Parte 3: Flujo Completo Paso a Paso

Imagina que pregunta un ciudadano: "¿Cómo reporto un delito?"

### ⏱️ Segundo 0: Pregunta entra
```
Usuario → Agent.ask("¿Cómo reporto un delito?")
```

### ⏱️ Segundo 0.2: Obtener historial
```python
memory.get_session_history(session_id, limit=5)
# Devuelve: []  (primera pregunta, no hay historial)
```

### ⏱️ Segundo 0.4: Buscar en vector store
```python
results = vector_store.similarity_search("¿Cómo reporto un delito?", k=3)
# Devuelve:
# [
#   {"page_content": "Para reportar un delito, acuda a..."},
#   {"page_content": "Los números de emergencia son: 911, 066..."},
#   {"page_content": "El proceso de denuncia requiere..."}
# ]
```

### ⏱️ Segundo 0.6: Armar prompt para LLM
```python
prompt = f"""
SISTEMA: [instrucciones]
CONTEXTO: [historial vacío]
DOCUMENTOS: [3 chunks encontrados]
PREGUNTA: ¿Cómo reporto un delito?
"""
```

### ⏱️ Segundo 0.8-2: LLM genera respuesta
```
Groq LLM procesa prompt
↓
Genera: "Para reportar un delito en Hermosillo:
1. Llame al 911 para emergencias
2. Visite las instalaciones en calle X
3. Presente denuncia formal
4. Obtendrá número de caso"
```

### ⏱️ Segundo 2: Guardar en base de datos
```python
memory.save_interaction(
    session_id="user_123",
    user_message="¿Cómo reporto un delito?",
    agent_response="Para reportar un delito en Hermosillo: 1. Llame..."
)
```

### ⏱️ Segundo 2.1: Devolver respuesta
```
Respuesta mostrada al usuario
```

---

## Parte 4: Cómo Evitar Alucinaciones

Este agente **NO alucina** porque:

### ✅ Restricción 1: Solo usa documentos
```python
# El LLM tiene instrucción explícita:
"SOLO responde basándote en la documentación del manual disponible"
```

Si el manual no habla de algo, el agente dice:
```
"No encontré información sobre eso en el manual de la DGSP."
```

### ✅ Restricción 2: La tool solo devuelve documentos
```python
def search_manual(query):
    results = vector_store.similarity_search(query, k=3)
    if not results:
        return "No se encontró información relacionada"
    # Siempre devuelve lo que está EN el PDF
```

### ✅ Restricción 3: Temperatura baja del LLM
```python
# Groq inicializado con temperatura = 0.3
# Temperatura baja = respuestas más precisas, menos creativas
llm = ChatGroq(temperature=0.3)  # No 0.7 o 1.0
```

### ✅ Restricción 4: Sin acceso a internet
```
El agente NO puede:
- Buscar en Google
- Consultar Wikipedia
- Acceder a páginas web
- Conectarse a redes sociales

SOLO puede:
- Leer el PDF cargado
- Recordar el historial
- Procesar con el LLM
```

---

## Parte 5: Mejoras Futuras (Juntos)

En la próxima sesión podemos agregar:

### 🔹 Búsqueda multi-PDFs
```python
# En lugar de un PDF, cargar varios:
documents = []
documents.extend(prepare_documents("manual_dgsp.pdf"))
documents.extend(prepare_documents("reglamento_tránsito.pdf"))
documents.extend(prepare_documents("derechos_ciudadanos.pdf"))
vector_store.create_vector_store(documents)
```

### 🔹 Feedback del usuario
```python
# Guardar si la respuesta fue útil o no
memory.rate_interaction(interaction_id, rating="good")  # o "bad"
```

### 🔹 Reportes inteligentes
```python
# Ver qué preguntan más los ciudadanos
memory.get_most_asked_questions(limit=10)
memory.get_questions_by_topic("Tránsito")
```

### 🔹 Web interface
```python
# En lugar de consola, una página web con:
# - Chat bonito
# - Historial visual
# - Búsqueda de sesiones pasadas
```

### 🔹 Integración WhatsApp/Telegram
```python
# Los ciudadanos preguntan directamente en WhatsApp
# El agente responde automáticamente
```

---

## Resumen: Los 5 Módulos Trabajan Así

```
Usuario → AGENTE → Busca en VECTOR STORE → Obtiene 3 chunks
                        ↓
                   Obtiene CONTEXTO de MEMORIA
                        ↓
                   Envía al LLM (GROQ) junto con PROMPT
                        ↓
                   LLM genera respuesta precisa
                        ↓
                   AGENTE guarda en MEMORIA
                        ↓
                   Usuario recibe respuesta
```

**Cada módulo es independiente:**
- Puedo cambiar Vector Store sin tocar el agente
- Puedo cambiar LLM sin tocar el vector store
- Puedo cambiar Memoria sin tocar nada más

Eso es buena arquitectura. 🎯

---

¿Preguntas? Sobre cualquier parte, me preguntas y lo explicamos juntos.
