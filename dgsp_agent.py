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
    def __init__(self, pdf_path: str, session_id: str = "default"):
        """
        Inicializa el agente
        
        Args:
            pdf_path: Ruta del archivo PDF del manual
            session_id: ID de la sesión actual
        """
        self.session_id = session_id
        self.pdf_path = pdf_path
        
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
                documents = prepare_documents(self.pdf_path)
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
        class SearchManualInput(BaseModel):
            """Esquema de entrada para la herramienta de búsqueda en el manual"""
            query: str = Field(
                description="Pregunta clara o tema específico para buscar en el manual de organización de la DGSP. Ejemplos: 'organigrama', 'funciones de la comisaría general', 'procedimientos de audiencia'"
            )
        
        def search_manual(query: str) -> str:
            """
            Busca información en el manual de organización de la DGSP.
            
            Esta herramienta permite buscar información específica sobre la estructura,
            departamentos, funciones, responsabilidades, procedimientos, horarios y
            cualquier otra información documentada en el manual de la Jefatura de
            Policía Preventiva y Tránsito Municipal de Hermosillo.
            
            Args:
                query: Pregunta clara o tema específico para buscar en el manual
                
            Returns:
                Información relevante del manual con indicadores de relevancia
            """
            # Verificar que el vector store esté cargado
            if self.vector_store_manager.vector_store is None:
                error_msg = "[ERROR] El vector store no está inicializado. No se puede buscar en el manual."
                print(error_msg)
                return error_msg
            
            try:
                results = self.vector_store_manager.similarity_search(query, k=3)
                
                if not results:
                    return "No se encontró información relacionada en el manual."
                
                context = "\n---\n".join([
                    f"[RELEVANCIA: {100-(i*25)}%]\n{doc.page_content}"
                    for i, doc in enumerate(results)
                ])
                
                return context
            except Exception as e:
                error_msg = f"[ERROR] Error al buscar en el manual: {str(e)}"
                print(error_msg)
                return error_msg
        
        tools = [
            Tool(
                name="search_manual",
                func=search_manual,
                description="""
                Busca información en el manual de organización de la DGSP (Jefatura de Policía Preventiva y Tránsito Municipal de Hermosillo).
                
                Usa esta herramienta cuando el usuario pregunte sobre:
                - Estructura organizacional y organigrama
                - Funciones y responsabilidades de departamentos
                - Procedimientos y procesos internos
                - Horarios y operaciones
                - Normas y regulaciones
                - Cualquier información documentada en el manual oficial
                
                Input: pregunta clara o tema específico relacionado con la DGSP
                """,
                args_schema=SearchManualInput
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
        system_prompt = """Eres un asistente experto sobre la Dirección General de Seguridad 
Pública (DGSP) / Jefatura de Policía Preventiva y Tránsito Municipal de Hermosillo, Sonora.

INSTRUCCIONES CRÍTICAS:
1. SOLO responde basándote en la documentación del manual disponible
2. SI no encuentras la información en el manual, dilo claramente
3. NUNCA hagas suposiciones ni inventes información
4. Cita siempre de dónde obtuviste la información
5. Si la pregunta está fuera del ámbito del manual, explica que no está documentado
6. Sé conciso y útil en tus respuestas

MANEJO DEL HISTORIAL DE CONVERSACIÓN:
- El historial de conversación contiene preguntas y respuestas anteriores
- Si el usuario hace una pregunta ambigua o de seguimiento (ej: "repite por favor", "¿y eso?"), 
  usa el contexto del historial para entender a qué se refiere
- Si la pregunta no tiene contexto claro, responde basándote en la información más reciente del historial
- NO intentes buscar en el manual preguntas que son solo de seguimiento o repetición

CONTEXTO PREVIO:
{context}

Cuando el usuario pregunte, busca primero en el manual y luego responde con precisión.
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
            raw_history = self.memory.get_session_history(self.session_id, limit=5)
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
    
    # Ruta del PDF (IMPORTANTE: reemplaza con tu ruta)
    PDF_PATH = "./manual_dgsp.pdf"  # Cambia esto a tu ruta
    
    # Generar session_id único basado en timestamp
    session_id = f"sesion_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Crear agente con session_id único
    agent = DGSPAgent(pdf_path=PDF_PATH, session_id=session_id)
    
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
