from typing import Optional, List, Dict
from datetime import datetime
import uuid
import threading
from app.copilot.schemas.copilot import Conversation, ConversationMessage

class ConversationRepository:
    def create_conversation(self, investigation_id: str) -> Conversation:
        raise NotImplementedError
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        raise NotImplementedError
    
    def append_message(self, conversation_id: str, role: str, content: str, metadata: Optional[dict] = None) -> ConversationMessage:
        raise NotImplementedError

class InMemoryConversationRepository(ConversationRepository):
    def __init__(self):
        self._store: Dict[str, Conversation] = {}
        self._lock = threading.Lock()

    def create_conversation(self, investigation_id: str) -> Conversation:
        with self._lock:
            conv = Conversation(
                conversation_id=f"conv_{uuid.uuid4().hex[:8]}",
                investigation_id=investigation_id,
                created_at=datetime.utcnow()
            )
            self._store[conv.conversation_id] = conv
            return conv

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        with self._lock:
            return self._store.get(conversation_id)

    def append_message(self, conversation_id: str, role: str, content: str, metadata: Optional[dict] = None) -> ConversationMessage:
        with self._lock:
            conv = self._store.get(conversation_id)
            if not conv:
                raise ValueError("Conversation not found")
            msg = ConversationMessage(
                message_id=f"msg_{uuid.uuid4().hex[:8]}",
                role=role,
                content=content,
                timestamp=datetime.utcnow(),
                metadata=metadata
            )
            conv.messages.append(msg)
            return msg

# Global instance for MVP
_instance = InMemoryConversationRepository()

def get_conversation_repository() -> ConversationRepository:
    return _instance
