"""
Módulo para cargar y procesar documentos PDF
Objetivo: Extraer texto del manual y dividirlo en chunks manejables
"""

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List
from langchain_core.documents import Document


class DocumentProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Inicializa el procesador de documentos
        
        Args:
            chunk_size: Tamaño de cada chunk en caracteres
            chunk_overlap: Superposición entre chunks (para continuidad)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", " ", ""]
        )
    
    def load_pdf(self, pdf_path: str) -> str:
        """
        Carga un archivo PDF y extrae el texto
        
        Args:
            pdf_path: Ruta del archivo PDF
            
        Returns:
            Texto extraído del PDF
        """
        try:
            reader = PdfReader(pdf_path)
            text = ""
            
            print(f"Leyendo PDF: {pdf_path}")
            print(f"   Total de páginas: {len(reader.pages)}")
            
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                text += page_text + "\n"
                
                if page_num % 10 == 0:
                    print(f"   [*] Procesadas {page_num} páginas...")
            
            print(f"[OK] PDF cargado exitosamente ({len(text)} caracteres)")
            return text
            
        except Exception as e:
            print(f"[ERROR] Error al cargar PDF: {e}")
            raise
    
    def split_into_chunks(self, text: str, source: str = "manual") -> List[Document]:
        """
        Divide el texto en chunks más pequeños
        
        Args:
            text: Texto a dividir
            source: Fuente del documento (para metadata)
            
        Returns:
            Lista de Document objects con metadata
        """
        chunks = self.splitter.split_text(text)
        
        documents = [
            Document(
                page_content=chunk,
                metadata={
                    "source": source,
                    "chunk_id": i,
                    "length": len(chunk)
                }
            )
            for i, chunk in enumerate(chunks)
        ]
        
        print(f"[INFO] Documento dividido en {len(documents)} chunks")
        print(f"   - Tamaño promedio: {sum(len(d.page_content) for d in documents) // len(documents)} caracteres")
        
        return documents


def prepare_documents(pdf_path: str) -> List[Document]:
    """
    Función auxiliar para cargar y procesar un PDF en un paso
    
    Args:
        pdf_path: Ruta del archivo PDF
        
    Returns:
        Lista de documentos procesados y divididos
    """
    processor = DocumentProcessor(chunk_size=1000, chunk_overlap=200)
    text = processor.load_pdf(pdf_path)
    documents = processor.split_into_chunks(text)
    return documents
