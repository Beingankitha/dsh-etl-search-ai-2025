"""
Chat and RAG services for conversational dataset discovery.

Exports:
- OllamaService: LLM inference via Ollama
- ChatService: Conversational interface with RAG
- ChatServiceError: Exception for chat service failures
"""

from .ollama_service import OllamaService, OllamaServiceError
from .chat_service import ChatService, ChatServiceError

__all__ = [
    "OllamaService",
    "OllamaServiceError",
    "ChatService",
    "ChatServiceError",
]
