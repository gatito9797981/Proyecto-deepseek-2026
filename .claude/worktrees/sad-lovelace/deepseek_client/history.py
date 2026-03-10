"""
Módulo de gestión de historial de conversaciones.

Este módulo proporciona funcionalidades para:
    - Almacenar conversaciones
    - Recuperar historial
    - Exportar/importar conversaciones
    - Búsqueda en el historial

Formatos soportados:
    - JSON (por defecto)
    - Markdown
    - Texto plano
"""

import os
import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
import logging


@dataclass
class Message:
    """
    Representa un mensaje en la conversación.
    
    Attributes:
        id: ID único del mensaje
        role: Rol del mensaje ('user', 'assistant', 'system')
        content: Contenido del mensaje
        timestamp: Timestamp del mensaje
        metadata: Metadatos adicionales (tokens, modelo, etc.)
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    role: str = "user"
    content: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el mensaje a diccionario."""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Crea un mensaje desde un diccionario."""
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            metadata=data.get("metadata", {})
        )
    
    def to_openai_format(self) -> Dict[str, str]:
        """Convierte al formato esperado por la API de OpenAI."""
        return {
            "role": self.role,
            "content": self.content
        }


@dataclass
class Conversation:
    """
    Representa una conversación completa.
    
    Attributes:
        id: ID único de la conversación
        title: Título de la conversación
        messages: Lista de mensajes
        created_at: Fecha de creación
        updated_at: Fecha de última actualización
        metadata: Metadatos adicionales
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    title: str = "Nueva conversación"
    messages: List[Message] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: str, content: str, metadata: Dict = None) -> Message:
        """
        Añade un mensaje a la conversación.
        
        Args:
            role: Rol del mensaje
            content: Contenido
            metadata: Metadatos opcionales
        
        Returns:
            Message: Mensaje creado
        """
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.updated_at = datetime.now().isoformat()
        
        # Auto-generar título si es el primer mensaje del usuario
        if len(self.messages) == 1 and role == "user":
            self.title = content[:50] + ("..." if len(content) > 50 else "")
        
        return message
    
    def get_last_messages(self, n: int = 10) -> List[Message]:
        """
        Obtiene los últimos N mensajes.
        
        Args:
            n: Número de mensajes
        
        Returns:
            List[Message]: Últimos mensajes
        """
        return self.messages[-n:]
    
    def get_messages_for_api(self, max_tokens: int = 4000) -> List[Dict[str, str]]:
        """
        Obtiene mensajes en formato API, respetando límite de tokens.
        
        Args:
            max_tokens: Límite aproximado de tokens
        
        Returns:
            List[Dict]: Mensajes en formato API
        """
        # Estimación simple: ~4 caracteres por token
        max_chars = max_tokens * 4
        
        result = []
        total_chars = 0
        
        # Empezar desde el final, mantener contexto
        for message in reversed(self.messages):
            msg_chars = len(message.content)
            if total_chars + msg_chars > max_chars:
                break
            
            result.insert(0, message.to_openai_format())
            total_chars += msg_chars
        
        return result
    
    def clear_messages(self):
        """Limpia todos los mensajes de la conversación."""
        self.messages = []
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la conversación a diccionario."""
        return {
            "id": self.id,
            "title": self.title,
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        """Crea una conversación desde un diccionario."""
        messages = [Message.from_dict(m) for m in data.get("messages", [])]
        
        return cls(
            id=data.get("id", str(uuid.uuid4())[:12]),
            title=data.get("title", "Nueva conversación"),
            messages=messages,
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            metadata=data.get("metadata", {})
        )
    
    def get_token_count(self) -> int:
        """Estima el número de tokens en la conversación."""
        total_chars = sum(len(m.content) for m in self.messages)
        return total_chars // 4  # Estimación simple


class HistoryManager:
    """
    Gestor de historial de conversaciones.
    
    Proporciona funcionalidades para:
        - Guardar/cargar conversaciones
        - Listar conversaciones
        - Buscar en el historial
        - Exportar conversaciones
    """
    
    def __init__(self, history_dir: str = None):
        """
        Inicializa el gestor de historial.
        
        Args:
            history_dir: Directorio para almacenar el historial
        """
        self.history_dir = Path(history_dir or os.path.join(os.getcwd(), "chat_history"))
        self.history_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("deepseek_client.history")
        self._current_conversation: Optional[Conversation] = None
    
    @property
    def current_conversation(self) -> Conversation:
        """Obtiene la conversación actual, creando una nueva si es necesario."""
        if self._current_conversation is None:
            self._current_conversation = Conversation()
        return self._current_conversation
    
    def new_conversation(self, title: str = None) -> Conversation:
        """
        Crea una nueva conversación.
        
        Args:
            title: Título opcional
        
        Returns:
            Conversation: Nueva conversación
        """
        self._current_conversation = Conversation(title=title or "Nueva conversación")
        return self._current_conversation
    
    def save_conversation(self, conversation: Conversation = None) -> str:
        """
        Guarda una conversación en disco.
        
        Args:
            conversation: Conversación a guardar (usa la actual si es None)
        
        Returns:
            str: Ruta del archivo guardado
        """
        conv = conversation or self._current_conversation
        if conv is None:
            raise ValueError("No hay conversación para guardar")
        
        filepath = self.history_dir / f"{conv.id}.json"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(conv.to_dict(), f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Conversación guardada: {filepath}")
        return str(filepath)
    
    def load_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Carga una conversación desde disco.
        
        Args:
            conversation_id: ID de la conversación
        
        Returns:
            Conversation o None si no existe
        """
        filepath = self.history_dir / f"{conversation_id}.json"
        
        if not filepath.exists():
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        conversation = Conversation.from_dict(data)
        self._current_conversation = conversation
        
        return conversation
    
    def list_conversations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Lista todas las conversaciones guardadas.
        
        Args:
            limit: Número máximo a listar
        
        Returns:
            List[Dict]: Lista de conversaciones con metadatos
        """
        conversations = []
        
        for filepath in sorted(
            self.history_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        ):
            if len(conversations) >= limit:
                break
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                conversations.append({
                    "id": data.get("id"),
                    "title": data.get("title", "Sin título"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "message_count": len(data.get("messages", [])),
                })
            except Exception as e:
                self.logger.warning(f"Error leyendo {filepath}: {e}")
        
        return conversations
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Elimina una conversación.
        
        Args:
            conversation_id: ID de la conversación
        
        Returns:
            bool: True si se eliminó correctamente
        """
        filepath = self.history_dir / f"{conversation_id}.json"
        
        if filepath.exists():
            filepath.unlink()
            
            # Limpiar conversación actual si es la eliminada
            if self._current_conversation and self._current_conversation.id == conversation_id:
                self._current_conversation = None
            
            return True
        
        return False
    
    def search_conversations(self, query: str) -> List[Dict[str, Any]]:
        """
        Busca en el historial de conversaciones.
        
        Args:
            query: Texto a buscar
        
        Returns:
            List[Dict]: Resultados de búsqueda
        """
        results = []
        query_lower = query.lower()
        
        for filepath in self.history_dir.glob("*.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Buscar en título y mensajes
                found = False
                matching_messages = []
                
                if query_lower in data.get("title", "").lower():
                    found = True
                
                for msg in data.get("messages", []):
                    if query_lower in msg.get("content", "").lower():
                        found = True
                        matching_messages.append({
                            "role": msg.get("role"),
                            "content": msg.get("content")[:200] + "..."
                        })
                
                if found:
                    results.append({
                        "id": data.get("id"),
                        "title": data.get("title"),
                        "matching_messages": matching_messages[:3]
                    })
            
            except Exception as e:
                self.logger.warning(f"Error buscando en {filepath}: {e}")
        
        return results
    
    def export_conversation(
        self,
        conversation_id: str,
        format: str = "markdown",
        output_path: str = None
    ) -> str:
        """
        Exporta una conversación a un formato específico.
        
        Args:
            conversation_id: ID de la conversación
            format: Formato de exportación ('markdown', 'json', 'txt')
            output_path: Ruta de salida (opcional)
        
        Returns:
            str: Ruta del archivo exportado
        """
        conversation = self.load_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversación no encontrada: {conversation_id}")
        
        if format == "json":
            content = json.dumps(conversation.to_dict(), indent=2, ensure_ascii=False)
            ext = "json"
        
        elif format == "markdown" or format == "md":
            content = self._to_markdown(conversation)
            ext = "md"
        
        else:  # txt
            content = self._to_text(conversation)
            ext = "txt"
        
        if output_path is None:
            output_path = str(self.history_dir / f"{conversation_id}.{ext}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return output_path
    
    def _to_markdown(self, conversation: Conversation) -> str:
        """Convierte una conversación a Markdown."""
        lines = [
            f"# {conversation.title}",
            "",
            f"*Creado: {conversation.created_at}*",
            f"*Actualizado: {conversation.updated_at}*",
            "",
            "---",
            ""
        ]
        
        for msg in conversation.messages:
            role_emoji = "👤" if msg.role == "user" else "🤖"
            role_name = "Usuario" if msg.role == "user" else "Asistente"
            
            lines.append(f"### {role_emoji} {role_name}")
            lines.append(f"*{msg.timestamp}*")
            lines.append("")
            lines.append(msg.content)
            lines.append("")
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
    
    def _to_text(self, conversation: Conversation) -> str:
        """Convierte una conversación a texto plano."""
        lines = [
            f"Conversación: {conversation.title}",
            f"Creado: {conversation.created_at}",
            "",
        ]
        
        for msg in conversation.messages:
            role = "Usuario" if msg.role == "user" else "Asistente"
            lines.append(f"[{role}] {msg.timestamp}")
            lines.append(msg.content)
            lines.append("")
        
        return "\n".join(lines)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del historial.
        
        Returns:
            Dict: Estadísticas
        """
        total_conversations = 0
        total_messages = 0
        total_tokens = 0
        
        for filepath in self.history_dir.glob("*.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                total_conversations += 1
                total_messages += len(data.get("messages", []))
                
                for msg in data.get("messages", []):
                    total_tokens += len(msg.get("content", "")) // 4
            
            except Exception:
                continue
        
        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "estimated_tokens": total_tokens,
            "history_dir": str(self.history_dir)
        }
    
    def clear_all(self):
        """Elimina todo el historial."""
        for filepath in self.history_dir.glob("*.json"):
            filepath.unlink()
        
        self._current_conversation = None
        self.logger.info("Historial limpiado completamente")


def create_history_manager(history_dir: str = None) -> HistoryManager:
    """
    Función de conveniencia para crear un gestor de historial.
    
    Args:
        history_dir: Directorio para el historial
    
    Returns:
        HistoryManager: Gestor de historial
    """
    return HistoryManager(history_dir)
