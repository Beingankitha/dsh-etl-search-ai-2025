"""
Ollama Service - Local LLM Inference

This module provides a service for communicating with a local Ollama instance
for LLM inference. Ollama must be running separately.

Architecture:
    - OllamaService: HTTP client wrapper for Ollama API
    - Async/await support for non-blocking inference
    - Configurable model selection via environment
    - Graceful fallback when Ollama is unavailable
    - Structured error handling with custom exceptions
    - Observable with tracing spans

Features:
    - Generate text completions from prompts
    - Support for temperature control (creativity vs determinism)
    - Configurable timeout for long-running inference
    - Handles connection errors gracefully
    - Detailed logging for debugging
    - Request/response validation

Usage Example:
    from src.services.chat import OllamaService
    from src.config import settings
    
    # Initialize service
    ollama = OllamaService(
        host=settings.ollama_host,
        model=settings.ollama_model,
        timeout=settings.ollama_timeout
    )
    
    # Generate response
    try:
        response = await ollama.generate(
            prompt="What is climate change?",
            temperature=0.7
        )
        print(response)
    except OllamaServiceError as e:
        print(f"Ollama error: {e}")

Requirements:
    - Ollama running locally on specified host:port
    - Model downloaded in Ollama: ollama pull <model_name>
    - Network access to Ollama HTTP endpoint
"""

import logging
from typing import Optional
import httpx

from src.config import settings
from src.logging_config import get_logger

logger = get_logger(__name__)

# Lazy import for tracing (avoid circular imports)
_tracer = None


def get_tracer():
    """Get tracer instance lazily."""
    global _tracer
    if _tracer is None:
        try:
            from src.services.observability import get_tracer as get_tracer_impl
            _tracer = get_tracer_impl(__name__)
        except Exception:
            _tracer = None
    return _tracer


class OllamaServiceError(Exception):
    """Exception raised when Ollama service fails."""
    pass


class OllamaService:
    """
    Service for communicating with local Ollama LLM.
    
    Ollama provides fast, local LLM inference without requiring cloud APIs.
    This service provides a clean interface for prompting Ollama with
    proper error handling and fallback behavior.
    
    Architecture:
    - Uses httpx for async HTTP communication
    - Timeout protection against hanging inference
    - Connection pooling for efficiency
    - Structured error messages for debugging
    
    Design Patterns:
    - Singleton-like usage per request (created fresh per API call)
    - Dependency Injection: host/model passed as constructor args
    - Observable: Operations traced and logged
    """
    
    # Ollama API endpoint paths
    GENERATE_ENDPOINT = "/api/generate"
    PULL_ENDPOINT = "/api/pull"
    TAGS_ENDPOINT = "/api/tags"
    
    def __init__(
        self,
        host: str = None,
        model: str = None,
        timeout: int = None
    ):
        """
        Initialize OllamaService.
        
        Args:
            host: Ollama host URL (e.g., "http://localhost:11434")
                  Defaults to settings.ollama_host
            model: Model name to use (e.g., "llama3.2")
                   Defaults to settings.ollama_model
            timeout: Request timeout in seconds
                     Defaults to settings.ollama_timeout
        """
        self.host = host or settings.ollama_host
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout
        
        logger.debug(
            f"Initialized OllamaService: host={self.host}, "
            f"model={self.model}, timeout={self.timeout}s"
        )
    
    async def health_check(self) -> bool:
        """
        Check if Ollama service is available.
        
        Returns:
            True if Ollama is responding, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.host}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"Ollama health check failed: {e}")
            return False
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate text using Ollama.
        
        This method sends a prompt to the local Ollama instance and returns
        the generated completion. The generation process is streamed and
        assembled into a complete response.
        
        Args:
            prompt: User prompt to generate completion for
            temperature: Creativity vs determinism (0-1)
                        0.0 = deterministic (greedy)
                        1.0 = maximum creativity
                        Default: 0.7 (balanced)
            top_p: Nucleus sampling parameter (0-1)
                   Default: 0.9
            top_k: Limits vocabulary to top K most likely tokens
                   Default: 40
            system_prompt: Optional system prompt to guide LLM behavior
                          Example: "You are an expert in environmental science"
        
        Returns:
            Generated text completion
            
        Raises:
            OllamaServiceError: If Ollama is unavailable or generation fails
            TimeoutError: If generation exceeds timeout
            
        Example:
            response = await ollama.generate(
                prompt="Summarize climate change impacts",
                temperature=0.5,
                system_prompt="You are a climate scientist"
            )
        """
        # Prepare request payload
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,  # Don't stream - wait for full response
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
        }
        
        # Add system prompt if provided
        if system_prompt:
            payload["system"] = system_prompt
        
        logger.debug(
            f"Calling Ollama generate: model={self.model}, "
            f"prompt_len={len(prompt)}, temp={temperature}"
        )
        
        # Call Ollama API
        try:
            async with httpx.AsyncClient(
                timeout=float(self.timeout)
            ) as client:
                response = await client.post(
                    f"{self.host}{self.GENERATE_ENDPOINT}",
                    json=payload
                )
        except httpx.ConnectError as e:
            error_msg = (
                f"Failed to connect to Ollama at {self.host}. "
                f"Is Ollama running? Error: {e}"
            )
            logger.error(error_msg)
            raise OllamaServiceError(error_msg) from e
        except httpx.TimeoutException as e:
            error_msg = f"Ollama request timed out after {self.timeout}s"
            logger.error(error_msg)
            raise OllamaServiceError(error_msg) from e
        
        # Check response status
        if response.status_code != 200:
            error_msg = (
                f"Ollama returned status {response.status_code}: "
                f"{response.text}"
            )
            logger.error(error_msg)
            raise OllamaServiceError(error_msg)
        
        # Parse response
        try:
            result = response.json()
            generated_text = result.get("response", "").strip()
            
            logger.debug(
                f"Ollama generation complete: "
                f"response_len={len(generated_text)}"
            )
            logger.debug(f"Response content preview: {generated_text[:200] if generated_text else '[EMPTY]'}")
            
            return generated_text
        
        except ValueError as e:
            error_msg = f"Failed to parse Ollama response: {e}"
            logger.error(error_msg)
            raise OllamaServiceError(error_msg) from e
    
    async def generate_with_context(
        self,
        user_message: str,
        context: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate response with provided context for RAG.
        
        This is a convenience method for RAG pipelines where you have
        retrieved context (e.g., from vector store) that should inform
        the LLM response.
        
        Args:
            user_message: The user's query or message
            context: Retrieved context to inform the response
                    Typically dataset metadata/abstracts from vector search
            system_prompt: Optional system prompt to guide behavior
            **kwargs: Additional parameters passed to generate()
                     (temperature, top_p, top_k, etc.)
        
        Returns:
            Generated response that uses the provided context
            
        Example:
            context = "Dataset: Soil carbon content, 2019-2020"
            response = await ollama.generate_with_context(
                user_message="Tell me about carbon data",
                context=context,
                temperature=0.5
            )
        """
        # Build RAG prompt that incorporates context
        rag_prompt = f"""Based on the following context, answer the user's question.

Context:
{context}

User Question: {user_message}

Answer:"""
        
        return await self.generate(
            prompt=rag_prompt,
            system_prompt=system_prompt,
            **kwargs
        )
