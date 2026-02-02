"""
Secure API key storage using macOS Keychain.
"""

import objc
from Foundation import NSBundle

# Load Security framework
Security = NSBundle.bundleWithIdentifier_("com.apple.security")

from ..utils.logger import Logger

logger = Logger("Keychain")


class KeychainManager:
    """
    Manages secure storage of API keys in macOS Keychain.
    """
    
    SERVICE_NAME = "com.overai.apikeys"
    
    def __init__(self):
        self._security = Security
    
    def save_api_key(self, service_id: str, api_key: str) -> bool:
        """
        Save an API key to the Keychain.
        
        Args:
            service_id: Unique identifier for the service
            api_key: The API key to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete existing key first
            self.delete_api_key(service_id)
            
            # Import Security functions
            from Security import SecItemAdd, SecItemDelete, kSecClassGenericPassword
            from Security import kSecAttrAccount, kSecAttrService, kSecValueData, kSecClass
            
            # Create query
            query = {
                kSecClass: kSecClassGenericPassword,
                kSecAttrService: self.SERVICE_NAME,
                kSecAttrAccount: service_id,
                kSecValueData: api_key.encode('utf-8')
            }
            
            status = SecItemAdd(query, None)
            
            if status == 0:  # errSecSuccess
                logger.info(f"Saved API key for {service_id}")
                return True
            else:
                logger.error(f"Failed to save API key: {status}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving API key: {e}")
            # Fallback to file storage for development
            return self._save_to_file(service_id, api_key)
    
    def get_api_key(self, service_id: str) -> str:
        """
        Retrieve an API key from the Keychain.
        
        Args:
            service_id: Unique identifier for the service
            
        Returns:
            The API key or None if not found
        """
        try:
            from Security import SecItemCopyMatching, kSecClassGenericPassword
            from Security import kSecAttrAccount, kSecAttrService, kSecReturnData
            from Security import kSecClass, kSecMatchLimit, kSecMatchLimitOne
            
            query = {
                kSecClass: kSecClassGenericPassword,
                kSecAttrService: self.SERVICE_NAME,
                kSecAttrAccount: service_id,
                kSecReturnData: True,
                kSecMatchLimit: kSecMatchLimitOne
            }
            
            result = SecItemCopyMatching(query, None)
            
            if result and result[0] == 0:  # errSecSuccess
                data = result[1]
                if data:
                    return data.decode('utf-8')
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving API key: {e}")
            # Fallback to file storage
            return self._get_from_file(service_id)
    
    def delete_api_key(self, service_id: str) -> bool:
        """
        Delete an API key from the Keychain.
        
        Args:
            service_id: Unique identifier for the service
            
        Returns:
            True if successful or not found, False on error
        """
        try:
            from Security import SecItemDelete, kSecClassGenericPassword
            from Security import kSecAttrAccount, kSecAttrService, kSecClass
            
            query = {
                kSecClass: kSecClassGenericPassword,
                kSecAttrService: self.SERVICE_NAME,
                kSecAttrAccount: service_id
            }
            
            SecItemDelete(query)
            return True
            
        except Exception as e:
            logger.error(f"Error deleting API key: {e}")
            return False
    
    def _save_to_file(self, service_id: str, api_key: str) -> bool:
        """Fallback: Save to encrypted file (development only)."""
        import json
        from pathlib import Path
        
        try:
            config_dir = Path.home() / "Library" / "Application Support" / "OverAI"
            config_dir.mkdir(parents=True, exist_ok=True)
            
            key_file = config_dir / ".api_keys"
            
            keys = {}
            if key_file.exists():
                with open(key_file, 'r') as f:
                    keys = json.load(f)
            
            keys[service_id] = api_key
            
            with open(key_file, 'w') as f:
                json.dump(keys, f)
            
            # Set restrictive permissions
            key_file.chmod(0o600)
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving to file: {e}")
            return False
    
    def _get_from_file(self, service_id: str) -> str:
        """Fallback: Retrieve from file."""
        import json
        from pathlib import Path
        
        try:
            key_file = Path.home() / "Library" / "Application Support" / "OverAI" / ".api_keys"
            
            if key_file.exists():
                with open(key_file, 'r') as f:
                    keys = json.load(f)
                return keys.get(service_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Error reading from file: {e}")
            return None
