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
from langchain_core.tools import Tool
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
        
        print("[SETUP] Inicializando modelo llama-3.1-8b-instant (Groq)...")
        return ChatGroq(
            api_key=api_key,
            model_name="llama-3.1-8b-instant",
            temperature=0.3,  # Bajo para respuestas más precisas
            max_tokens=2048
        )
    
    def _create_tools(self) -> list:
        """Crea las herramientas disponibles para el agente"""
        
        # Esquema Pydantic para los argumentos de la herramienta
        class SearchDocumentsInput(BaseModel):
            """Esquema de entrada para la herramienta de búsqueda en documentos institucionales"""
            query: str = Field(
                description="La consulta o palabra clave para buscar en los documentos de la policía de Hermosillo. Ejemplos: 'organigrama', 'Tu voz en QR', 'funciones de la comisaría general', 'procedimientos de audiencia', 'ley de tránsito', 'justicia cívica', 'multas', 'proyectos institucionales'"
            )
        
        def search_documents(query: str) -> str:
            """
            Busca información en los documentos institucionales de la Jefatura de Policía.
            
            Esta herramienta permite buscar información específica sobre estructura,
            departamentos, funciones, responsabilidades, procedimientos, horarios,
            leyes de tránsito, justicia cívica, multas y cualquier otra información
            documentada en los documentos oficiales de la Jefatura de Policía Preventiva
            y Tránsito Municipal de Hermosillo.
            
            Args:
                query: Pregunta clara o tema específico para buscar en los documentos
                
            Returns:
                Información relevante de los documentos con indicadores de relevancia
            """
            # DIAGNÓSTICO HIPÓTESIS 4: Verificar argumentos Pydantic
            print(f"[DEBUG TOOL] search_documents llamada con query: {query}")
            print(f"[DEBUG TOOL] Tipo de query: {type(query)}")
            
            # Verificar que el vector store esté cargado
            if self.vector_store_manager.vector_store is None:
                error_msg = "[ERROR] El vector store no está inicializado. No se puede buscar en los documentos."
                print(error_msg)
                return error_msg
            
            try:
                results = self.vector_store_manager.similarity_search(query, k=3)
                
                if not results:
                    return "No se encontró información relacionada en los documentos institucionales."
                
                context = "\n---\n".join([
                    f"[RELEVANCIA: {100-(i*25)}%]\n{doc.page_content}"
                    for i, doc in enumerate(results)
                ])
                
                return context
            except Exception as e:
                error_msg = f"[ERROR] Error al buscar en los documentos: {str(e)}"
                print(error_msg)
                return error_msg
        
        tools = [
            Tool(
                name="buscar_documentos_policia",
                func=search_documents,
                description="""
                Busca cualquier información oficial, legal o institucional de la Policía de Hermosillo.
                
                Esta herramienta tiene acceso a TODOS los documentos oficiales de la dependencia:
                - Manual de Organización de la DGSP
                - Ley de Tránsito y reglamentos viales
                - Reglamentos de Justicia Cívica
                - Proyectos institucionales como "Tu voz en QR"
                - Normas sobre multas y sanciones
                - Procedimientos y trámites ciudadanos
                - Cualquier otro documento oficial de la corporación
                
                USA ESTA HERRAMIENTA SIEMPRE que el usuario pregunte sobre:
                - Estructura organizacional y organigrama
                - Funciones y responsabilidades de departamentos
                - Leyes de tránsito y reglamentos viales
                - Justicia cívica y procedimientos administrativos
                - Multas, sanciones y procedimientos de infracción
                - Trámites ciudadanos y procedimientos
                - Horarios y operaciones
                - Normas y regulaciones
                - Proyectos institucionales y tecnológicos
                - Cualquier información documentada en los archivos oficiales
                
                Input: pregunta clara o tema específico relacionado con la Policía de Hermosillo
                """,
                args_schema=SearchDocumentsInput
            ),
        ]
        
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
Eres el Asistente de la Jefatura de Policía Preventiva y de Tránsito de Hermosillo.

TU FUNCIÓN:
Responder preguntas sobre trámites, leyes de tránsito, justicia cívica, multas, estructura y proyectos institucionales.

DOCUMENTOS DISPONIBLES:
Tienes acceso a un repositorio documental oficial que incluye:
- Manual de Organización de la DGSP
- Ley de Tránsito y reglamentos viales
- Reglamentos de Justicia Cívica
- Proyectos institucionales como "Tu voz en QR"
- Normas sobre multas y sanciones
- Procedimientos ciudadanos

INSTRUCCIONES ESTRICTAS:

1. USA LA HERRAMIENTA DE BÚSQUEDA siempre para verificar datos
2. RESPONDE SOLO con información de los documentos
3. Cuando necesites buscar información, tienes total libertad de generar los pensamientos internos necesarios (Tool Calls) en el formato técnico que requiere el sistema. No limites tu razonamiento interno.
4. Tu RESPUESTA FINAL al ciudadano debe ser directa, concisa, sin introducciones largas ni conclusiones con advertencias legales o disclaimers (como 'consulte a un profesional'). Si usas listas, sé breve y usa negritas.
5. Si NO encuentras información: responde en UNA sola oración: "No encontré registro de esa información en los documentos oficiales de la corporación."
6. NUNCA digas al usuario que consulte documentos — TÚ das la respuesta directa
7. NUNCA inventes información ni hagas suposiciones

CONTEXTO PREVIO:
{context}

Pregunta del usuario: usa la herramienta de búsqueda, genera el razonamiento interno necesario, y entrega la respuesta final directa al ciudadano."""
        
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
            max_iterations=10,
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
        
        # DIAGNÓSTICO HIPÓTESIS 1: Verificar input recibido
        print(f"[DEBUG AGENT] Input recibido en ask(): {question}")
        print(f"[DEBUG AGENT] Tipo de dato: {type(question)}")
        
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
            # DIAGNÓSTICO HIPÓTESIS 2: Verificar historial de chat
            raw_history = self.memory.get_session_history(self.session_id, limit=5)
            print(f"[DEBUG AGENT] Historial raw: {raw_history}")
            langchain_history = self._convert_history_to_langchain_format(raw_history)
            print(f"[DEBUG AGENT] Historial LangChain: {langchain_history}")
            
            # DIAGNÓSTICO HIPÓTESIS 3: Verificar System Prompt
            print(f"[DEBUG AGENT] AgentExecutor inicializado: {self.agent}")
            print(f"[DEBUG AGENT] Tools disponibles: {[tool.name for tool in self.agent.tools]}")
            
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
