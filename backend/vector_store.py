"""
Módulo para crear y gestionar el vector store usando FAISS
Objetivo: Permite buscar similitud en el manual sin conectarse a internet
"""

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from typing import List
import os


class VectorStoreManager:
    def __init__(self, store_path: str = "./faiss_index"):
        """
        Inicializa el gestor del vector store
        
        Args:
            store_path: Ruta donde se guardará el índice FAISS
        """
        self.store_path = store_path
        self.embeddings = None
        self.vector_store = None
        
        # Inicializa embeddings de HuggingFace (descargados localmente)
        self._init_embeddings()
    
    def _init_embeddings(self):
        """Inicializa el modelo de embeddings"""
        print("[SETUP] Inicializando modelo de embeddings (HuggingFace)...")
        try:
            # Obtener HF_TOKEN si está configurado
            hf_token = os.getenv("HF_TOKEN")
            
            # Configurar embeddings con o sin token
            if hf_token:
                self.embeddings = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2",
                    model_kwargs={"device": "cpu"},
                    encode_kwargs={"normalize_embeddings": True}
                )
                print("[OK] Embeddings cargados correctamente (autenticado)")
            else:
                self.embeddings = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2",
                    model_kwargs={"device": "cpu"},
                    encode_kwargs={"normalize_embeddings": True}
                )
                print("[OK] Embeddings cargados correctamente (sin autenticación)")
        except Exception as e:
            print(f"[ERROR] Error al cargar embeddings: {e}")
            raise
    
    def create_vector_store(self, documents: List[Document]) -> FAISS:
        """
        Crea un vector store a partir de documentos
        
        Args:
            documents: Lista de documentos (Document objects)
            
        Returns:
            Vector store de FAISS
        """
        print(f"\n[PROCESS] Creando vector store con {len(documents)} documentos...")
        
        try:
            self.vector_store = FAISS.from_documents(
                documents=documents,
                embedding=self.embeddings
            )
            print(f"[OK] Vector store creado exitosamente")
            return self.vector_store
        except Exception as e:
            print(f"[ERROR] Error al crear vector store: {e}")
            raise
    
    def save_vector_store(self):
        """Guarda el vector store en disco"""
        if self.vector_store is None:
            print("[WARNING] No hay vector store para guardar")
            return
        
        print(f"[SAVE] Guardando vector store en: {self.store_path}")
        self.vector_store.save_local(self.store_path)
        print("[OK] Vector store guardado")
    
    def load_vector_store(self) -> FAISS:
        """Carga un vector store existente"""
        if not os.path.exists(self.store_path):
            print(f"[WARNING] No se encontró vector store en: {self.store_path}")
            return None
        
        print(f"[LOAD] Cargando vector store desde: {self.store_path}")
        try:
            self.vector_store = FAISS.load_local(
                self.store_path,
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            print("[OK] Vector store cargado")
            return self.vector_store
        except Exception as e:
            print(f"[ERROR] Error al cargar vector store: {e}")
            raise
    
    def similarity_search(self, query: str, k: int = 3) -> List[Document]:
        """
        Busca documentos similares a la consulta
        
        Args:
            query: Pregunta o texto de búsqueda
            k: Número de resultados a devolver
            
        Returns:
            Lista de documentos más similares
        """
        if self.vector_store is None:
            print("[ERROR] Vector store no cargado")
            return []
        
        results = self.vector_store.similarity_search(query, k=k)
        return results
    
    def get_retriever(self, k: int = 3):
        """
        Devuelve un retriever para usar en el agente
        
        Args:
            k: Número de documentos a recuperar
            
        Returns:
            Retriever object
        """
        if self.vector_store is None:
            print("[ERROR] Vector store no cargado")
            return None
        
        return self.vector_store.as_retriever(search_kwargs={"k": k})
