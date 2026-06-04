"""
Módulo para gestionar la memoria del agente usando SQLite
Objetivo: Guardar historial de conversaciones y contexto
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import json


class ConversationMemory:
    def __init__(self, db_path: str = "./agent_memory.db"):
        """
        Inicializa la memoria del agente
        
        Args:
            db_path: Ruta del archivo de base de datos SQLite
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Crea las tablas si no existen"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla de conversaciones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_message TEXT NOT NULL,
                agent_response TEXT NOT NULL,
                context TEXT,
                source_documents TEXT
            )
        """)
        
        # Tabla de sesiones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
                topic TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        print("[OK] Base de datos inicializada")
    
    def create_session(self, session_id: str, topic: str = "General") -> str:
        """
        Crea una nueva sesión
        
        Args:
            session_id: ID único para la sesión
            topic: Tema de la sesión
            
        Returns:
            session_id
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO sessions (session_id, topic)
            VALUES (?, ?)
        """, (session_id, topic))
        
        conn.commit()
        conn.close()
        print(f"[OK] Sesión creada: {session_id}")
        return session_id
    
    def save_interaction(
        self,
        session_id: str,
        user_message: str,
        agent_response: str,
        context: Optional[str] = None,
        source_docs: Optional[List[str]] = None
    ):
        """
        Guarda una interacción en la memoria
        
        Args:
            session_id: ID de la sesión
            user_message: Pregunta del usuario
            agent_response: Respuesta del agente
            context: Contexto adicional
            source_docs: Lista de fuentes consultadas
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        source_json = json.dumps(source_docs) if source_docs else None
        
        cursor.execute("""
            INSERT INTO conversations
            (session_id, user_message, agent_response, context, source_documents)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, user_message, agent_response, context, source_json))
        
        # Actualiza last_activity de la sesión
        cursor.execute("""
            UPDATE sessions
            SET last_activity = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """, (session_id,))
        
        conn.commit()
        conn.close()
    
    def get_session_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """
        Obtiene el historial de una sesión
        
        Args:
            session_id: ID de la sesión
            limit: Número máximo de interacciones a devolver
            
        Returns:
            Lista de diccionarios con el historial
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_message, agent_response, context, timestamp
            FROM conversations
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (session_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = [
            {
                "user": row[0],
                "agent": row[1],
                "context": row[2],
                "timestamp": row[3]
            }
            for row in rows
        ]
        
        return history[::-1]  # Invertir para orden cronológico
    
    def get_context_summary(self, session_id: str, last_n: int = 5) -> str:
        """
        Genera un resumen del contexto de la sesión
        
        Args:
            session_id: ID de la sesión
            last_n: Últimas N interacciones a considerar
            
        Returns:
            Resumen en texto para usar como contexto
        """
        history = self.get_session_history(session_id, limit=last_n)
        
        if not history:
            return "No hay historial previo."
        
        summary = "📋 HISTORIAL DE LA SESIÓN:\n"
        for i, interaction in enumerate(history, 1):
            summary += f"\n{i}. Pregunta: {interaction['user']}\n"
            summary += f"   Respuesta: {interaction['agent'][:100]}...\n"
        
        return summary
    
    def list_sessions(self) -> List[Dict]:
        """
        Lista todas las sesiones
        
        Returns:
            Lista de sesiones
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT session_id, topic, created_at, last_activity
            FROM sessions
            ORDER BY last_activity DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        sessions = [
            {
                "session_id": row[0],
                "topic": row[1],
                "created_at": row[2],
                "last_activity": row[3]
            }
            for row in rows
        ]
        
        return sessions
    
    def delete_session(self, session_id: str):
        """
        Elimina una sesión y su historial
        
        Args:
            session_id: ID de la sesión a eliminar
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        
        conn.commit()
        conn.close()
        print(f"[OK] Sesión eliminada: {session_id}")
