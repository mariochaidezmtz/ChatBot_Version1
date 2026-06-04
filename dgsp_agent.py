"""
Agente de IA para responder preguntas sobre la DGSP de Hermosillo
Objetivo: Usar solo la documentación local sin conectarse a internet
"""

import os
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import Tool, tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel, Field

from document_loader import prepare_documents
from vector_store import VectorStoreManager
from memory import ConversationMemory

# Cargar variables de entorno
load_dotenv()


class DGSPAgent:
    def __init__(self, documents_path: str = None, session_id: str = "default"):
        """
        Inicializa el agente
        
        Args:
            documents_path: Ruta del archivo PDF, carpeta con documentos, o None para escanear ./documents
            session_id: ID de la sesión actual
        """
        self.session_id = session_id
        self.documents_path = documents_path
        
        print("\n" + "="*60)
        print("INICIALIZANDO AGENTE DGSP HERMOSILLO")
        print("="*60)
        
        # 1. Inicializar memoria
        self.memory = ConversationMemory()
        self.memory.create_session(session_id)
        
        # 2. Cargar o crear vector store
        self.vector_store_manager = VectorStoreManager()
        self._setup_vector_store()
        
        # 3. Inicializar LLM (Groq)
        self.llm = self._init_llm()
        
        # 4. Crear tools
        self.tools = self._create_tools()
        
        # 5. Crear agente
        self.agent = self._create_agent()
        
        print("\n[OK] Agente inicializado correctamente\n")
    
    def _setup_vector_store(self):
        """Configura el vector store (carga existente o crea nuevo)"""
        # Intenta cargar vector store existente
        loaded_store = self.vector_store_manager.load_vector_store()
        
        if loaded_store is None:
            # Si no existe, crea uno nuevo
            print("\n[PROCESS] Vector store no encontrado, creando nuevo...")
            try:
                # Usar escaneo dinámico si documents_path es None o una carpeta
                if self.documents_path is None or os.path.isdir(self.documents_path):
                    documents = prepare_documents(directory=self.documents_path)
                else:
                    documents = prepare_documents(paths=self.documents_path)
                
                if not documents:
                    raise ValueError("[ERROR] No se encontraron documentos para procesar")
                
                self.vector_store_manager.create_vector_store(documents)
                self.vector_store_manager.save_vector_store()
            except Exception as e:
                print(f"[ERROR] Error al crear vector store: {e}")
                raise
    
    def _init_llm(self) -> ChatGroq:
        """Inicializa el modelo de lenguaje de Groq"""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("[ERROR] GROQ_API_KEY no está configurada en .env")
        
        print("[SETUP] Inicializando modelo Llama 3.1 8B Instant (Groq)...")
        return ChatGroq(
            api_key=api_key,
            model_name="llama-3.1-8b-instant",
            temperature=0.3,  # Bajo para respuestas más precisas
            max_tokens=1024
        )
    
    def _create_tools(self) -> list:
        """Crea las herramientas disponibles para el agente"""

        # Esquema Pydantic para los argumentos de la herramienta
        class QueryInput(BaseModel):
            """Esquema de entrada para la herramienta de búsqueda en documentos institucionales"""
            query: str = Field(
                description="Texto limpio con palabras clave para buscar en el repositorio de la policía de Hermosillo."
            )

        @tool("buscar_documentos_policia", args_schema=QueryInput)
        def buscar_documentos_policia(query: str) -> str:
            """Usa esta herramienta para consultar información oficial sobre leyes de tránsito, justicia cívica, multas, manuales y proyectos de la Policía de Hermosillo."""
            # Asegura limpiar cualquier comilla rebelde que mande el LLM
            query_limpia = str(query).replace('"', '').replace("'", "").strip()

            # Limpieza adicional del query para remover muletillas y caracteres problemáticos
            import re
            query_limpia = query_limpia.strip()
            # Remover muletillas comunes al inicio
            muletillas = ['oye', 'hey', 'hola', 'buenos días', 'buenas tardes', 'buenas noches', 'disculpa', 'perdón']
            for muletilla in muletillas:
                if query_limpia.lower().startswith(muletilla.lower()):
                    query_limpia = query_limpia[len(muletilla):].strip()
                    if query_limpia.startswith(','):
                        query_limpia = query_limpia[1:].strip()
                    if query_limpia.startswith(','):
                        query_limpia = query_limpia[1:].strip()
            # Remover caracteres de puntuación excesivos al inicio/final
            query_limpia = re.sub(r'^[¿¡\?,.\s]+', '', query_limpia)
            query_limpia = re.sub(r'[¿¡\?,.\s]+$', '', query_limpia)

            # Verificar que el vector store esté cargado
            if self.vector_store_manager.vector_store is None:
                error_msg = "[ERROR] El vector store no está inicializado. No se puede buscar en los documentos."
                print(error_msg)
                return error_msg

            try:
                results = self.vector_store_manager.similarity_search(query_limpia, k=5)

                if not results:
                    return "No se encontró información relacionada en los documentos institucionales."

                context = "\n---\n".join([
                    f"[RELEVANCIA: {100-(i*20)}%]\n{doc.page_content}"
                    for i, doc in enumerate(results)
                ])

                return context
            except Exception as e:
                error_msg = f"[ERROR] Error al buscar en los documentos: {str(e)}"
                print(error_msg)
                return error_msg

        tools = [buscar_documentos_policia]
        return tools
    
    def _convert_history_to_langchain_format(self, history: list) -> list:
        """
        Convierte el historial personalizado al formato de LangChain
        
        Args:
            history: Lista de diccionarios con formato personalizado
                    (user, agent, context, timestamp)
                    
        Returns:
            Lista de mensajes en formato LangChain (role, content)
        """
        langchain_messages = []
        
        for interaction in history:
            # Mensaje del usuario
            langchain_messages.append(HumanMessage(content=interaction["user"]))
            
            # Mensaje del agente
            langchain_messages.append(AIMessage(content=interaction["agent"]))
        
        return langchain_messages

    def _create_agent(self) -> AgentExecutor:
        """Crea el agente con prompt personalizado"""
        
        # Prompt del sistema personalizado
        system_prompt = """
        
Eres el Asistente Inteligente Oficial de la Jefatura de Policía Preventiva y de Tránsito de Hermosillo, Sonora.

TU OBJETIVO:
Resolver dudas de la ciudadanía sobre trámites, leyes de tránsito, justicia cívica, multas, estructuras de la dependencia y proyectos tecnológicos de la corporación como "Tu voz en QR".

DOCUMENTOS DISPONIBLES:
Tienes acceso a un repositorio documental oficial que incluye:
- Manual de Organización de la DGSP
- Ley de Tránsito y reglamentos viales
- Reglamentos de Justicia Cívica
- Proyectos institucionales como "Tu voz en QR"
- Normas sobre multas y sanciones
- Procedimientos y trámites ciudadanos
- Cualquier otro documento oficial de la corporación

INSTRUCCIONES CRÍTICAS:
1. CUENTAS CON UNA HERRAMIENTA DE BÚSQUEDA para consultar el repositorio documental oficial
2. Usa tu herramienta de búsqueda `buscar_documentos_policia` ÚNICAMENTE cuando la pregunta del usuario involucre de manera explícita leyes, reglamentos, multas, la organización interna o proyectos como 'Tu voz en QR'
3. Si el usuario te saluda de forma casual (ej. 'hola', 'buenos días', 'qué tal'), despide la conversación ('gracias', 'adiós') o hace charla informal que no requiere datos específicos, responde de forma natural, breve y cortés como el asistente de la Policía de Hermosillo, sin intentar usar la herramienta de búsqueda
4. CUANDO USES LA HERRAMIENTA DE BÚSQUEDA, extrae ÚNICAMENTE las palabras clave esenciales de la duda del usuario para el parámetro de búsqueda. Por ejemplo, si el usuario dice 'oye me multaron y no puedo pagar la multa, ¿qué hago?', debes invocar la herramienta usando únicamente un término limpio como query='procedimiento pago multas' o 'no puedo pagar multa'. NUNCA pases frases conversacionales completas, muletillas ('oye', 'hola') ni caracteres de puntuación complejos al argumento de la función.
5. ANÁLISIS EXHAUSTIVO DE DOCUMENTOS: Cuando utilices la herramienta de búsqueda, recibirás fragmentos de múltiples documentos oficiales (Bando de Tránsito, Manual de Organización, Leyes, etc.). Si notas que los primeros fragmentos recuperados de un documento específico NO contienen una respuesta clara, contundente o exacta a la duda del usuario, NO te rindas diciendo que no hay información en ese manual. Tienes la obligación estricta de revisar y contrastar todos los demás fragmentos de los OTROS documentos adjuntos en el contexto de la herramienta para encontrar la respuesta correcta (como el Bando de Tránsito). Consolida la información buscando siempre dar la respuesta más útil y legal para el ciudadano.
6. SOLO responde basándote en la documentación disponible en los documentos institucionales para preguntas técnicas
7. SI tras usar la herramienta el dato exacto no existe en los documentos, indica de forma breve que no encontraste registro oficial de ese tema
8. NUNCA hagas suposiciones ni inventes información
9. Cita siempre de dónde obtuviste la información (ley de tránsito, manual de organización, proyecto "Tu voz en QR", etc.)
10. Si la pregunta está fuera del ámbito de los documentos, explica que no está documentado
11. Sé conciso y útil en tus respuestas

MANEJO DEL HISTORIAL DE CONVERSACIÓN:
- El historial de conversación contiene preguntas y respuestas anteriores
- Si el usuario hace una pregunta ambigua o de seguimiento (ej: "repite por favor", "¿y eso?"), 
  usa el contexto del historial para entender a qué se refiere
- Si la pregunta no tiene contexto claro, responde basándote en la información más reciente del historial
- NO intentes buscar en los documentos preguntas que son solo de seguimiento o repetición

CONTEXTO PREVIO:
{context}

Cuando el usuario pregunte, usa la herramienta de búsqueda para consultar los documentos institucionales y luego responde con precisión.
"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # Ejecutor del agente con verbosidad
        executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=3,
            handle_parsing_errors=True
        )
        
        return executor
    
    def _is_followup_question(self, question: str) -> bool:
        """
        Detecta si la pregunta es de seguimiento que no requiere búsqueda en el manual
        
        Args:
            question: Pregunta del usuario
            
        Returns:
            True si es una pregunta de seguimiento, False si requiere búsqueda
        """
        followup_patterns = [
            "repite", "repite por favor", "repetir", "otra vez",
            "¿qué?", "qué dijiste", "qué dijiste?",
            "explícame", "explícame mejor", "más detalles",
            "¿y eso?", "y eso?", "por qué",
            "cómo", "cómo así", "cómo es",
            "¿y?", "y?", "¿y qué más?",
            "continúa", "sigue", "más"
        ]
        
        question_lower = question.lower().strip()
        
        for pattern in followup_patterns:
            if pattern in question_lower:
                return True
        
        return False

    def ask(self, question: str, use_history: bool = True) -> str:
        """
        Hace una pregunta al agente
        
        Args:
            question: Pregunta del usuario
            use_history: Si usar el historial de conversación como contexto
            
        Returns:
            Respuesta del agente
        """
        print(f"\n[USER] {question}")
        
        # Detectar si es una pregunta de seguimiento
        if self._is_followup_question(question):
            # Obtener la última respuesta del historial
            history = self.memory.get_session_history(self.session_id, limit=1)
            if history:
                last_answer = history[0]["agent"]
                print(f"\n[AGENT] {last_answer}\n")
                
                # Guardar en memoria
                self.memory.save_interaction(
                    session_id=self.session_id,
                    user_message=question,
                    agent_response=last_answer
                )
                return last_answer
            else:
                return "No hay una respuesta anterior para repetir. Por favor, haz una pregunta específica sobre el manual."
        
        # Obtener contexto del historial
        context = ""
        if use_history:
            context = self.memory.get_context_summary(self.session_id, last_n=3)
        
        # Ejecutar agente
        try:
            # Obtener historial y convertirlo al formato de LangChain
            # Limitar a últimos 3 mensajes para evitar sesgo de repetición
            raw_history = self.memory.get_session_history(self.session_id, limit=3)
            langchain_history = self._convert_history_to_langchain_format(raw_history)
            
            response = self.agent.invoke({
                "input": question,
                "context": context,
                "chat_history": langchain_history
            })
            
            answer = response.get("output", "No se pudo obtener respuesta")
            
            # Guardar en memoria
            self.memory.save_interaction(
                session_id=self.session_id,
                user_message=question,
                agent_response=answer
            )
            
            print(f"\n[AGENT] {answer}\n")
            return answer
            
        except Exception as e:
            error_msg = f"[ERROR] {str(e)}"
            print(error_msg)
            return error_msg
    
    def show_history(self):
        """Muestra el historial de la sesión actual"""
        history = self.memory.get_session_history(self.session_id)
        
        if not history:
            print("[INFO] No hay historial en esta sesión")
            return
        
        print("\n" + "="*60)
        print("HISTORIAL DE CONVERSACION")
        print("="*60)
        
        for i, interaction in enumerate(history, 1):
            print(f"\n{i}. Pregunta: {interaction['user']}")
            print(f"   Respuesta: {interaction['agent'][:150]}...")
            print(f"   Hora: {interaction['timestamp']}")
    
    def list_sessions(self):
        """Lista todas las sesiones"""
        sessions = self.memory.list_sessions()
        
        print("\n" + "="*60)
        print("SESIONES DISPONIBLES")
        print("="*60)
        
        for session in sessions:
            print(f"\n[SESSION] {session['session_id']}")
            print(f"   Tema: {session['topic']}")
            print(f"   Creada: {session['created_at']}")
            print(f"   Última actividad: {session['last_activity']}")


def main():
    """Función principal - ejemplo de uso interactivo"""
    
    # Ruta de los documentos (puede ser una carpeta o None para escanear ./documents)
    # Para escaneo automático, usa None o especifica la carpeta "./documents"
    DOCUMENTS_PATH = None  # Escaneará automáticamente la carpeta ./documents
    
    # Alternativamente, puedes especificar archivos específicos:
    # DOCUMENTS_PATH = ["./manual_dgsp.pdf", "./ley-de-transito-del-estado-de-sonora.pdf"]
    
    # Generar session_id único basado en timestamp
    session_id = f"sesion_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Crear agente con session_id único
    agent = DGSPAgent(documents_path=DOCUMENTS_PATH, session_id=session_id)
    
    print("\n" + "="*60)
    print("CHATBOT DGSP HERMOSILLO")
    print("Jefatura de Policía Preventiva y Tránsito Municipal de Hermosillo")
    print("="*60)
    print("Escribe 'salir', 'adios', 'bye', 'stop' o 'terminar' para terminar")
    print("Escribe 'historial' para ver la conversación")
    print("="*60 + "\n")
    
    # Palabras clave de despedida
    farewell_keywords = ['salir', 'adios', 'adiós', 'bye', 'stop', 'terminar']
    
    try:
        while True:
            # Obtener input del usuario y limpiar
            question = input("Tú: ").strip().lower()
            
            # Validar que no esté vacío
            if not question:
                continue
            
            # Verificar si es palabra de despedida
            if question in farewell_keywords:
                print("\n" + "="*60)
                print("Gracias por consultar el Chatbot de la Jefatura de")
                print("Policía Preventiva y Tránsito Municipal de Hermosillo.")
                print("Estamos para servirte. ¡Cuídate y ten un excelente día!")
                print("="*60 + "\n")
                break
            
            # Verificar si quiere ver el historial
            if question == "historial":
                agent.show_history()
                continue
            
            # Hacer pregunta (el historial se mantiene automáticamente)
            agent.ask(question)
            
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("Gracias por consultar el Chatbot de la Jefatura de")
        print("Policía Preventiva y Tránsito Municipal de Hermosillo.")
        print("¡Cuídate y ten un excelente día!")
        print("="*60 + "\n")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Eliminar la sesión al finalizar
        agent.memory.delete_session(session_id)
        print(f"[INFO] Sesión {session_id} eliminada.")


if __name__ == "__main__":
    main()
