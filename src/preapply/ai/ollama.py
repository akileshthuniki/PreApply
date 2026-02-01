"""Ollama adapter for AI advisor (optional)."""

import os
from typing import Optional
from ..contracts.core_output import CoreOutput
from ..utils.errors import PreApplyError
from ..utils.logging import get_logger
from .base import AIAdvisor

logger = get_logger("ai.ollama")


class OllamaAdvisor(AIAdvisor):
    """
    Ollama-based AI advisor (local LLM).
    
    Requires Ollama to be installed and running locally.
    """
    
    def __init__(self, model: str = "llama3.2", base_url: Optional[str] = None):
        """
        Initialize Ollama advisor.
        
        Args:
            model: Ollama model name (default: llama3.2)
            base_url: Ollama API base URL (default: http://localhost:11434)
        """
        self.model = model
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._check_ollama_available()
    
    def _check_ollama_available(self) -> None:
        """Check if Ollama is available."""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            response.raise_for_status()
        except Exception as e:
            raise PreApplyError(
                f"Ollama not available at {self.base_url}. "
                f"Make sure Ollama is installed and running. Error: {e}"
            )
    
    def ask(
        self,
        core_output: CoreOutput,
        question: str,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Ask Ollama about the CoreOutput.
        
        Args:
            core_output: CoreOutput from analysis
            question: User's question
            max_tokens: Optional max tokens (Ollama uses num_predict)
            
        Returns:
            Advisory response from Ollama
        """
        from .prompt import build_prompt
        
        try:
            import requests
        except ImportError:
            raise PreApplyError("requests package required for Ollama adapter. Install with: pip install requests")
        
        prompt = build_prompt(core_output, question)
        
        # Ollama API request
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        if max_tokens:
            payload["options"] = {"num_predict": max_tokens}
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "").strip()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API error: {e}")
            raise PreApplyError(f"Failed to get response from Ollama: {e}")
    
    def is_available(self) -> bool:
        """Check if Ollama is available."""
        try:
            self._check_ollama_available()
            return True
        except PreApplyError:
            return False
