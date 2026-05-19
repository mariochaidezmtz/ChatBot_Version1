"""
Agente de IA para responder preguntas sobre la DGSP de Hermosillo
Objetivo: Usar solo la documentación local sin conectarse a internet
"""

import os
from typing import Optional
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

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
        try:
            # Intenta cargar vector store existente
            self.vector_store_manager.load_vector_store()
        except:
            # Si no existe, crea uno nuevo
            print("\n[PROCESS] Vector store no encontrado, creando nuevo...")
            documents = prepare_documents(self.pdf_path)
            self.vector_store_manager.create_vector_store(documents)
            self.vector_store_manager.save_vector_store()
    
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
        
        def search_manual(query: str) -> str:
            """
            Busca información en el manual de la DGSP
            
            Args:
                query: Pregunta o texto a buscar
                
            Returns:
                Información relevante del manual
            """
            results = self.vector_store_manager.similarity_search(query, k=3)
            
            if not results:
                return "No se encontró información relacionada en el manual."
            
            context = "\n---\n".join([
                f"[RELEVANCIA: {100-(i*25)}%]\n{doc.page_content}"
                for i, doc in enumerate(results)
            ])
            
            return context
        
        tools = [
            Tool(
                name="search_manual",
                func=search_manual,
                description="""
                Busca información en el manual de organización de la DGSP.
                Útil para: estructuras, departamentos, funciones, responsabilidades,
                procedimientos, horarios y cualquier información documentada.
                Input: pregunta clara o tema a buscar
                """
            ),
        ]
        
        return tools
    
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
            verbose=False,
            max_iterations=3,
            handle_parsing_errors=True
        )
        
        return executor
    
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
        
        # Obtener contexto del historial
        context = ""
        if use_history:
            context = self.memory.get_context_summary(self.session_id, last_n=3)
        
        # Ejecutar agente
        try:
            response = self.agent.invoke({
                "input": question,
                "context": context,
                "chat_history": self.memory.get_session_history(self.session_id, limit=5)
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
    
    # Crear agente
    agent = DGSPAgent(pdf_path=PDF_PATH, session_id="sesion_demo_001")
    
    print("\n" + "="*60)
    print("CHATBOT DGSP HERMOSILLO")
    print("Escribe 'salir' para terminar")
    print("Escribe 'historial' para ver la conversación")
    print("="*60 + "\n")
    
    while True:
        try:
            question = input("Tú: ").strip()
            
            if not question:
                continue
            
            if question.lower() == "salir":
                print("\n[OK] Hasta luego!")
                break
            
            if question.lower() == "historial":
                agent.show_history()
                continue
            
            # Hacer pregunta
            agent.ask(question)
            
        except KeyboardInterrupt:
            print("\n\n[OK] Hasta luego!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
