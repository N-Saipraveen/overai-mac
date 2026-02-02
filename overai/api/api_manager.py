"""
Manager for API-based AI services.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import asdict

from .api_service import APIService, CustomAPIService, PREDEFINED_APIS, APIFormat
from .keychain import KeychainManager
from ..utils.logger import Logger

logger = Logger("APIManager")

API_SERVICE_KEY = "api_service"  # Key for storage
CUSTOM_APIS_FILE = Path.home() / "Library" / "Application Support" / "OverAI" / "custom_apis.json"


class APIManager:
    """
    Manages API-based AI services.
    Handles custom API configurations and key storage.
    """
    
    def __init__(self):
        self._keychain = KeychainManager()
        self._custom_services: Dict[str, CustomAPIService] = {}
        self._load_custom_services()
    
    def _load_custom_services(self):
        """Load user-defined custom API services."""
        try:
            if CUSTOM_APIS_FILE.exists():
                with open(CUSTOM_APIS_FILE, 'r') as f:
                    data = json.load(f)
                    
                for service_data in data.get('services', []):
                    service = CustomAPIService.from_dict(service_data)
                    self._custom_services[service.id] = service
                    
                logger.info(f"Loaded {len(self._custom_services)} custom API services")
        except Exception as e:
            logger.error(f"Error loading custom services: {e}")
    
    def _save_custom_services(self):
        """Save custom API services to disk."""
        try:
            CUSTOM_APIS_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'services': [s.to_dict() for s in self._custom_services.values()]
            }
            
            with open(CUSTOM_APIS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info("Saved custom API services")
            
        except Exception as e:
            logger.error(f"Error saving custom services: {e}")
    
    def get_all_services(self) -> Dict[str, APIService]:
        """
        Get all available API services (predefined + custom).
        
        Returns:
            Dictionary of service_id -> APIService
        """
        services = dict(PREDEFINED_APIS)
        services.update(self._custom_services)
        return services
    
    def get_service(self, service_id: str) -> Optional[APIService]:
        """Get a specific service by ID."""
        if service_id in PREDEFINED_APIS:
            return PREDEFINED_APIS[service_id]
        return self._custom_services.get(service_id)
    
    def add_custom_service(self, name: str, base_url: str, api_key: str,
                          api_format: str = "openai", default_model: str = None,
                          description: str = "") -> Optional[CustomAPIService]:
        """
        Add a new custom API service.
        
        Args:
            name: Display name
            base_url: API base URL
            api_key: API key (stored in Keychain)
            api_format: API format (openai, anthropic, custom)
            default_model: Default model name
            description: Optional description
            
        Returns:
            The created service or None on error
        """
        try:
            # Parse API format
            format_enum = APIFormat(api_format.lower())
            
            # Create service
            service = CustomAPIService.create(
                name=name,
                base_url=base_url,
                api_key=api_key,
                api_format=format_enum,
                default_model=default_model,
                description=description
            )
            
            # Store API key
            if api_key and service.requires_api_key:
                if not self._keychain.save_api_key(service.id, api_key):
                    logger.warning("Failed to save API key to Keychain, using file fallback")
            
            # Add to custom services
            self._custom_services[service.id] = service
            self._save_custom_services()
            
            logger.info(f"Added custom API service: {service.name} ({service.id})")
            return service
            
        except Exception as e:
            logger.error(f"Error adding custom service: {e}")
            return None
    
    def remove_custom_service(self, service_id: str) -> bool:
        """
        Remove a custom API service.
        
        Args:
            service_id: ID of the service to remove
            
        Returns:
            True if successful
        """
        if service_id in self._custom_services:
            # Delete API key
            self._keychain.delete_api_key(service_id)
            
            # Remove service
            del self._custom_services[service_id]
            self._save_custom_services()
            
            logger.info(f"Removed custom API service: {service_id}")
            return True
        
        return False
    
    def update_service_api_key(self, service_id: str, api_key: str) -> bool:
        """
        Update the API key for a service.
        
        Args:
            service_id: Service ID
            api_key: New API key
            
        Returns:
            True if successful
        """
        service = self.get_service(service_id)
        if not service:
            return False
        
        return self._keychain.save_api_key(service_id, api_key)
    
    def get_api_key(self, service_id: str) -> Optional[str]:
        """Get the API key for a service."""
        return self._keychain.get_api_key(service_id)
    
    def test_connection(self, service_id: str) -> tuple:
        """
        Test connection to an API service.
        
        Returns:
            (success: bool, message: str)
        """
        import urllib.request
        import urllib.error
        import json
        
        service = self.get_service(service_id)
        if not service:
            return False, "Service not found"
        
        api_key = self.get_api_key(service_id)
        if service.requires_api_key and not api_key:
            return False, "API key not configured"
        
        try:
            # Build request
            url = service.get_full_url(service.models_endpoint)
            headers = {
                "Content-Type": "application/json"
            }
            
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            if service.headers:
                headers.update(service.headers)
            
            req = urllib.request.Request(
                url,
                headers=headers,
                method="GET"
            )
            
            # Make request with timeout
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    model_count = len(data.get('data', []))
                    return True, f"Connected! {model_count} models available"
                else:
                    return False, f"HTTP {response.status}"
                    
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return False, "Invalid API key"
            elif e.code == 404:
                return True, "Connected (models endpoint not available)"
            return False, f"HTTP {e.code}"
            
        except urllib.error.URLError as e:
            return False, f"Connection failed: {e.reason}"
            
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def get_available_models(self, service_id: str) -> List[str]:
        """
        Get list of available models for a service.
        
        Returns:
            List of model IDs
        """
        import urllib.request
        import json
        
        service = self.get_service(service_id)
        if not service:
            return []
        
        api_key = self.get_api_key(service_id)
        
        try:
            url = service.get_full_url(service.models_endpoint)
            headers = {"Content-Type": "application/json"}
            
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                models = data.get('data', [])
                return [m.get('id', '') for m in models if m.get('id')]
                
        except Exception as e:
            logger.error(f"Error fetching models: {e}")
            # Return default model
            if service.default_model:
                return [service.default_model]
            return []


# Global instance
_api_manager = None

def get_api_manager() -> APIManager:
    """Get the global API manager instance."""
    global _api_manager
    if _api_manager is None:
        _api_manager = APIManager()
    return _api_manager
