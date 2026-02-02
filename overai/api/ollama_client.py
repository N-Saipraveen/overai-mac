"""
Ollama API client for local LLM communication.
Handles HTTP requests to Ollama running as a macOS background service.
"""

import json
import urllib.request
import urllib.error
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass

from ..utils.logger import Logger

logger = Logger("OllamaClient")

OLLAMA_BASE_URL = "http://127.0.0.1:11434"


@dataclass
class OllamaModel:
    """Represents an Ollama model."""
    name: str
    size: int = 0
    
    @property
    def display_name(self) -> str:
        """Get display name (without tag)."""
        return self.name.split(':')[0]


class OllamaClient:
    """
    Client for communicating with Ollama API.
    Uses HTTP requests which work reliably from Python.
    """
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
        self._available_models: List[OllamaModel] = []
    
    def is_running(self) -> bool:
        """Check if Ollama is running."""
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/tags",
                method="GET"
            )
            req.add_header("Content-Type", "application/json")
            
            with urllib.request.urlopen(req, timeout=3) as response:
                return response.status == 200
        except Exception as e:
            logger.debug(f"Ollama not reachable: {e}")
            return False
    
    def get_models(self) -> List[OllamaModel]:
        """Get list of available models."""
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/tags",
                method="GET"
            )
            req.add_header("Content-Type", "application/json")
            
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                models = data.get('models', [])
                self._available_models = [
                    OllamaModel(
                        name=m.get('name', ''),
                        size=m.get('size', 0)
                    )
                    for m in models
                ]
                logger.info(f"Found {len(self._available_models)} Ollama models")
                return self._available_models
                
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            return []
    
    def chat(self, model: str, messages: List[Dict], stream: bool = False) -> str:
        """
        Send chat request to Ollama.
        
        Args:
            model: Model name (e.g., "llama3.2")
            messages: List of message dicts with 'role' and 'content'
            stream: Whether to stream response (not implemented yet)
        
        Returns:
            Assistant's response text
        """
        try:
            data = {
                "model": model,
                "messages": messages,
                "stream": False  # Non-streaming for simplicity
            }
            
            req = urllib.request.Request(
                f"{self.base_url}/api/chat",
                data=json.dumps(data).encode('utf-8'),
                method="POST"
            )
            req.add_header("Content-Type", "application/json")
            
            logger.debug(f"Sending chat to {model}")
            
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode('utf-8'))
                content = result.get('message', {}).get('content', '')
                logger.debug(f"Got response: {len(content)} chars")
                return content
                
        except urllib.error.URLError as e:
            logger.error(f"Network error: {e}")
            return f"Error: Cannot reach Ollama - {e.reason}"
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return f"Error: {str(e)}"


# Singleton instance
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """Get singleton Ollama client."""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client
