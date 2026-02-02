"""
API Service models for custom AI endpoints.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from enum import Enum


class APIFormat(Enum):
    """Supported API formats."""
    OPENAI = "openai"  # OpenAI-compatible API
    ANTHROPIC = "anthropic"  # Claude API
    CUSTOM = "custom"  # Custom format


@dataclass
class APIService:
    """Base class for API-based AI services."""
    
    id: str
    name: str
    icon: str
    api_format: APIFormat
    base_url: str  # e.g., "https://api.openai.com/v1"
    models_endpoint: str = "/models"
    chat_endpoint: str = "/chat/completions"
    requires_api_key: bool = True
    default_model: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        data['api_format'] = self.api_format.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "APIService":
        """Create from dictionary."""
        data = data.copy()
        data['api_format'] = APIFormat(data.get('api_format', 'openai'))
        return cls(**data)
    
    def get_full_url(self, endpoint: str) -> str:
        """Get full URL for an endpoint."""
        base = self.base_url.rstrip('/')
        path = endpoint.lstrip('/')
        return f"{base}/{path}"


@dataclass  
class CustomAPIService(APIService):
    """User-defined custom API service."""
    
    user_defined: bool = True
    description: str = ""
    created_at: Optional[str] = None
    
    def __post_init__(self):
        if not self.id.startswith("custom_"):
            self.id = f"custom_{self.id}"
    
    @classmethod
    def create(cls, name: str, base_url: str, api_key: str, 
               api_format: APIFormat = APIFormat.OPENAI,
               default_model: str = None, description: str = "") -> "CustomAPIService":
        """
        Create a new custom API service.
        
        Args:
            name: Display name for the service
            base_url: Base URL for the API
            api_key: API key (stored separately)
            api_format: API format type
            default_model: Default model to use
            description: Optional description
        """
        import time
        
        service_id = f"custom_{name.lower().replace(' ', '_')}_{int(time.time())}"
        
        return cls(
            id=service_id,
            name=name,
            icon="bolt.horizontal.circle.fill",
            api_format=api_format,
            base_url=base_url,
            default_model=default_model or "gpt-3.5-turbo",
            description=description,
            created_at=str(int(time.time()))
        )


# Predefined API service templates
PREDEFINED_APIS = {
    "openai": APIService(
        id="openai",
        name="OpenAI",
        icon="circle.grid.2x2",
        api_format=APIFormat.OPENAI,
        base_url="https://api.openai.com/v1",
        default_model="gpt-4"
    ),
    "anthropic": APIService(
        id="anthropic",
        name="Anthropic Claude",
        icon="quote.bubble.fill",
        api_format=APIFormat.ANTHROPIC,
        base_url="https://api.anthropic.com/v1",
        chat_endpoint="/messages",
        default_model="claude-3-opus-20240229"
    ),
    "groq": APIService(
        id="groq",
        name="Groq",
        icon="bolt.fill",
        api_format=APIFormat.OPENAI,
        base_url="https://api.groq.com/openai/v1",
        default_model="llama3-70b-8192"
    ),
    "ollama": APIService(
        id="ollama",
        name="Ollama (Local)",
        icon="desktopcomputer",
        api_format=APIFormat.OPENAI,
        base_url="http://localhost:11434/v1",
        default_model="llama2",
        requires_api_key=False
    ),
    "openrouter": APIService(
        id="openrouter",
        name="OpenRouter",
        icon="network",
        api_format=APIFormat.OPENAI,
        base_url="https://openrouter.ai/api/v1",
        default_model="anthropic/claude-3-opus"
    ),
}
